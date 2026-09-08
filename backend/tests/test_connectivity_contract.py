from unittest.mock import MagicMock

from app.alerts import PostgresAlertStore


def test_connectivity_accepts_unknown_and_timestamp(monkeypatch):
    store = PostgresAlertStore('unused')
    connection = MagicMock()
    connection.__enter__.return_value.execute.return_value.fetchall.return_value = [{
        'region_code': 'assam', 'state_name': 'Assam', 'active_events': 0,
        'blocked_events': 0, 'restricted_events': 0, 'status': 'unknown',
        'last_event_at': None,
    }]
    monkeypatch.setattr(store, '_connect', lambda: connection)
    result = store.connectivity('assam')
    assert result[0].status == 'unknown'
    assert result[0].last_event_at is None
    sql, params = connection.__enter__.return_value.execute.call_args.args
    assert "count(e.id)=0 then 'unknown'" in sql
    assert params == ('assam',)
