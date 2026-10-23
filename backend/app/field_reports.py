"""Backend-only PostGIS access for geo-tagged field reports."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Protocol

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import FieldReport, FieldReportAttachment, FieldReportCreate, FieldReportReview


class FieldReportStore(Protocol):
    def create(self, report: FieldReportCreate, reporter_id: str) -> FieldReport: ...

    def list(
        self,
        region_code: str | None,
        limit: int,
        status: str | None = None,
        include_expired: bool = True,
    ) -> list[FieldReport]: ...

    def review(self, report_id: str, review: FieldReportReview, reviewer_id: str) -> FieldReport: ...

    def active_events(
        self, region_code: str | None = None, include_inactive: bool = False
    ) -> list[dict]: ...

    def resolve_event(self, event_id: str, actor_id: str, note: str) -> dict: ...

    def extend_event_expiry(
        self, event_id: str, actor_id: str, new_ends_at: datetime, note: str
    ) -> dict: ...

    def road_candidates(self, report_id: str, dataset_id: str, region_code: str | None = None) -> list[dict]: ...

    def save_attachment(self, report_id: str, user_id: str, path: str, mime: str, size: int, sha256: str) -> FieldReportAttachment: ...


class PostgresFieldReportStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("Field reporting requires DATABASE_URL")
        return psycopg.connect(self.database_url, sslmode=os.getenv("DATABASE_SSLMODE", "require"),
                               connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5")),
                               options=f"-c statement_timeout={int(os.getenv('DB_STATEMENT_TIMEOUT_MS', '5000'))} -c idle_in_transaction_session_timeout=10000",
                               row_factory=dict_row)

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

    def list(
        self,
        region_code: str | None,
        limit: int,
        status: str | None = None,
        include_expired: bool = True,
    ) -> list[FieldReport]:
        with self._connect() as conn:
            select = """select id::text,client_report_id,region_code,district,place_name,kind,
                accessibility_status,severity,st_x(geom) lon,st_y(geom) lat,description,
                observed_at,submitted_at,review_status,valid_until,offline_created_at,details
                from field_reports"""
            clauses = []
            params: list = []
            if region_code:
                clauses.append("region_code=%s")
                params.append(region_code)
            if status:
                clauses.append("review_status=%s")
                params.append(status)
            if not include_expired:
                clauses.append("(valid_until is null or valid_until >= now())")
            where_sql = f" where {' and '.join(clauses)}" if clauses else ""
            params.append(limit)
            rows = conn.execute(
                f"{select}{where_sql} order by observed_at desc limit %s", tuple(params)
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
            if source["review_status"] not in {"pending", "corroborated"}:
                raise ValueError("Field report has already been reviewed")

            valid_until = review.valid_until or source["valid_until"]
            decision_status = review.decision
            if review.decision == "evidence_requested":
                decision_status = "pending"

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
                event = conn.execute(
                    """insert into accessibility_events
                    (source_report_id,region_code,dataset_id,edge_id,kind,accessibility_status,severity,geom,
                     starts_at,ends_at,source,details)
                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'field_report',%s)
                    returning id""",
                    (
                        source["id"],
                        source["region_code"],
                        review.dataset_id,
                        review.edge_id,
                        source["kind"],
                        status,
                        source["severity"],
                        source["geom"],
                        source["observed_at"],
                        valid_until,
                        Jsonb(
                            {
                                **(source["details"] or {}),
                                "review_note": review.review_note,
                                "reviewer_id": reviewer_id,
                            }
                        ),
                    ),
                ).fetchone()
                if event:
                    alert_type = "blocked_route" if status == "blocked" else "high_risk"
                    conn.execute(
                        """insert into alerts(event_id,alert_type,severity,title,message_key,message_params,expires_at)
                        values(%s,%s,%s,%s,%s,%s,%s)
                        on conflict do nothing""",
                        (
                            event["id"],
                            alert_type,
                            source["severity"],
                            "Road blocked" if status == "blocked" else "Road accessibility restricted",
                            "route.blocked" if status == "blocked" else "route.restricted",
                            Jsonb({"place": source["place_name"], "district": source["district"]}),
                            valid_until,
                        ),
                    )

            updated_details = {
                **(source["details"] or {}),
                "reviewed_by": reviewer_id,
                "review_note": review.review_note,
            }
            if review.decision == "evidence_requested":
                updated_details["evidence_requested"] = True

            row = conn.execute(
                """update field_reports set review_status=%s,reviewed_by=%s,
                reviewed_at=now(),review_note=%s,valid_until=%s,details=%s where id=%s
                returning id::text,client_report_id,region_code,district,place_name,kind,
                  accessibility_status,severity,st_x(geom) lon,st_y(geom) lat,description,
                  observed_at,submitted_at,review_status,valid_until,offline_created_at,details""",
                (
                    decision_status,
                    reviewer_id,
                    review.review_note,
                    valid_until,
                    Jsonb(updated_details),
                    report_id,
                ),
            ).fetchone()
            conn.execute(
                """insert into operation_audit_log
                (actor_id,action,entity_type,entity_id,before_state,after_state)
                values(%s,'review','field_report',%s,%s,%s)""",
                (
                    reviewer_id,
                    report_id,
                    Jsonb({"review_status": source["review_status"]}),
                    Jsonb({"review_status": review.decision, "review_note": review.review_note}),
                ),
            )
            return self._to_model(row)

    def road_candidates(self, report_id: str, dataset_id: str, region_code: str | None = None) -> list[dict]:
        with self._connect() as conn:
            report = conn.execute(
                "select region_code from field_reports where id=%s", (report_id,),
            ).fetchone()
            if not report:
                raise LookupError("Field report was not found")
            if region_code is not None and report["region_code"] != region_code:
                raise PermissionError("Report is outside the assigned reviewer region")
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

    def active_events(
        self, region_code: str | None = None, include_inactive: bool = False
    ) -> list[dict]:
        max_age_hours = int(os.getenv("OPERATIONAL_EVENT_MAX_AGE_HOURS", "24"))
        where_clauses = []
        params: list = []
        if not include_inactive:
            where_clauses.append("(e.ends_at is null or e.ends_at >= now())")
            where_clauses.append("e.starts_at >= now() - (%s * interval '1 hour')")
            params.append(max_age_hours)
        if region_code:
            where_clauses.append("e.region_code=%s")
            params.append(region_code)
        where_sql = f"where {' and '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""select e.id::text,e.region_code,e.dataset_id,e.edge_id,e.kind,
                e.accessibility_status,e.severity,st_x(e.geom) lon,st_y(e.geom) lat,
                e.starts_at,e.ends_at,e.source,e.details
                from accessibility_events e {where_sql}
                order by e.starts_at desc limit 500""",
                tuple(params),
            ).fetchall()
            return [dict(row) for row in rows]

    def resolve_event(self, event_id: str, actor_id: str, note: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                """update accessibility_events
                set ends_at=now(),
                    details=details || jsonb_build_object('resolved_by', %s, 'resolution_note', %s, 'resolved_at', now()::text)
                where id=%s
                returning id::text, region_code, dataset_id, edge_id, kind, accessibility_status, severity,
                          st_x(geom) lon, st_y(geom) lat, starts_at, ends_at, source, details""",
                (actor_id, note, event_id),
            ).fetchone()
            if not row:
                raise LookupError("Accessibility event was not found")
            conn.execute(
                """insert into operation_audit_log (actor_id, action, entity_type, entity_id, before_state, after_state)
                values(%s, 'resolve', 'accessibility_event', %s, '{}'::jsonb, %s)""",
                (actor_id, event_id, Jsonb({"resolution_note": note})),
            )
            res = dict(row)
            res["status"] = "resolved"
            return res

    def extend_event_expiry(
        self, event_id: str, actor_id: str, new_ends_at: datetime, note: str
    ) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                """update accessibility_events
                set ends_at=%s,
                    details=details || jsonb_build_object('extended_by', %s, 'extension_note', %s)
                where id=%s
                returning id::text, region_code, dataset_id, edge_id, kind, accessibility_status, severity,
                          st_x(geom) lon, st_y(geom) lat, starts_at, ends_at, source, details""",
                (new_ends_at, actor_id, note, event_id),
            ).fetchone()
            if not row:
                raise LookupError("Accessibility event was not found")
            conn.execute(
                """insert into operation_audit_log (actor_id, action, entity_type, entity_id, before_state, after_state)
                values(%s, 'extend_expiry', 'accessibility_event', %s, '{}'::jsonb, %s)""",
                (actor_id, event_id, Jsonb({"new_ends_at": new_ends_at.isoformat(), "note": note})),
            )
            res = dict(row)
            res["status"] = "active"
            return res


