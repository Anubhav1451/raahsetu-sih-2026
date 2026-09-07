"""Backend-only PostGIS access for geo-tagged field reports."""

from __future__ import annotations

import os
from typing import Protocol

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import FieldReport, FieldReportAttachment, FieldReportCreate, FieldReportReview


class FieldReportStore(Protocol):
    def create(self, report: FieldReportCreate, reporter_id: str) -> FieldReport: ...

    def list(self, region_code: str | None, limit: int) -> list[FieldReport]: ...

    def review(self, report_id: str, review: FieldReportReview, reviewer_id: str) -> FieldReport: ...

    def active_events(self, region_code: str | None) -> list[dict]: ...

    def road_candidates(self, report_id: str, dataset_id: str) -> list[dict]: ...

    def save_attachment(self, report_id: str, user_id: str, path: str, mime: str, size: int, sha256: str) -> FieldReportAttachment: ...


class PostgresFieldReportStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("Field reporting requires DATABASE_URL")
        return psycopg.connect(self.database_url, sslmode="require", row_factory=dict_row)

    @staticmethod
    def _to_model(row: dict) -> FieldReport:
        return FieldReport.model_validate(row)

    def create(self, report: FieldReportCreate, reporter_id: str) -> FieldReport:
        with self._connect() as conn:
            row = conn.execute(
                """insert into field_reports
                (client_report_id,reporter_id,region_code,district,place_name,kind,accessibility_status,
                 severity,geom,description,observed_at,valid_until,offline_created_at,details)
                values(%(client_report_id)s,%(reporter_id)s,%(region_code)s,%(district)s,%(place_name)s,%(kind)s,
                 %(accessibility_status)s,%(severity)s,
                 st_setsrid(st_makepoint(%(lon)s,%(lat)s),4326),%(description)s,
                 %(observed_at)s,%(valid_until)s,%(offline_created_at)s,%(details)s)
                on conflict(client_report_id) do update
                  set client_report_id=excluded.client_report_id
                  where field_reports.reporter_id=excluded.reporter_id
                returning id::text,client_report_id,region_code,district,place_name,kind,
                  accessibility_status,severity,st_x(geom) lon,st_y(geom) lat,description,
                  observed_at,submitted_at,review_status,valid_until,offline_created_at,details""",
                {**report.model_dump(), "reporter_id": reporter_id, "details": Jsonb(report.details)},
            ).fetchone()
            if row is None:
                raise ValueError("Client report ID belongs to a different submission")
            return self._to_model(row)

    def list(self, region_code: str | None, limit: int) -> list[FieldReport]:
        with self._connect() as conn:
            select = """select id::text,client_report_id,region_code,district,place_name,kind,
                accessibility_status,severity,st_x(geom) lon,st_y(geom) lat,description,
                observed_at,submitted_at,review_status,valid_until,offline_created_at,details
                from field_reports"""
            if region_code:
                rows = conn.execute(
                    select + " where region_code=%s order by observed_at desc limit %s",
                    (region_code, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    select + " order by observed_at desc limit %s", (limit,)
                ).fetchall()
            return [self._to_model(row) for row in rows]

    def review(self, report_id: str, review: FieldReportReview, reviewer_id: str) -> FieldReport:
        with self._connect() as conn:
            source = conn.execute(
                "select * from field_reports where id=%s for update", (report_id,)
            ).fetchone()
            if not source:
                raise LookupError("Field report was not found")
            profile = conn.execute(
                "select role,region_code from profiles where id=%s", (reviewer_id,)
            ).fetchone()
            if not profile or profile["role"] not in {"reviewer", "admin"}:
                raise ValueError("Reviewer role required")
            if (
                profile["role"] != "admin"
                and profile["region_code"]
                and profile["region_code"] != source["region_code"]
            ):
                raise ValueError("Report is outside the assigned reviewer region")
            if source["review_status"] != "pending":
                raise ValueError("Field report has already been reviewed")
            if review.decision == "accepted":
                status = source["accessibility_status"]
                if status == "unknown":
                    raise ValueError("An unknown accessibility status cannot be accepted")
                candidate = conn.execute(
                    """select edge_id from road_edges e join field_reports r on r.id=%s
                    where e.dataset_id=%s and e.edge_id=%s
                    and st_dwithin(e.geom::geography,r.geom::geography,2000) limit 1""",
                    (report_id, review.dataset_id, review.edge_id),
                ).fetchone()
                if not candidate:
                    raise ValueError("Selected road edge is not within 2 km of the report")
                conn.execute(
                """insert into accessibility_events
                    (source_report_id,region_code,dataset_id,edge_id,kind,accessibility_status,severity,geom,
                     starts_at,ends_at,source,details)
                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'field_report',%s)""",
                    (
                        source["id"], source["region_code"], review.dataset_id, review.edge_id,
                        source["kind"], status,
                        source["severity"], source["geom"], source["observed_at"],
                        source["valid_until"], Jsonb({**(source["details"] or {}), "review_note": review.review_note}),
                    ),
                )
            row = conn.execute(
                """update field_reports set review_status=%s,reviewed_by=%s,
                reviewed_at=now(),review_note=%s where id=%s
                returning id::text,client_report_id,region_code,district,place_name,kind,
                  accessibility_status,severity,st_x(geom) lon,st_y(geom) lat,description,
                  observed_at,submitted_at,review_status,valid_until,offline_created_at,details""",
                (review.decision, reviewer_id, review.review_note, report_id),
            ).fetchone()
            conn.execute(
                """insert into operation_audit_log
                (actor_id,action,entity_type,entity_id,before_state,after_state)
                values(%s,'review','field_report',%s,%s,%s)""",
                (
                    reviewer_id, report_id,
                    Jsonb({"review_status": "pending"}),
                    Jsonb({"review_status": review.decision, "review_note": review.review_note}),
                ),
            )
            return self._to_model(row)

    def road_candidates(self, report_id: str, dataset_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """select e.edge_id,e.name,
                round(st_distance(e.geom::geography,r.geom::geography)::numeric,1) distance_m
                from road_edges e join field_reports r on r.id=%s
                where e.dataset_id=%s and st_dwithin(e.geom::geography,r.geom::geography,2000)
                order by st_distance(e.geom::geography,r.geom::geography) limit 10""",
                (report_id, dataset_id),
            ).fetchall()
            return [dict(row) for row in rows]

    def save_attachment(self, report_id: str, user_id: str, path: str, mime: str, size: int, sha256: str) -> FieldReportAttachment:
        with self._connect() as conn:
            row = conn.execute(
                """insert into field_report_attachments(report_id,storage_path,mime_type,byte_size,sha256)
                select id,%s,%s,%s,%s from field_reports where id=%s and reporter_id=%s
                returning id::text,report_id::text,storage_path,mime_type,byte_size,sha256,captured_at""",
                (path, mime, size, sha256, report_id, user_id),
            ).fetchone()
            if not row:
                raise LookupError("Report not found or not owned by current user")
            return FieldReportAttachment.model_validate(row)

    def active_events(self, region_code: str | None) -> list[dict]:
        where = "where (e.ends_at is null or e.ends_at >= now())"
        params: tuple = ()
        if region_code:
            where += " and e.region_code=%s"
            params = (region_code,)
        with self._connect() as conn:
            rows = conn.execute(
                f"""select e.id::text,e.region_code,e.dataset_id,e.edge_id,e.kind,
                e.accessibility_status,e.severity,st_x(e.geom) lon,st_y(e.geom) lat,
                e.starts_at,e.ends_at,e.source,e.details
                from accessibility_events e {where}
                order by e.starts_at desc limit 500""", params,
            ).fetchall()
            return [dict(row) for row in rows]
