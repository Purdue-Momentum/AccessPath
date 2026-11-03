"""Purdue chat completions with bounded retries, shared throttling and safe accounting."""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.utils import timezone

from .configuration import option
from .contract import ContractError, _check
from .models import LLMCall, ProviderSlot

ENDPOINT = "https://genai.rcac.purdue.edu/api/chat/completions"


class ProviderError(Exception):
    """Safe to report: never contains keys, provider bodies or lecture content."""


class RetryableProviderError(ProviderError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward bearer credentials to a redirected host.


@dataclass
class Completion:
    data: dict
    model: str


def wait_for_slot(key):
    """At most one request per 3.2 seconds for this key across app workers."""
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    ProviderSlot.objects.get_or_create(key_hash=key_hash, defaults={"next_allowed_at": timezone.now()})
    for _ in range(40):
        now = timezone.now()
        if ProviderSlot.objects.filter(key_hash=key_hash, next_allowed_at__lte=now).update(
            next_allowed_at=now + timedelta(seconds=3.2)
        ):
            return
        time.sleep(1)
    raise RetryableProviderError("provider_busy")


def _tokens(usage, name):
    value = usage.get(name, 0)
    return value if type(value) is int and 0 <= value <= 2_147_483_647 else 0


def _request(body, key):
    request = Request(ENDPOINT, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
    })
    try:
        with build_opener(NoRedirect()).open(request, timeout=120) as response:
            raw = response.read(4_000_001)
    except HTTPError as exc:
        if exc.code == 429 or exc.code >= 500:
            raise RetryableProviderError(f"http_{exc.code}") from None
        raise ProviderError(f"http_{exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise RetryableProviderError("network_error") from None
    if len(raw) > 4_000_000:
        raise ProviderError("response_too_large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise RetryableProviderError("invalid_provider_json") from None
    if payload is None:
        raise RetryableProviderError("provider_returned_null")
    if not isinstance(payload, dict):
        raise ProviderError("invalid_provider_response")
    return payload


def complete(*, model, messages, schema, klass_id, source_file_id, purpose, prompt_version, node_id=None):
    key = option("GENAI_API_KEY", "").strip()
    if not key:
        raise ProviderError("missing_genai_api_key")
    backend = option("GENAI_BACKEND", "vllm")
    body = {"model": model, "messages": messages, "stream": False, "max_tokens": 8192, "temperature": 0}
    if backend == "vllm":
        body["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "accesspath_nodes", "schema": schema,
        }}
    elif backend == "ollama":
        body["format"] = schema
    else:
        raise ProviderError("unsupported_genai_backend")
    for attempt in range(3):
        wait_for_slot(key)
        call = LLMCall.objects.create(
            klass_id=klass_id, source_file_id=source_file_id, node_id=node_id, purpose=purpose,
            model=model, prompt_version=prompt_version, provider="purdue", status="started", cost_usd=None,
        )
        started = time.monotonic()
        retry = False
        try:
            payload = _request(body, key)
            usage = payload.get("usage") or {}
            if isinstance(usage, dict):
                call.input_tokens = _tokens(usage, "prompt_tokens")
                call.output_tokens = _tokens(usage, "completion_tokens")
                details = usage.get("prompt_tokens_details") or {}
                if isinstance(details, dict):
                    call.cache_read_tokens = _tokens(details, "cached_tokens")
            reported_model = payload.get("model")
            if isinstance(reported_model, str) and reported_model:
                call.model = reported_model[:100]
            request_id = payload.get("id")
            if isinstance(request_id, str):
                call.provider_request_id = request_id[:200]
            try:
                choice = payload["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ProviderError("incomplete_generation")
                message = choice["message"]
                if message.get("refusal"):
                    raise ProviderError("model_refusal")
                data = json.loads(message["content"])
                _check(data, schema, "response")
            except (KeyError, IndexError, TypeError, ValueError, ContractError):
                raise ProviderError("invalid_structured_output") from None
            call.status = "succeeded"
            return Completion(data, call.model)
        except RetryableProviderError as exc:
            call.status, call.error_code = "failed", str(exc)
            if attempt == 2:
                raise
            retry = True
        except ProviderError as exc:
            call.status, call.error_code = "failed", str(exc)
            raise
        finally:
            call.latency_ms = min(int((time.monotonic() - started) * 1000), 2_147_483_647)
            call.save()
        if retry:
            time.sleep(5 * (attempt + 1))
    raise ProviderError("attempts_exhausted")
