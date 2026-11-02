"""The fallback from one model to the next. Run: python tests/run.py"""
from support_kg import *


def test_the_api_key_comes_from_the_environment_or_env_file():
    import os
    import tempfile
    from pathlib import Path
    import kg_llm
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            assert kg_llm._key("ANTHROPIC_API_KEY", "claude_API_KEY", path) is None
            path.write_text("OTHER=1\nclaude_API_KEY=abc123\n", encoding="utf-8")
            assert kg_llm._key("ANTHROPIC_API_KEY", "claude_API_KEY", path) == "abc123"
            path.write_text("claude_API_KEY_HERE:abc123\n", encoding="utf-8")
            assert kg_llm._key("ANTHROPIC_API_KEY", "claude_API_KEY", path) == "abc123"
            os.environ["ANTHROPIC_API_KEY"] = "from-shell"
            assert kg_llm._key("ANTHROPIC_API_KEY", "claude_API_KEY", path) == "from-shell"
    finally:
        os.environ.pop("ANTHROPIC_API_KEY", None)
        if saved:
            os.environ["ANTHROPIC_API_KEY"] = saved


def _chain(*models, question="who is james"):
    from kg_llm import ask_llm
    s = Substrate()
    try:
        return ask_llm(s, question, models=list(models))
    finally:
        s.close()


def _fails(why):
    def phrase(question, evidence):
        from kg_llm import LLMUnavailable
        raise LLMUnavailable(why)
    return phrase


def test_the_next_model_answers_when_one_fails():
    r = _chain(("claude", _fails("no credit")), ("gemini", lambda q, e: [GOOD_CLAIM]))
    assert r["source"] == "gemini" and r["answer"] == GOOD_CLAIM["text"], r
    assert r["tried"] == ["claude: no credit"], r


def test_the_next_model_answers_when_the_gate_refuses_one():
    bad = {"text": "James lives in Atlantis.", "evidence": "not in the evidence"}
    r = _chain(("gemini", lambda q, e: [bad]), ("ollama", lambda q, e: [GOOD_CLAIM]))
    assert r["source"] == "ollama" and "gate refused" in r["tried"][0], r


def test_the_walker_answers_when_every_model_fails():
    r = _chain(("claude", _fails("no credit")), ("gemini", _fails("quota")), ("ollama", _fails("stopped")))
    assert r["source"] == "walker", r
    for why in ("no credit", "quota", "stopped"):
        assert why in r["fallback_reason"], r


def test_gemini_and_ollama_replies_are_read():
    import json
    import kg_llm
    reply = json.dumps({"claims": [GOOD_CLAIM]})
    saved = kg_llm._post, kg_llm._key
    calls = []
    try:
        kg_llm._key = lambda *a: "secret"
        kg_llm._post = lambda url, body, headers=None, timeout=60: calls.append((url, headers)) or {
            "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": reply}]}}]}
        assert kg_llm._gemini("q", "e") == [GOOD_CLAIM]
        assert "secret" not in calls[0][0] and calls[0][1] == {"x-goog-api-key": "secret"}
        kg_llm._post = lambda url, body, headers=None, timeout=60: {"message": {"content": reply}}
        assert kg_llm._ollama("q", "e") == [GOOD_CLAIM]
        kg_llm._post = lambda url, body, headers=None, timeout=60: {
            "candidates": [{"finishReason": "SAFETY"}]}
        try:
            kg_llm._gemini("q", "e")
            assert False, "a stopped reply is not an answer"
        except kg_llm.LLMUnavailable as e:
            assert "SAFETY" in str(e)
    finally:
        kg_llm._post, kg_llm._key = saved


if __name__ == "__main__":
    run_tests(globals())
