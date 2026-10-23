import pytest

import ai_cache
import klog
import session


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Тесты не трогают реальные logs/kesha.log и data/ai_cache.json."""
    klog.set_path(tmp_path / "kesha.log")
    monkeypatch.setattr(ai_cache.cache, "path", tmp_path / "ai_cache.json")
    monkeypatch.setattr(ai_cache.cache, "_data", None)
    session.reset()
    yield
