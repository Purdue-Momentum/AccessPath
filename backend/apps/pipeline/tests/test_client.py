import json
from unittest.mock import Mock

import pytest

from apps.pipeline import client
from apps.pipeline.models import LLMCall

SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}},
          "required": ["answer"], "additionalProperties": False}


@pytest.fixture
def call(make_user, settings, monkeypatch):
    from apps.classes.services import create_class
    klass = create_class(user=make_user(), name="Test")
    settings.GENAI_API_KEY = "test-key-not-a-real-secret"
    monkeypatch.setattr(client, "wait_for_slot", Mock())
    monkeypatch.setattr(client.time, "sleep", Mock())
    def invoke():
        return client.complete(model="test-model", messages=[], schema=SCHEMA, klass_id=klass.pk,
                               source_file_id=None, purpose="test", prompt_version="test-v1")
    return invoke


def response(content=None, reason="stop"):
    return {"id": "request-123", "model": "served-model", "choices": [{"finish_reason": reason,
            "message": {"content": json.dumps(content or {"answer": "ok"})}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "prompt_tokens_details": {"cached_tokens": 3}}}


def test_success_and_usage(call, monkeypatch):
    request = Mock(return_value=response())
    monkeypatch.setattr(client, "_request", request)
    result = call()
    assert result.data == {"answer": "ok"} and result.model == "served-model"
    assert request.call_args.args[0]["response_format"]["json_schema"]["schema"] == SCHEMA
    entry = LLMCall.objects.get()
    assert (entry.input_tokens, entry.output_tokens, entry.cache_read_tokens) == (12, 8, 3)
    assert entry.status == "succeeded" and entry.cost_usd is None


def test_ollama_shape(call, settings, monkeypatch):
    settings.GENAI_BACKEND = "ollama"
    request = Mock(return_value=response())
    monkeypatch.setattr(client, "_request", request)
    call()
    assert request.call_args.args[0]["format"] == SCHEMA
    assert "response_format" not in request.call_args.args[0]


def test_retry_logs_every_attempt(call, monkeypatch):
    request = Mock(side_effect=[client.RetryableProviderError("provider_returned_null"), response()])
    monkeypatch.setattr(client, "_request", request)
    call()
    assert request.call_count == 2
    assert set(LLMCall.objects.values_list("status", flat=True)) == {"failed", "succeeded"}


def test_retries_are_bounded(call, monkeypatch):
    request = Mock(side_effect=client.RetryableProviderError("http_429"))
    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(client.RetryableProviderError):
        call()
    assert request.call_count == LLMCall.objects.count() == 3


@pytest.mark.parametrize("payload,code", [(response(reason="length"), "incomplete_generation"),
                                         (response({"wrong": "shape"}), "invalid_structured_output"),
                                         ({"choices": []}, "invalid_structured_output")])
def test_invalid_responses(call, monkeypatch, payload, code):
    monkeypatch.setattr(client, "_request", Mock(return_value=payload))
    with pytest.raises(client.ProviderError, match=code):
        call()
    assert LLMCall.objects.get().status == "failed"


def test_missing_key(call, settings, monkeypatch):
    settings.GENAI_API_KEY = ""
    request = Mock()
    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(client.ProviderError, match="missing_genai_api_key"):
        call()
    request.assert_not_called()
    assert not LLMCall.objects.exists()


def test_request_null_is_retryable(monkeypatch):
    from contextlib import nullcontext
    reader = Mock()
    reader.read.return_value = b'null'
    opener = Mock()
    opener.open.return_value = nullcontext(reader)
    monkeypatch.setattr(client, "build_opener", Mock(return_value=opener))
    with pytest.raises(client.RetryableProviderError, match="provider_returned_null"):
        client._request({}, "fake")


@pytest.mark.parametrize("status,retryable", [(401, False), (429, True), (503, True), (302, False)])
def test_http_error_classification(monkeypatch, status, retryable):
    from urllib.error import HTTPError
    opener = Mock()
    opener.open.side_effect = HTTPError(client.ENDPOINT, status, "private body", {}, None)
    monkeypatch.setattr(client, "build_opener", Mock(return_value=opener))
    expected = client.RetryableProviderError if retryable else client.ProviderError
    with pytest.raises(expected, match=f"http_{status}"):
        client._request({}, "fake")


def test_provider_throttle_shares_slot(db, monkeypatch):
    from datetime import timedelta

    from django.utils import timezone

    from apps.pipeline.models import ProviderSlot
    monkeypatch.setattr(client.time, "sleep", Mock())
    client.wait_for_slot("synthetic-key")
    assert ProviderSlot.objects.count() == 1
    with pytest.raises(client.RetryableProviderError, match="provider_busy"):
        client.wait_for_slot("synthetic-key")
    ProviderSlot.objects.update(next_allowed_at=timezone.now()-timedelta(seconds=1))
    client.wait_for_slot("synthetic-key")
    assert ProviderSlot.objects.count() == 1
