| Model | Score (avg@k) | 95% CI | Task SE | Run SE | Cost / task | Duration mean / median / p90 (s) | Uncached in / task | Cached in / task | Cache write / task | Output / task | Reasoning / task | Cut-off calls | Refusals |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 90.28% (runs: 0.875 0.9167 0.9167) | 86.71% to 93.85% | 1.82% | 1.39% | $0.2694 | 101.8 / 46.4 / 202.6 | 34,036 | 13,256 | 67 | 6,513 | 6,012 | 7 | 0 |
| gpt-6-astra | 89.06% (runs: 0.8802 0.9115 0.8802) | 85.08% to 93.05% | 2.03% | 1.04% | $0.4558 | 51.5 / 38.5 / 96.2 | 41,816 | 818 | 0 | 737 | 420 | 0 | 0 |
| gpt-6.1-sol | 86.28% (runs: 0.875 0.8646 0.849) | 81.96% to 90.61% | 2.21% | 0.76% | $0.0929 | 55.9 / 40.1 / 103.2 | 42,358 | 637 | 0 | 816 | 484 | 0 | 0 |
| accounts/fireworks/models/kimi-k3 | 85.94% (runs: 0.8698 0.8646 0.8438) | 81.61% to 90.26% | 2.21% | 0.80% | $0.1884 | 96.5 / 47.6 / 208.9 | 47,505 | 5,321 | 0 | 2,954 | 2,443 | 0 | 0 |
| gemini-4-argon | 76.56% (runs: 0.7552 0.7448 0.7969) | 71.62% to 81.51% | 2.52% | 1.59% | $0.2325 | 237.7 / 163.4 / 488.9 | 61,249 | 106 | 0 | 11,001 | 10,410 | 6 | 3 |
| accounts/fireworks/models/deepseek-v4p1-flash-1017 | 70.49% (runs: 0.724 0.7188 0.6719) | 65.01% to 75.96% | 2.79% | 1.66% | $0.0194 | 108.2 / 50.1 / 276.6 | 28,189 | 12,475 | 0 | 9,023 | 8,587 | 2 | 0 |
| accounts/fireworks/models/muse-spark-open | 65.45% (runs: 0.6667 0.6615 0.6354) | 59.36% to 71.54% | 3.11% | 0.97% | $0.0998 | 193.9 / 106.7 / 485.0 | 56,875 | 16,450 | 0 | 6,180 | 5,351 | 0 | 0 |
| accounts/fireworks/models/minimax-m3p1-flash | 43.92% (runs: 0.3958 0.4635 0.4583) | 38.41% to 49.44% | 2.82% | 2.18% | $0.0135 | 180.2 / 105.0 / 425.3 | 27,815 | 23,549 | 0 | 14,977 | 14,103 | 0 | 0 |
| grok-4.7 | 35.59% (runs: 0.349 0.3646 0.3542) | 30.55% to 40.63% | 2.57% | 0.46% | $0.1497 | 256.1 / 30.8 / 968.9 | 24,944 | 15,565 | 0 | 15,340 | 15,095 | 0 | 0 |

Cost uses list prices from scripts/rate_card.json (dated 2026-10-19, 2026-10-21, 2026-10-23, 2026-11-09).
See NOTES.md, if present, for the setup and known issues behind these numbers.

Reruns (tasks that never got a real attempt; their rows were replaced, originals kept in report/*_tasks.before_<name>.csv):
- gpt-6-astra run1: 5 task(s) rerun (online.75, online.80, online.146, online.174, online.202), 4 passed on rerun, 4 changed result. Reason: openai.APIConnectionError ('Connection error.') ended the task; the error was not in the retry list.
- gpt-6-astra run2: 1 task(s) rerun (online.111), 1 passed on rerun, 1 changed result. Reason: Infrastructure error: BrowserType.connect_over_cdp timed out, so the browser never connected and the model never acted.
- gpt-6.1-sol run1: 1 task(s) rerun (online.144), 1 passed on rerun, 1 changed result. Reason: openai.APIConnectionError ('Connection error.') ended the task; the error was not in the retry list.
- gpt-6.1-sol run2: 2 task(s) rerun (online.164, online.168), 2 passed on rerun, 2 changed result. Reason: openai.APIConnectionError ('Connection error.') ended the task; the error was not in the retry list.
- gpt-6.1-sol run3: 5 task(s) rerun (online.64, online.65, online.66, online.112, online.148), 3 passed on rerun, 3 changed result. Reason: openai.APIConnectionError ('Connection error.') ended the task; the error was not in the retry list.
- gemini-4-argon run1: 1 task(s) rerun (online.99), 0 passed on rerun, 0 changed result. Reason: Infrastructure error: Page.goto timed out loading the start page, so the model never acted.
- gemini-4-argon run1: 1 task(s) rerun (online.99), 0 passed on rerun, 0 changed result. Reason: Infrastructure error in the first rerun: BrowserContext.cookies failed because the browser had closed, so the model never got a full attempt.
- gemini-4-argon run3: 1 task(s) rerun (online.198), 1 passed on rerun, 1 changed result. Reason: Infrastructure error: BrowserType.connect_over_cdp failed (ECONNREFUSED), so the browser never connected and the model never acted.
- accounts/fireworks/models/deepseek-v4p1-flash-1017 run1: 2 task(s) rerun (online.75, online.79), 1 passed on rerun, 1 changed result. Reason: Infrastructure error: BrowserType.connect_over_cdp timed out, so the browser never connected and the model never acted.
- accounts/fireworks/models/deepseek-v4p1-flash-1017 run2: 1 task(s) rerun (online.99), 1 passed on rerun, 1 changed result. Reason: Infrastructure error: BrowserType.connect_over_cdp timed out, so the browser never connected and the model never acted.
- accounts/fireworks/models/minimax-m3p1-flash run1: 1 task(s) rerun (online.96), 0 passed on rerun, 0 changed result. Reason: Infrastructure error: Page.goto timed out loading the start page, so the model never acted.
- grok-4.7 run1: 1 task(s) rerun (online.52), 1 passed on rerun, 1 changed result. Reason: Infrastructure error: BrowserType.connect_over_cdp timed out, so the browser never connected and the model never acted.
- grok-4.7 run2: 5 task(s) rerun (online.10, online.11, online.109, online.111, online.113), 3 passed on rerun, 3 changed result. Reason: Infrastructure error: xAI returned HTTP 503 (Service temporarily unavailable) through every client retry.
- grok-4.7 run2: 8 task(s) rerun (online.20, online.24, online.28, online.34, online.195, online.196, online.197, online.199), 2 passed on rerun, 2 changed result. Reason: Infrastructure error: the browser closed during the task (BrowserContext.cookies: Target page, context or browser has been closed).
Tasks killed at the time limit have no recorded time and score 0. In the duration figures: claude-opus-5-5: 1 counted at 1,800 s, gemini-4-argon: 1 counted at 1,800 s, accounts/fireworks/models/minimax-m3p1-flash: 1 counted at 1,800 s, grok-4.7: 23 counted at 1,800 s.
