# WARC-Bench test split: setup and known issues

Results are in `results.md` and `results.csv`. This file explains how they
were produced and what affects them.

## Setup

- **Tasks:** the whitelisted test split, 192 tasks
  (`environments/benchmark_test_whitelist.json`), as of repo commit `763224d`,
  with online.65's goal corrected (see Known issues).
- **Runs:** 3 full runs per model, 8 workers each, one run at a time on one
  machine, 2026-10-19 to 2026-11-10. Score is avg@3.
- **Agent:** `sva_v4_note`, with prompt `sva_v4/20261019_note.jinja2`. This
  prompt asks for `<note>` and `<action>` tags. It also asks for only the
  requested value in answers, because 53 tasks are graded by exact string match.
- **Limits:** at most 20 steps per task, 1,800 s per task, `max_tokens`
  32,000 per call, and a 600 s request timeout.
- **Reasoning effort:** the highest each API accepts. That is `xhigh` for
  GPT-6.1 Sol and GPT-6 Astra (they reject `max`), `max` for Claude Opus 5.5,
  `max` for Kimi K3 and DeepSeek V4.1 Flash 1017 on Fireworks, and
  `thinking_level: high` for Gemini 4 Argon (its levels are minimal, low,
  medium and high), `max` for Muse Spark Open and MiniMax M3.1 Flash on Fireworks,
  and `xhigh` for Grok 4.7 (its levels are low, medium, high and xhigh).
- **Gemini access:** Google's recommended Interactions API through the
  `google-genai` SDK (`client.interactions.create`), standard service tier,
  `store=False`. Its durations were measured on the Gemini API
  (`generativelanguage.googleapis.com`).
- **Grok access:** xAI's API (`api.x.ai`) through its recommended Responses
  API, `store=False`. OpenRouter was tried first but limits new accounts to
  20 requests per minute for this model.
- **Timeouts:** a task that reaches the 1,800 s limit fails once. The harness
  used to rerun such a task up to 3 times and score the last attempt; that was
  removed before the Grok runs. In the earlier runs it happened once (Gemini 4
  Argon run 3, online.34, which failed both attempts), so no score changed, but
  that task's duration is understated (counted at 1,800 s; it ran about two
  limits).
- **Browser:** the replay browser runs in UTC, so date-picker tasks are graded
  the same on any machine.
- **Cost:** computed from token counts at list prices dated 2026-10-19
  (`scripts/rate_card.json`, which also gives the sources). Judge or grader
  tokens: none; all graders are programmatic.
- **Not included:** GLM 5.3, because `glm-5p3` on Fireworks does not accept
  images and this benchmark is screenshot-only.

## Differences from the October comparison runs

Those runs used `max_tokens` 16,000, a 600 s per-task limit, and the
providers' default reasoning effort. They also used the earlier
`20261016_note` prompt, which had no answer-format line, and a browser in the
machine's local time zone. Numbers here are not directly comparable to those.

## Known issues

