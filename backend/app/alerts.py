from __future__ import annotations

import os
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from .models import Alert, ConnectivitySummary


class AlertStore(Protocol):
    def list_alerts(self, region_code: str | None, limit: int) -> list[Alert]: ...
    def connectivity(self, region_code: str | None) -> list[ConnectivitySummary]: ...


class PostgresAlertStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("Alerts require DATABASE_URL")
        return psycopg.connect(self.database_url, sslmode="require", row_factory=dict_row)

    def list_alerts(self, region_code: str | None, limit: int) -> list[Alert]:
        with self._connect() as conn:
            if region_code:
                rows = conn.execute("""select a.id::text,a.event_id::text,e.region_code,a.alert_type,a.severity,a.title,a.message_key,a.message_params,a.created_at,a.expires_at
                    from alerts a join accessibility_events e on e.id=a.event_id
                    where e.region_code=%s and (a.expires_at is null or a.expires_at>now())
                    order by a.created_at desc limit %s""", (region_code, limit)).fetchall()
            else:
                rows = conn.execute("""select a.id::text,a.event_id::text,e.region_code,a.alert_type,a.severity,a.title,a.message_key,a.message_params,a.created_at,a.expires_at
                    from alerts a join accessibility_events e on e.id=a.event_id
                    where a.expires_at is null or a.expires_at>now() order by a.created_at desc limit %s""", (limit,)).fetchall()
            return [Alert.model_validate(row) for row in rows]

    def connectivity(self, region_code: str | None) -> list[ConnectivitySummary]:
        with self._connect() as conn:
            params = (region_code,) if region_code else ()
            where = "where r.code=%s" if region_code else ""
            rows = conn.execute(f"""select r.code region_code,r.state_name,
                count(e.id)::int active_events,
                count(e.id) filter (where e.accessibility_status='blocked')::int blocked_events,
                count(e.id) filter (where e.accessibility_status='restricted')::int restricted_events,
                case when count(e.id)=0 then 'open' when count(e.id) filter (where e.accessibility_status='blocked')>0 then 'blocked' else 'restricted' end status,
                max(e.starts_at) last_event_at
                from region_catalog r left join accessibility_events e on e.region_code=r.code
                and e.starts_at<=now() and (e.ends_at is null or e.ends_at>now()) {where}
                group by r.code,r.state_name order by r.state_name""", (*params,)).fetchall()
            return [ConnectivitySummary.model_validate(row) for row in rows]
