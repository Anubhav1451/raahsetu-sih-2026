from __future__ import annotations

import os
from typing import Protocol

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import DeliveryJob, PositionCreate, VehicleAsset, VehiclePosition, VehicleSummary


class FleetStore(Protocol):
    def vehicles(self, operator_id: str) -> list[VehicleAsset]: ...
    def positions(self, region_code: str | None, limit: int) -> list[VehicleSummary]: ...
    def record_position(self, payload: PositionCreate, operator_id: str) -> VehiclePosition: ...
    def deliveries(self, region_code: str | None, limit: int) -> list[DeliveryJob]: ...


class PostgresFleetStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("Fleet tracking requires DATABASE_URL")
        return psycopg.connect(self.database_url, sslmode="require", row_factory=dict_row)

    def positions(self, region_code: str | None, limit: int) -> list[VehicleSummary]:
        where, params = "", []
        if region_code:
            where, params = "where v.region_code=%s", [region_code]
        with self._connect() as conn:
            rows = conn.execute(f"""select v.id::text vehicle_id,v.region_code,v.registration,v.vehicle_type,
                p.recorded_at,st_x(p.geom) lon,st_y(p.geom) lat,p.speed_kph,p.heading,p.status,p.accuracy_m
                from vehicle_assets v join lateral (select * from vehicle_positions p where p.vehicle_id=v.id
                order by p.recorded_at desc limit 1) p on true {where} and v.active order by p.recorded_at desc limit %s""",
                (*params, limit)).fetchall()
            return [VehicleSummary.model_validate(row) for row in rows]

    def vehicles(self, operator_id: str) -> list[VehicleAsset]:
        with self._connect() as conn:
            rows = conn.execute("""select id::text,region_code,registration,vehicle_type,active,metadata
                from vehicle_assets where operator_id=%s and active order by registration""", (operator_id,)).fetchall()
            return [VehicleAsset.model_validate(row) for row in rows]

    def record_position(self, payload: PositionCreate, operator_id: str) -> VehiclePosition:
        with self._connect() as conn:
            row = conn.execute("""insert into vehicle_positions(vehicle_id,recorded_at,geom,speed_kph,heading,status,accuracy_m,metadata)
                select id,%(recorded_at)s,st_setsrid(st_makepoint(%(lon)s,%(lat)s),4326),%(speed_kph)s,%(heading)s,%(status)s,%(accuracy_m)s,%(metadata)s
                from vehicle_assets where id=%(vehicle_id)s and operator_id=%(operator_id)s and active
                on conflict(vehicle_id,recorded_at) do update set metadata=excluded.metadata
                returning id::text,vehicle_id::text,recorded_at,st_x(geom) lon,st_y(geom) lat,speed_kph,heading,status,accuracy_m,metadata""",
                {**payload.model_dump(), "operator_id": operator_id, "metadata": Jsonb(payload.metadata)}).fetchone()
            if not row:
                raise LookupError("Vehicle is not assigned to this operator")
            return VehiclePosition.model_validate(row)

    def deliveries(self, region_code: str | None, limit: int) -> list[DeliveryJob]:
        with self._connect() as conn:
            if region_code:
                rows = conn.execute("select id::text,vehicle_id::text,region_code,commodity,origin_name,destination_name,status,eta_at,delivered_at,created_at,metadata from delivery_jobs where region_code=%s order by created_at desc limit %s", (region_code, limit)).fetchall()
            else:
                rows = conn.execute("select id::text,vehicle_id::text,region_code,commodity,origin_name,destination_name,status,eta_at,delivered_at,created_at,metadata from delivery_jobs order by created_at desc limit %s", (limit,)).fetchall()
            return [DeliveryJob.model_validate(row) for row in rows]
