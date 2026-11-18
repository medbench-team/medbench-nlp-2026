from medbench.llm.cache import LLMResponse, ResponseCache, cache_key

MSG = [{"role": "user", "content": "q"}]
GEN = {"temperature": 0, "reasoning": True, "num_predict": 8192}


def test_key_stable_and_sensitive():
    k = cache_key("m", MSG, GEN, "v1")
    assert k == cache_key("m", MSG, dict(reversed(list(GEN.items()))), "v1")
    assert k != cache_key("m2", MSG, GEN, "v1")
    assert k != cache_key("m", [{"role": "user", "content": "q2"}], GEN, "v1")
    assert k != cache_key("m", MSG, GEN, "v2")


def test_roundtrip_and_no_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "secret-value-123")
    cache = ResponseCache(tmp_path / "c.sqlite")
    key = cache_key("m", MSG, GEN, "v1")
    assert cache.get(key) is None
    resp = LLMResponse(content="Ответ: да", reasoning_chars=10, input_tokens=5, output_tokens=7, latency_s=0.5)
    cache.put(key, "m", resp)
    assert cache.get(key) == resp
    assert cache.count() == 1
    cache.close()
    assert b"secret-value-123" not in (tmp_path / "c.sqlite").read_bytes()