**online.65 goal corrected (all runs rescored).** The goal asked for the
commit count of the `noise_emb` branch of `jimHalpert123/NeMo`. That fork has
only a `main` branch in the archive; the branch and the expected answer are in
`NVIDIA/NeMo`, where the task starts. No model passed it in any run. The goal
was corrected on 2026-10-21 (repo PR #8), and online.65 was rerun with the
corrected goal in every run; the results in this report use the corrected task
throughout.

**Infrastructure errors (rerun).** Following the rule that infrastructure
errors are rerun rather than scored, 33 task-runs were rerun, and each result
uses the rerun. `results.md` lists every one with its reason; originals are
kept in `report/*_tasks.before_<name>.csv`.
- OpenAI connection drops: 13 (8 GPT-6.1 Sol, 5 GPT-6 Astra). The error
  (`openai.APIConnectionError`) was not in the client's retry list, so each
  one scored 0 without a model answer. It is now retried.
- Browser closed during the task: 8 (Grok 4.7 run 2).
- Browser did not connect: 6 (DeepSeek runs 1 and 2, GPT-6 Astra run 2,
  Gemini 4 Argon run 3, Grok 4.7 run 1).
- HTTP 503 from xAI after every client retry: 5 (Grok 4.7 run 2).
- Start page did not load: 2 (Gemini 4 Argon run 1, MiniMax M3.1 Flash run 1).

Two reruns were redone: Gemini 4 Argon's online.99, whose first rerun also
hit a browser error, and Grok 4.7's 13 run 2 reruns, whose first attempt
overlapped with the machine sleeping. Every final rerun completed without an
infrastructure error.

**DeepSeek V4.1 Flash 1017 empty replies (not corrected).** In 39 of its 576
task-runs (6.8%), one call returned an empty answer and the task scored 0.
That was 39 of 4,897 calls (0.8%).
- In 37 of the 39, the call stopped normally. A diagnostic rerun with full
  responses logged showed that in this case DeepSeek writes a complete
  `<note>`/`<action>` without first ending its thinking section. Fireworks
  then returns everything as `reasoning_content` and leaves `content` empty,
  and the agent only reads `content`.
- The other 2 were real cut-offs at the 32,000-token limit.

Kimi K3, on the same Fireworks setup, never did this. DeepSeek's reported
70.49% counts all 39 as failures.

**Calls cut off at 32,000 tokens.** 7 for Claude Opus 5.5, 6 for Gemini 4
Argon and 2 for DeepSeek across all runs, and none for the other models. Each ended its task. In the
Opus cases, thinking grew step by step until it hit the cap, which looks
like the model getting stuck rather than needing more room.

**Tasks killed at the time limit.** 2: Claude Opus 5.5 run 3 (online.173)
and Gemini 4 Argon run 3 (online.34). Each scores 0 and counts at 1,800 s in
the duration figures.

**Gemini 4 Argon.**
- Refusals: Google's copyright/recitation filter blocked online.111 in all 3
  runs ("Request blocked due to copyright/recitation content"). These count
  as refusals and so as failures. The block comes back as an HTTP 400 error
  rather than a reply, so it was not logged at run time; the 3 records were
  added from the eval logs and are marked `reconstructed_from_eval_log`.
- Replies with no output: 1 (online.39, run 1). The call completed with 0
  output and 0 thinking tokens; it counts as a failure.
- Speed: it is the slowest model here (mean 238 s per task), because it
  writes about 11,000 output tokens per task at `high`, nearly all thinking.
  Its per-call fixed latency was also about 1 to 2 s higher than the other
  providers', with occasional spikes.

**Muse Spark Open.**
- Coordinates: Muse answers on a 0 to 1000 grid over the screenshot, not in
  pixels; the provider confirmed this ((0, 0) top-left, (1000, 1000)
  bottom-right). For Muse only, the prompt's pixel-coordinate sentence is
  replaced by one stating the grid, and action positions are converted to
  pixels with x = round(x * width / 1000), y = round(y * height / 1000),
  clamped to the grid and the screen. Every other model's prompt and actions
  are unchanged.
- Reply format failures (counted as failures): 44 of 576 task-runs (7.6%).
  33 replies had the action with no `<action>` tags, usually after a sentence
  addressed to the user (some of these answers were correct); 11 were not
  valid Python, such as a string broken across lines or a quote written as
  `''`. The prompt asks for the tags in the same way for every model.
- No infrastructure errors in its runs.

**MiniMax M3.1 Flash: coordinates (measured, not documented).** MiniMax
answers in the pixels of a smaller copy of the screenshot, not of the
1280 x 720 image it is sent: in a first smoke test it clicked (501, 82) for a
play button at (970, 152), and (36, 40) for a link at about (60, 75), so most
clicks missed. Neither Fireworks nor MiniMax documents this, so the scale was
measured: a 1280 x 720 test image with 8 numbered markers at known positions
(including near the right and bottom edges) was sent 3 times, and MiniMax was
asked for each marker's click position. Its answers fit a scale of 1.952 (x)
and 1.895 (y), that is an image of about 656 x 380; its largest values were
x 646 and y 365. After rescaling, the mean error was 18 px (worst 39 px).
For MiniMax only, positions are converted with x = round(x * 1280 / 656) and
y = round(y * 720 / 380), clamped to the grid and the screen
(`coordinate_space: scaled`, `coordinate_grid: [656, 380]`). Its prompt is
unchanged, since the scale was measured with it. The remaining error of about
20 px can still miss very small targets, so its score may be slightly
understated.

**MiniMax M3.1 Flash: other notes.**
- Reply format failures (counted as failures): 73 of 576 task-runs (12.7%).
  59 actions were not valid Python (often a mangled closing tag left inside
  the action, as in `click(310, 407)</`, or a string broken across lines),
  12 replies had no action tags, and 2 gave `complete(answer=...)` a number
  instead of a string.
- It often uses all 20 steps (about 12 to 13 steps per task on average).
- Run scores vary more than for other models (39.58%, 46.35%, 45.83%).
- Serving speed varied between runs: median call latency was 3.2 s in run 1
  (evening), 6.5 s in run 2 and 5.6 s in run 3 (daytime), with the local
  browser time per step unchanged, so its duration figures partly reflect
  Fireworks load.
- Infrastructure reruns: 1 (start page did not load, run 1).

**Grok 4.7: missing closing tag (counted as failures).** Grok often ends its
reply right after a complete, correct action, without the closing `</action>`
tag, for example:

```
<note>
The page shows a course detail view; I will click Home in the left sidebar to start the requested path.
</note>
<action>
click(66, 75)
```

The response reports a normal finish, and the tag is nowhere else in the
response (including the reasoning fields). Under the benchmark's strict
format rule the reply has no parseable action, so the step fails and the task
scores 0, as for every other model.
- Frequency on the same first-step request: 9 of 12 missing through xAI's
  API at `xhigh`; through OpenRouter, 0 of 10 at `xhigh` and 3 of 10 at
  `high`. In a partial OpenRouter run (stopped and not counted) it hit about
  16% of 395 calls.
- It is not a harness or serving cut-off. No stop sequences or prefill are
  sent, and when Grok was asked to write `</action>` with more text after it
  (for example `<action>click(1, 2)</action>` then the word FINISHED), the tag
  came back every time (9 of 9). It goes missing only when it would be the
  last thing in the reply.
- In Grok's counted runs it ended 273 of 576 task-runs (47.4%), which is the
  main reason for its score. Its median task time (31 s) is low because so
  many tasks end on the first step.
- Among the other models only Muse Spark Open did this, 2 times in 576
  task-runs.

**Grok 4.7: other failures.** 23 task-runs were killed at the 1,800 s limit
(Grok often thinks for 2 to 4 minutes per step at `xhigh`), and 1 answered
with a number instead of a string (`complete(answer=<int>)`). Infrastructure
reruns: 1 browser-connect timeout, 8 browser crashes and 5 HTTP 503 responses
from xAI (listed in `results.md`). A first attempt at 13 of these reruns
overlapped with the machine sleeping, so it was discarded and redone.

**Prompt caching.** The GPT models and Gemini 4 Argon read almost nothing from
cache (under 1,000 tokens per task), because their requests include screenshots. Their cost is
nearly all uncached input.

**Live-site dependency.** online.95 to online.98 (the Scrimba video tasks)
stream the video from the live site, because the archive does not contain it.
Their expected answers match the live site as of 2026-10-19.

**Refusals:** none for any model.

## Code used

- Claude Opus 5.5, GPT-6.1 Sol, GPT-6 Astra, Kimi K3 and DeepSeek V4.1 Flash 1017:
  repo commit `763224d` with `openai==1.55.3`. Their online.65 and
  infrastructure reruns used the later code below.
- Gemini 4 Argon and Muse Spark Open: the code merged as repo PR #7, with the
  online.65 fix (PR #8), `openai==1.55.3` and `google-genai==2.32.0`.
- Grok 4.7: repo main after PR #7 and #8 plus PR #9 (xAI provider, upload
  check, no timeout retry), with `openai==3.37.0`.
- MiniMax M3.1 Flash: repo main at `668fa01` plus PR #10 (scaled coordinate
  conversion), with `openai==3.37.0`.
