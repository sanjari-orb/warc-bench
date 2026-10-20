"""Append per-call token usage to the JSONL file named by LLM_USAGE_LOG."""

import json
import os
import time


def write_usage_record(record: dict) -> None:
    path = os.environ.get("LLM_USAGE_LOG")
    if not path:
        return
    record = dict(record, pid=os.getpid())
    # One write per line keeps records from different worker processes intact.
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def log_anthropic_usage(model: str, raw, latency_s: float) -> None:
    u = raw.usage
    # Newer models report thinking tokens (a part of output_tokens) under
    # output_tokens_details. Older SDK versions don't declare that field, so
    # read it from the extra fields. None means the API did not report it.
    details = getattr(u, "output_tokens_details", None) or (getattr(u, "model_extra", None) or {}).get("output_tokens_details")
    if isinstance(details, dict):
        reasoning = details.get("thinking_tokens")
    else:
        reasoning = getattr(details, "thinking_tokens", None) if details is not None else None
    write_usage_record({
        "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
        "provider": "anthropic", "model": model, "latency_s": round(latency_s, 2),
        "input_uncached": u.input_tokens or 0,
        "input_cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
        "input_cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "output": u.output_tokens or 0, "reasoning": reasoning,
        "stop_reason": raw.stop_reason,
    })


def log_openai_usage(model: str, raw, latency_s: float, provider: str = "openai") -> None:
    u = raw.usage
    if u is None:
        # Never drop a call silently: a missing record would under-count cost.
        write_usage_record({
            "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
            "provider": provider, "model": model, "latency_s": round(latency_s, 2),
            "usage_missing": True,
            "stop_reason": raw.choices[0].finish_reason if raw.choices else None,
        })
        return
    prompt = u.prompt_tokens or 0
    details = u.prompt_tokens_details
    cached = (getattr(details, "cached_tokens", 0) or 0) if details else 0
    # Some models (such as gpt-5.6-sol) also report cache_write_tokens. Older
    # SDK versions don't declare that field, so read it from the extra fields.
    cache_write = 0
    if details is not None:
        cache_write = getattr(details, "cache_write_tokens", None) or (getattr(details, "model_extra", None) or {}).get("cache_write_tokens") or 0
    reasoning = (getattr(u.completion_tokens_details, "reasoning_tokens", 0) or 0) if u.completion_tokens_details else 0
    write_usage_record({
        "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
        "provider": provider, "model": model, "latency_s": round(latency_s, 2),
        # OpenAI's prompt_tokens includes cached and cache-written tokens; split
        # them out so both providers report alike.
        "input_uncached": max(prompt - cached - cache_write, 0), "input_cache_read": cached,
        "input_cache_write": cache_write,
        # completion_tokens includes reasoning tokens.
        "output": u.completion_tokens or 0, "reasoning": reasoning,
        "stop_reason": raw.choices[0].finish_reason if raw.choices else None,
    })