class InMemoryFieldReportStore:
    """In-memory store providing full field report capabilities when PostgreSQL is unavailable."""

    def __init__(self):
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        self._reports: dict[str, FieldReport] = {}
        self._reports_by_client_id: dict[str, str] = {}
        self._attachments: list[FieldReportAttachment] = []
        self._events: list[dict] = []

        # Seed realistic reports for demonstration and review testing
        rep1_id = "00000000-0000-0000-0000-000000000101"
        self._reports[rep1_id] = FieldReport(
            id=rep1_id,
            client_report_id="rep-sela-pass-001",
            region_code="arunachal-pradesh",
            district="West Kameng",
            place_name="Sela Pass Summit Ridge",
            kind="landslide",
            accessibility_status="blocked",
            severity=0.92,
            lon=92.10,
            lat=27.50,
            description="Active sub-zero rockfall and snow slush over NH-13. Heavy vehicles unable to pass summit bend. Detour via lower tunnel bypass recommended.",
            observed_at=now - timedelta(hours=2),
            submitted_at=now - timedelta(hours=1, minutes=45),
            review_status="pending",
            valid_until=now + timedelta(hours=22),
            offline_created_at=None,
            details={"reporter_role": "field_official", "has_photo": True, "district_sdma": "West Kameng DC Office"},
        )
        rep2_id = "00000000-0000-0000-0000-000000000102"
        self._reports[rep2_id] = FieldReport(
            id=rep2_id,
            client_report_id="rep-phesama-sink-002",
            region_code="nagaland",
            district="Kohima",
            place_name="NH-29 Phesama Subsidence Zone",
            kind="road_damage",
            accessibility_status="restricted",
            severity=0.86,
            lon=94.10,
            lat=25.65,
            description="Tectonic sinking of road shoulder on NH-29. Multi-axle commercial freight halted; light emergency 4x4 permitted at 10km/h crawl.",
            observed_at=now - timedelta(hours=4),
            submitted_at=now - timedelta(hours=3, minutes=30),
            review_status="corroborated",
            valid_until=now + timedelta(hours=18),
            offline_created_at=None,
            details={"reporter_role": "field_official", "has_photo": True, "corroboration_note": "Corroborated by 2 independent field observations"},
        )
        rep3_id = "00000000-0000-0000-0000-000000000103"
        self._reports[rep3_id] = FieldReport(
            id=rep3_id,
            client_report_id="rep-sonapur-flood-003",
            region_code="meghalaya",
            district="East Jaintia Hills",
            place_name="Sonapur Tunnel Flash Mudflow",
            kind="flood",
            accessibility_status="restricted",
            severity=0.88,
            lon=92.36,
            lat=25.12,
            description="Hill stream overflowed tunnel mouth; sludge clearance underway. Single lane alternating traffic.",
            observed_at=now - timedelta(hours=6),
            submitted_at=now - timedelta(hours=5),
            review_status="authority_verified",
            valid_until=now + timedelta(hours=12),
            offline_created_at=None,
            details={"reporter_role": "reviewer", "reviewed_by": "demo-reviewer", "review_note": "PWD clearing squad on site with JCB"},
        )
        rep4_id = "00000000-0000-0000-0000-000000000104"
        self._reports[rep4_id] = FieldReport(
            id=rep4_id,
            client_report_id="rep-kamakhya-old-004",
            region_code="assam",
            district="Kamrup Metropolitan",
            place_name="Kamakhya Foothills Drainage",
            kind="road_blocked",
            accessibility_status="blocked",
            severity=0.75,
            lon=91.70,
            lat=26.16,
            description="Temporary waterlogging cleared yesterday. Report expired.",
            observed_at=now - timedelta(days=2),
            submitted_at=now - timedelta(days=2),
            review_status="expired",
            valid_until=now - timedelta(hours=10),
            offline_created_at=None,
            details={"reporter_role": "citizen", "has_photo": False},
        )
        for r_id, r in self._reports.items():
            self._reports_by_client_id[r.client_report_id] = r_id

        # Seed operational accessibility events
        self._events = [
            {
                "id": "evt-001",
                "source_report_id": rep1_id,
                "region_code": "arunachal-pradesh",
                "dataset_id": "osm-arunachal-pradesh",
                "edge_id": "e_nh13_sela",
                "kind": "landslide",
                "accessibility_status": "blocked",
                "severity": 0.92,
                "lon": 92.10,
                "lat": 27.50,
                "starts_at": (now - timedelta(hours=2)).isoformat(),
                "ends_at": (now + timedelta(hours=22)).isoformat(),
                "source": "field_report",
                "review_status": "authority_verified",
                "verification_authority": "SDRF Arunachal / BRO Project Vartak",
                "details": {"review_note": "NH-13 Sela Pass closed due to sub-zero rockfall. Diverting freight to Sela Tunnel bypass."},
            },
            {
                "id": "evt-002",
                "source_report_id": rep2_id,
                "region_code": "nagaland",
                "dataset_id": "osm-nagaland",
                "edge_id": "e_nh29_phesama",
                "kind": "road_damage",
                "accessibility_status": "restricted",
                "severity": 0.86,
                "lon": 94.10,
                "lat": 25.65,
                "starts_at": (now - timedelta(hours=4)).isoformat(),
                "ends_at": (now + timedelta(hours=18)).isoformat(),
                "source": "field_report",
                "review_status": "authority_verified",
                "verification_authority": "Nagaland PWD (NH) Division",
                "details": {"review_note": "NH-29 Phesama sinking zone restricted to 3.5T; multi-axle freight detoured."},
            },
            {
                "id": "evt-003",
                "source_report_id": rep3_id,
                "region_code": "meghalaya",
                "dataset_id": "osm-meghalaya",
                "edge_id": "e_nh6_sonapur",
                "kind": "flood",
                "accessibility_status": "restricted",
                "severity": 0.88,
                "lon": 92.36,
                "lat": 25.12,
                "starts_at": (now - timedelta(hours=6)).isoformat(),
                "ends_at": (now + timedelta(hours=12)).isoformat(),
                "source": "field_report",
                "review_status": "authority_verified",
                "verification_authority": "Meghalaya Disaster Management Authority",
                "details": {"review_note": "Sonapur tunnel single-lane mud clearance operation underway."},
            },
            {
                "id": "evt-004",
                "source_report_id": None,
                "region_code": "assam",
                "dataset_id": "osm-guwahati",
                "edge_id": "e_nh27_beltola",
                "kind": "road_damage",
                "accessibility_status": "restricted",
                "severity": 0.65,
                "lon": 91.78,
                "lat": 26.12,
                "starts_at": (now - timedelta(days=1)).isoformat(),
                "ends_at": (now - timedelta(hours=2)).isoformat(),
                "source": "pwd_advisory",
                "review_status": "authority_verified",
                "verification_authority": "Assam PWD Roads Division",
                "details": {"review_note": "Culvert repair completed and verified by PWD Inspector.", "resolved_by": "demo-reviewer"},
            },
        ]

    def create(self, report: FieldReportCreate, reporter_id: str) -> FieldReport:
        import uuid
        from datetime import UTC, datetime

        client_id = report.client_report_id
        if client_id in self._reports_by_client_id:
            existing_id = self._reports_by_client_id[client_id]
            return self._reports[existing_id]

        report_id = str(uuid.uuid4())
        # Check auto-corroboration: if another pending report exists nearby (<2km) in same region
        nearby_count = sum(
            1 for r in self._reports.values()
            if r.region_code == report.region_code
            and abs(r.lon - report.lon) < 0.02 and abs(r.lat - report.lat) < 0.02
        )
        initial_status = "corroborated" if nearby_count >= 1 else "pending"

        details = dict(report.details)
        if nearby_count >= 1:
            details["corroboration_note"] = f"Corroborated by {nearby_count} independent field observation(s)"

        stored = FieldReport(
            id=report_id,
            client_report_id=report.client_report_id,
            region_code=report.region_code,
            district=report.district,
            place_name=report.place_name,
            kind=report.kind,
            accessibility_status=report.accessibility_status,
            severity=report.severity,
            lon=report.lon,
            lat=report.lat,
            description=report.description,
            observed_at=report.observed_at,
            submitted_at=datetime.now(UTC),
            review_status=initial_status,
            valid_until=report.valid_until,
            offline_created_at=report.offline_created_at,
            details=details,
        )
        self._reports[report_id] = stored
        self._reports_by_client_id[client_id] = report_id
        return stored

    def list(
        self,
        region_code: str | None,
        limit: int,
        status: str | None = None,
        include_expired: bool = True,
    ) -> list[FieldReport]:
        from datetime import UTC, datetime
        now = datetime.now(UTC)

        matches = []
        for r in self._reports.values():
            if region_code is not None and r.region_code != region_code:
                continue
            if status is not None and r.review_status != status:
                continue
            if not include_expired and r.valid_until is not None and r.valid_until < now:
                continue
            matches.append(r)

        matches.sort(key=lambda x: x.observed_at, reverse=True)
        return matches[:limit]

    def review(self, report_id: str, review: FieldReportReview, reviewer_id: str) -> FieldReport:
        import uuid

        if report_id not in self._reports:
            raise LookupError("Field report was not found")

        source = self._reports[report_id]
        if source.review_status not in {"pending", "corroborated"}:
            raise ValueError("Field report has already been reviewed")

        status = source.accessibility_status
        valid_until = review.valid_until or source.valid_until

        if review.decision == "accepted":
            if status == "unknown":
                raise ValueError("An unknown accessibility status cannot be accepted")
            event_id = str(uuid.uuid4())
            event = {
                "id": event_id,
                "source_report_id": source.id,
                "region_code": source.region_code,
                "dataset_id": review.dataset_id,
                "edge_id": review.edge_id,
                "kind": source.kind,
                "accessibility_status": status,
                "severity": source.severity,
                "lon": source.lon,
                "lat": source.lat,
                "starts_at": source.observed_at.isoformat(),
                "ends_at": valid_until.isoformat() if valid_until else None,
                "source": "field_report",
                "review_status": "authority_verified",
                "verification_authority": f"Reviewer ({reviewer_id})",
                "details": {**(source.details or {}), "review_note": review.review_note},
            }
            self._events.insert(0, event)

        final_review_status = (
            "authority_verified"
            if review.decision == "accepted"
            else ("pending" if review.decision == "evidence_requested" else "rejected")
        )
        updated_details = {
            **(source.details or {}),
            "reviewed_by": reviewer_id,
            "review_note": review.review_note,
        }
        if review.decision == "evidence_requested":
            updated_details["evidence_requested"] = True

        updated = source.model_copy(
            update={
                "review_status": final_review_status,
                "valid_until": valid_until,
                "details": updated_details,
            }
        )
        self._reports[report_id] = updated
        return updated

    def road_candidates(self, report_id: str, dataset_id: str, region_code: str | None = None) -> list[dict]:
        import json
        from pathlib import Path

        from .routing import distance_m

        if report_id not in self._reports:
            raise LookupError("Field report was not found")

        report = self._reports[report_id]
        if region_code is not None and report.region_code != region_code:
            raise PermissionError("Report is outside the assigned reviewer region")

        root = Path(__file__).resolve().parents[1]
        graph_file = root / "data" / f"{dataset_id}.json"
        if not graph_file.exists():
            graph_file = root / "data" / "osm-northeast.json"
        if not graph_file.exists():
            return []

        data = json.loads(graph_file.read_text(encoding="utf-8"))
        candidates = []
        for edge in data.get("edges", []):
            geom = edge.get("geometry", [])
            if len(geom) >= 2:
                # Approximate distance to line midpoint / start
                mid = geom[len(geom) // 2]
                d = distance_m(report.lon, report.lat, mid[0], mid[1])
                if d <= 5000:
                    candidates.append({"edge_id": edge["id"], "name": edge["name"], "distance_m": round(d, 1)})

        candidates.sort(key=lambda x: x["distance_m"])
        return candidates[:10]

    def save_attachment(self, report_id: str, user_id: str, path: str, mime: str, size: int, sha256: str) -> FieldReportAttachment:
        import uuid
        from datetime import UTC, datetime

        if report_id not in self._reports:
            raise LookupError("Report not found or not owned by current user")

        attachment = FieldReportAttachment(
            id=str(uuid.uuid4()),
            report_id=report_id,
            storage_path=path,
            mime_type=mime,
            byte_size=size,
            sha256=sha256,
            captured_at=datetime.now(UTC),
        )
        self._attachments.append(attachment)
        return attachment

    def active_events(
        self, region_code: str | None = None, include_inactive: bool = False
    ) -> list[dict]:
        import os
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        cutoff = now - timedelta(
            hours=int(os.getenv("OPERATIONAL_EVENT_MAX_AGE_HOURS", "24"))
        )
        results = []
        for e in self._events:
            if region_code is not None and e.get("region_code") != region_code:
                continue
            if not include_inactive:
                if datetime.fromisoformat(e["starts_at"]) < cutoff:
                    continue
                if e.get("ends_at") is not None and datetime.fromisoformat(e["ends_at"]) < now:
                    continue
            results.append(e)
        return results

    def resolve_event(self, event_id: str, actor_id: str, note: str) -> dict:
        from datetime import UTC, datetime
        now = datetime.now(UTC)
        for event in self._events:
            if event["id"] == event_id:
                event["ends_at"] = now.isoformat()
                event["status"] = "resolved"
                event["details"] = {
                    **(event.get("details") or {}),
                    "resolved_by": actor_id,
                    "resolution_note": note,
                    "resolved_at": now.isoformat(),
                }
                return event
        raise LookupError("Accessibility event was not found")

    def extend_event_expiry(
        self, event_id: str, actor_id: str, new_ends_at: datetime, note: str
    ) -> dict:
        for event in self._events:
            if event["id"] == event_id:
                event["ends_at"] = new_ends_at.isoformat()
                event["status"] = "active"
                event["details"] = {
                    **(event.get("details") or {}),
                    "extended_by": actor_id,
                    "extension_note": note,
                }
                return event
        raise LookupError("Accessibility event was not found")
