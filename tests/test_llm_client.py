import pytest
try:
    from ftg.utils.llm_client import chat
    HAVE_CHAT = True
except Exception:
    HAVE_CHAT = False

@pytest.mark.asyncio
@pytest.mark.skipif(not HAVE_CHAT, reason="LLM client not found")
async def test_llm_chat_trims_output(monkeypatch):
    import httpx
    long_text = "A"*10000
    class DummyResp:
        def __init__(self): self._json = {"choices":[{"message":{"content": long_text}}]}
        def json(self): return self._json
        def raise_for_status(self): pass
    async def ok_post(*args, **kwargs): return DummyResp()
    monkeypatch.setattr(httpx.AsyncClient, "post", ok_post, raising=True)
    out = await chat("prompt")
    assert isinstance(out, str) and len(out) <= 4096