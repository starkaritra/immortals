"""Pure translation/parse tests for the provider adapters (AS-030).

No network, no SDK, no API key: each adapter isolates the risky part — mapping normalized
chat/tool types to and from the provider wire format — into pure functions, which we exercise
directly against recorded-shape payloads (mirrors how ``test_copilot_backend`` tests
``_parse_jsonl``).
"""

from __future__ import annotations

import pytest

from immortals.runners.providers import (
    ChatMessage,
    FakeProvider,
    ProviderError,
    ToolCall,
    ToolSpec,
    Usage,
    get_provider,
)
from immortals.runners.providers import anthropic, gemini, ollama, openai


TOOLS = [ToolSpec(name="read_file", description="read a file", input_schema={
    "type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]})]

CONVO = [
    ChatMessage(role="user", content="do the thing"),
    ChatMessage(role="assistant", content="", tool_calls=[ToolCall(id="c1", name="read_file",
                                                                   arguments={"path": "x"})]),
    ChatMessage(role="tool", content="file body", tool_call_id="c1"),
]


# -- registry ----------------------------------------------------------------------------

def test_get_provider_known_and_unknown():
    assert get_provider("fake").name == "fake"
    assert {"anthropic", "openai", "gemini", "ollama"}.issubset(
        set(__import__("immortals.runners.providers", fromlist=["PROVIDER_NAMES"]).PROVIDER_NAMES))
    with pytest.raises(ProviderError):
        get_provider("nope")


def test_missing_sdk_raises_clear_error(monkeypatch):
    prov = get_provider("anthropic", api_key="sk-test")
    monkeypatch.setitem(__import__("sys").modules, "anthropic", None)
    # importlib returns the module set to None -> ModuleNotFoundError path in _require.
    with pytest.raises(ProviderError) as exc:
        prov.complete(system="s", messages=[ChatMessage(role="user", content="hi")])
    assert "anthropic" in str(exc.value)


def test_missing_key_raises_before_import():
    with pytest.raises(ProviderError):
        get_provider("openai", api_key=None).complete(
            system="s", messages=[ChatMessage(role="user", content="hi")])


# -- Anthropic ---------------------------------------------------------------------------

def test_anthropic_tools_and_messages_and_parse():
    assert anthropic._to_wire_tools(TOOLS)[0]["input_schema"]["required"] == ["path"]
    wire = anthropic._to_wire_messages(CONVO)
    assert wire[1]["content"][0]["type"] == "tool_use"
    assert wire[2]["content"][0]["type"] == "tool_result"
    assert wire[2]["content"][0]["tool_use_id"] == "c1"
    resp = anthropic._parse_response({
        "content": [{"type": "text", "text": "hi"},
                    {"type": "tool_use", "id": "t1", "name": "read_file", "input": {"path": "y"}}],
        "model": "claude-x", "usage": {"input_tokens": 5, "output_tokens": 3},
        "stop_reason": "tool_use"})
    assert resp.text == "hi"
    assert resp.tool_calls[0].name == "read_file" and resp.tool_calls[0].arguments == {"path": "y"}
    assert resp.usage.total_tokens == 8


# -- OpenAI ------------------------------------------------------------------------------

def test_openai_messages_and_parse():
    wire = openai._to_wire_messages("SYS", CONVO)
    assert wire[0] == {"role": "system", "content": "SYS"}
    assert wire[2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert wire[3] == {"role": "tool", "tool_call_id": "c1", "content": "file body"}
    resp = openai._parse_response({
        "choices": [{"message": {"content": None, "tool_calls": [
            {"id": "c9", "function": {"name": "sh", "arguments": "{\"cmd\": \"ls\"}"}}]},
            "finish_reason": "tool_calls"}],
        "model": "gpt-x", "usage": {"prompt_tokens": 4, "completion_tokens": 2}})
    assert resp.tool_calls[0].arguments == {"cmd": "ls"}
    assert resp.usage.input_tokens == 4 and resp.usage.output_tokens == 2


def test_openai_bad_tool_args_are_not_fatal():
    resp = openai._parse_response({"choices": [{"message": {"content": "",
        "tool_calls": [{"id": "c1", "function": {"name": "f", "arguments": "not json"}}]}}],
        "usage": {}})
    assert resp.tool_calls[0].arguments == {"_raw": "not json"}


# -- Gemini ------------------------------------------------------------------------------

def test_gemini_contents_and_parse_synthesizes_call_id():
    contents = gemini._to_wire_contents(CONVO)
    assert contents[1]["role"] == "model"
    assert contents[1]["parts"][0]["function_call"]["name"] == "read_file"
    assert contents[2]["parts"][0]["function_response"]["name"] == "c1"
    resp = gemini._parse_response({
        "candidates": [{"content": {"parts": [
            {"functionCall": {"name": "search", "args": {"q": "z"}}}]}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 1}})
    assert resp.tool_calls[0].name == "search"
    assert resp.tool_calls[0].id == "search-0"  # synthesized (Gemini gives none)
    assert resp.usage.input_tokens == 7


# -- Ollama ------------------------------------------------------------------------------

def test_ollama_messages_and_parse():
    wire = ollama._to_wire_messages("SYS", CONVO)
    assert wire[0]["role"] == "system"
    assert wire[2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert wire[3]["role"] == "tool"
    resp = ollama._parse_response({"message": {"content": "",
        "tool_calls": [{"function": {"name": "w", "arguments": {"x": 1}}}]},
        "model": "llama", "prompt_eval_count": 9, "eval_count": 4})
    assert resp.tool_calls[0].name == "w" and resp.tool_calls[0].id == "w-0"
    assert resp.usage.total_tokens == 13


# -- Fake provider (script engine used by the runner tests) ------------------------------

def test_fake_provider_scripts_turns_in_order():
    from immortals.runners.providers.base import ProviderResponse

    fake = FakeProvider(turns=[
        ProviderResponse(tool_calls=[ToolCall(id="1", name="read_file", arguments={"path": "a"})]),
        ProviderResponse(text="done", usage=Usage(2, 2)),
    ])
    first = fake.complete(system="s", messages=[ChatMessage(role="user", content="go")], tools=TOOLS)
    assert first.tool_calls[0].name == "read_file"
    second = fake.complete(system="s", messages=[ChatMessage(role="user", content="go")])
    assert second.text == "done"
    # Exhausted script repeats the last turn.
    assert fake.complete(system="s", messages=[]).text == "done"
    assert len(fake.calls) == 3


def test_usage_add():
    assert (Usage(1, 2) + Usage(3, 4)).total_tokens == 10
