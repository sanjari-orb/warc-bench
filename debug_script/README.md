# Debug scripts

Tools used to find and fix broken benchmark environments. Run them from the
repo root after `pip install -e .` and building the replay server. For the
test split, set `SUBTASK_BENCHMARK_FILE=benchmark_test.json`.

| Script | Use it to |
|---|---|
| `check_envs.py` | Load every task, screenshot its start page, and run its evaluator on the untouched page. Flags tasks that error, come up blank, or pass without any action. |
| `check_run.py` | Check a finished eval run: blank screenshots, pages that stayed blank all run, model notes about blank or error pages, task errors, and tasks that hit the step limit. |
| `dump_llm_calls.py` | Write every LLM call in a run (prompt text and reply) to a text file, or print one task's calls. |
| `inspect_task.py` | Load one task and list the failed requests and script errors, optionally after replaying clicks. A 404 means the archive does not have that page or script. |

Token use and task times come from running with `LLM_USAGE_LOG` set; see
`scripts/usage_report.py`.

## How these found the October 2026 environment problems

- `check_run.py` showed every Zendesk task starting blank, and `check_envs.py`
  confirmed the start pages.
- `inspect_task.py --fresh-tab` showed Zoho Desk's service worker sending
  requests to the live site (a redirect to the login page), and a missing
  script chunk when the page clock was the real date.
- `inspect_task.py` on Google Earth showed "SharedArrayBuffer transfer
  requires self.crossOriginIsolated"; the archived page's origin trial token
  had expired.
- `inspect_task.py online.204 --click ...` showed the Zoho ticket editor's
  scripts returning 404: the archive never captured that view, so those tasks
  were left out of `benchmark_test_whitelist.json`.
- `check_envs.py` found `online.118`, whose evaluator passes on the untouched
  page.
