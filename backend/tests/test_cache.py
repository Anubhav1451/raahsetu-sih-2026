from app.cache import cache_clear, cache_get, cache_set


def test_cache_round_trip_with_local_fallback(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache_clear()
    cache_set("test:key", {"value": 42}, 30)
    assert cache_get("test:key") == {"value": 42}


def test_cache_expiry(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache_clear()
    cache_set("test:expiry", {"value": 1}, 0)
    assert cache_get("test:expiry") is None
