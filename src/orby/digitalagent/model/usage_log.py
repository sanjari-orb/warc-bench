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
    write_usage_record({
        "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
        "provider": "anthropic", "model": model, "latency_s": round(latency_s, 2),
        "input_uncached": u.input_tokens or 0,
        "input_cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
        "input_cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "output": u.output_tokens or 0, "reasoning": None,
        "stop_reason": raw.stop_reason,
    })


def log_openai_usage(model: str, raw, latency_s: float) -> None:
    u = raw.usage
    prompt = u.prompt_tokens or 0
    cached = (getattr(u.prompt_tokens_details, "cached_tokens", 0) or 0) if u.prompt_tokens_details else 0
    reasoning = (getattr(u.completion_tokens_details, "reasoning_tokens", 0) or 0) if u.completion_tokens_details else 0
    write_usage_record({
        "event": "llm_call", "task": os.environ.get("EVAL_TASK_ID"), "time": time.time(),
        "provider": "openai", "model": model, "latency_s": round(latency_s, 2),
        # OpenAI's prompt_tokens includes cached tokens; split them so both providers report alike.
        "input_uncached": prompt - cached, "input_cache_read": cached, "input_cache_write": 0,
        # completion_tokens includes reasoning tokens.
        "output": u.completion_tokens or 0, "reasoning": reasoning,
        "stop_reason": raw.choices[0].finish_reason if raw.choices else None,
    })
