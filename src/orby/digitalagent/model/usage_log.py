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
    # OpenRouter adds the call's cost (USD) to usage and names the provider
    # that served it; record both when present.
    extra = getattr(u, "model_extra", None) or {}
    served = (getattr(raw, "model_extra", None) or {}).get("provider")
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
        **({"provider_cost_usd": extra["cost"]} if extra.get("cost") is not None else {}),
        **({"served_by": served} if served else {}),
    })


def log_raw_response(raw) -> None:
    """Append the full response to the JSONL file named by LLM_RAW_LOG, if set.

    For debugging only: it keeps fields the agent ignores, such as
    reasoning_content, so a reply with an empty answer can be inspected.
    """
    path = os.environ.get("LLM_RAW_LOG")
    if not path:
        return
    try:
        body = raw.model_dump()
    except AttributeError:
        body = str(raw)
    with open(path, "a") as f:
        f.write(json.dumps({"task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
                            "pid": os.getpid(), "response": body}, default=str) + "\n")


# Interactions API status values mapped to the stop reasons usage_report.py counts.
_GEMINI_STOP = {"completed": "stop", "incomplete": "max_tokens", "budget_exceeded": "max_tokens", "blocked": "refusal"}


def log_gemini_usage(model: str, raw: dict, latency_s: float) -> None:
    """Log one Gemini Interactions API call.

    total_input_tokens includes the cached tokens, and total_output_tokens
    excludes thinking (total_tokens = input + output + thought), which Google
    bills as output.
    """
    u = raw.get("usage") or {}
    status = raw.get("status")
    inp = u.get("total_input_tokens") or 0
    cached = u.get("total_cached_tokens") or 0
    thoughts = u.get("total_thought_tokens") or 0
    has_output = any(s.get("type") == "model_output" for s in raw.get("steps") or [])
    stop = _GEMINI_STOP.get(status, status)
    if status == "completed" and not has_output:
        stop = "no_output"
    write_usage_record({
        "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
        "provider": "gemini", "model": model, "latency_s": round(latency_s, 2),
        "input_uncached": max(inp - cached, 0), "input_cache_read": cached,
        # Gemini has implicit caching only, with no separate write charge.
        "input_cache_write": 0,
        "output": (u.get("total_output_tokens") or 0) + thoughts, "reasoning": thoughts,
        "stop_reason": stop, "status_raw": status, "service_tier": raw.get("service_tier"),
        **({"usage_missing": True} if not u else {}),
    })


def log_xai_usage(model: str, raw, latency_s: float) -> None:
    """Log one xAI Responses API call.

    input_tokens includes cached_tokens, and output_tokens includes
    reasoning_tokens. xAI also returns the call's cost in ticks of 1e-10 USD.
    """
    u = raw.usage
    status = getattr(raw, "status", None)
    incomplete = getattr(getattr(raw, "incomplete_details", None), "reason", None)
    if u is None:
        write_usage_record({
            "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
            "provider": "xai", "model": model, "latency_s": round(latency_s, 2),
            "usage_missing": True, "stop_reason": status,
        })
        return
    inp = u.input_tokens or 0
    cached = (getattr(u.input_tokens_details, "cached_tokens", 0) or 0) if u.input_tokens_details else 0
    reasoning = (getattr(u.output_tokens_details, "reasoning_tokens", 0) or 0) if u.output_tokens_details else 0
    ticks = (getattr(u, "model_extra", None) or {}).get("cost_in_usd_ticks")
    stop = "stop" if status == "completed" else ("max_tokens" if incomplete == "max_output_tokens" else (incomplete or status))
    write_usage_record({
        "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
        "provider": "xai", "model": model, "latency_s": round(latency_s, 2),
        "input_uncached": max(inp - cached, 0), "input_cache_read": cached, "input_cache_write": 0,
        "output": u.output_tokens or 0, "reasoning": reasoning,
        "stop_reason": stop, "status_raw": status,
        **({"provider_cost_usd": ticks / 1e10} if ticks is not None else {}),
    })
