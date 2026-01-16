from backend.app.services.summarizer import build_context, make_prompt, summarize_answer
import backend.app.services.summarizer as summarizer


def test_build_context_formats_chunks():
    chunks = [
        {"file_path": "a.md", "text": "hello", "score": 0.9},
        {"file_path": "b.md", "text": "world", "score": 0.8},
    ]
    ctx = build_context(chunks)
    assert "[1]" in ctx and "a.md" in ctx and "hello" in ctx
    assert "[2]" in ctx and "b.md" in ctx and "world" in ctx

def test_make_prompt_contains_notes_and_question():
    prompt = make_prompt("What is X?", "some context")
    assert "NOTES BEGIN" in prompt
    assert "some context" in prompt
    assert "Question: What is X?" in prompt

def test_summarize_answer_uses_mock_llm(monkeypatch):
    monkeypatch.setattr(summarizer, "call_llm", lambda prompt: "MOCKED")
    out = summarize_answer("What is the gradient?", "The gradient points uphill.")
    assert out == "MOCKED"
