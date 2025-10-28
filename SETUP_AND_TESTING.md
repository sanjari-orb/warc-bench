# Setup and Testing Instructions

This guide provides step-by-step instructions for setting up and running evaluations with the Orby Web Agent framework.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running Evaluations](#running-evaluations)
5. [Test Runs](#test-runs)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **Python**: 3.9 or higher (tested with Python 3.12)
- **Node.js**: v16 or higher (required for WARC server)
- **npm**: Latest version
- **Git**: For cloning repositories
- **Memory**: At least 8GB RAM recommended
- **Storage**: At least 10GB free space

### External Dependencies
- **BrowserGym**: Must be installed separately from `~/orby/BrowserGym`
- **Playwright browsers**: Will be installed automatically

---

## Installation

### Step 1: Clone the Repository

```bash
cd /path/to/your/workspace
git clone https://github.com/orby-ai-engineering/warc-bench.git
cd warc-bench
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
python3.12 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### Step 3: Install the Package

```bash
# Install in editable mode with all dependencies
pip install -e .

# This will:
# 1. Install all Python dependencies from pyproject.toml
# 2. Build the webreplay-standalone Node.js WARC server
# 3. Install the orby package with all submodules
```

**Note**: The installation may take 5-10 minutes as it builds the WARC server and downloads dependencies.

### Step 4: Install Playwright Browsers

```bash
playwright install
```

### Step 5: Verify Installation

```bash
# Test package imports
python scripts/test_imports.py

# Expected output:
# Successfully imported orby version 0.1.0
# ✅ Successfully imported orby.subtask_benchmark.config
# ✅ Successfully imported orby.subtask_benchmark.evaluator
# ✅ Successfully imported orby.subtask_benchmark.utils
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root (if not already present):

```bash
# API Keys for LLM providers
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here

# Optional: Weights & Biases for experiment tracking
WANDB_API_KEY=your_wandb_key_here

# Optional: AWS credentials for S3 output storage
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

### Evaluation Configuration

Evaluation configs are located in `scripts/eval_configs/`. The main config is `subtask.yaml`:

```yaml
# scripts/eval_configs/subtask.yaml
run_name: test                    # Name for this evaluation run

runner:
  threads: 4                      # Number of parallel threads
  output_dir: ./results           # Local output (or s3://bucket/path)
  wandb_project: sva_benchmark    # W&B project name (optional)
  seed: 17                        # Random seed for reproducibility
  timeout_secs: 600               # Timeout per task (10 minutes)

model_configs:
  claude:
    provider: anthropic
    name: claude-sonnet-4-20250514
    temperature: 0

agents:
  run1:
    name: sva_v4                  # Use the SvaV4 agent
    model_config_name: claude

benchmarks:
  subtaskbench:
    dataset: subtaskbench_test
    max_examples: -1              # -1 for all examples
    max_steps: 20
    headless: false               # Set to true for headless mode
    reset_env: false
```

### Customizing the Configuration

Create a copy for your test run:

```bash
cp scripts/eval_configs/subtask.yaml scripts/eval_configs/my_test.yaml
```

Edit `my_test.yaml`:

```yaml
run_name: my_first_test
runner:
  threads: 1                      # Start with 1 thread for testing
  output_dir: ./test_results      # Local directory
  timeout_secs: 300               # 5 minutes for quick tests

benchmarks:
  subtaskbench:
    max_examples: 5               # Test with just 5 examples
    headless: true                # Run in headless mode
```

---

## Running Evaluations

### Basic Usage

The evaluation runner is located at `scripts/run_eval.py`. Use it with:

```bash
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml
```

### Command-Line Options

```bash
# Basic run (default: uses BrowserGym directly)
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml

# With WebArena service
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml --use_wa_service

# With subprocess spawning (requires use_wa_service)
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml --use_wa_service --subprocess

# With elastic client (distributed execution)
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml --elastic_client

# Limit number of IPs for distributed execution
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml --elastic_client --max_ips 3
```

### Example Run Command

```bash
# Full evaluation with all examples
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml

# Quick test with 5 examples
python3.12 scripts/run_eval.py scripts/eval_configs/my_test.yaml
```

---

## Test Runs

### Test 1: Verify Installation

```bash
# Test basic imports
python3.12 -c "
from orby.digitalagent.agent.sva_v4 import SvaV4
from orby.digitalagent.evaluation import eval_runner
print('✅ All imports successful!')
"
```

### Test 2: Sanity Check Evaluation

```bash
# Run sanity check with minimal config
python3.12 scripts/run_eval.py scripts/eval_configs/sanity_check.yaml
```

This will run a quick sanity check to ensure:
- Agent can be initialized
- BrowserGym environment works
- WARC server starts correctly
- Tasks can be executed

**Expected time**: 2-5 minutes

### Test 3: Small Subset Test

Create a test config:

```bash
cat > scripts/eval_configs/quick_test.yaml << 'EOF'
run_name: quick_test

runner:
  threads: 1
  output_dir: ./test_results
  seed: 42
  timeout_secs: 180

model_configs:
  claude:
    provider: anthropic
    name: claude-sonnet-4-20250514
    temperature: 0

agents:
  test_run:
    name: sva_v4
    model_config_name: claude

benchmarks:
  subtaskbench:
    dataset: subtaskbench_test
    max_examples: 3
    max_steps: 10
    headless: true
    reset_env: false
EOF
```

Run it:

```bash
python3.12 scripts/run_eval.py scripts/eval_configs/quick_test.yaml
```

**Expected time**: 5-10 minutes

### Test 4: Full Evaluation

Once tests pass, run the full evaluation:

```bash
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml
```

**Expected time**: Depends on:
- Number of examples (subtask benchmark has ~200 examples)
- Number of threads (default: 4)
- Model response time
- Typical full run: 2-4 hours

---

## Understanding the Output

### Console Output

During execution, you'll see:

```
Starting evaluation: test
Loading agent: sva_v4
Loading benchmark: subtaskbench_test
Processing 5/200 examples...

Task: browsergym/subtaskbench.online.1
  Status: success
  Steps: 3
  Time: 12.5s

Task: browsergym/subtaskbench.online.2
  Status: failed
  Steps: 5
  Time: 18.2s
  Error: Timeout

...

=== Results ===
Success Rate: 75.0% (3/4)
Average Steps: 4.2
Total Time: 45.3s
```

### Output Files

Results are saved to the configured `output_dir`:

```
test_results/
├── run_name_timestamp/
│   ├── config.yaml           # Copy of the config used
│   ├── results.json          # Detailed results for each task
│   ├── summary.json          # Aggregated metrics
│   └── trajectories/         # Step-by-step trajectories
│       ├── task_1.json
│       ├── task_2.json
│       └── ...
```

### Results JSON Structure

```json
{
  "run_name": "test",
  "success_rate": 0.75,
  "total_tasks": 4,
  "successful_tasks": 3,
  "failed_tasks": 1,
  "average_steps": 4.2,
  "average_time": 11.3,
  "tasks": [
    {
      "task_id": "browsergym/subtaskbench.online.1",
      "status": "success",
      "steps": 3,
      "time": 12.5,
      "trajectory": [...]
    }
  ]
}
```

---

## Troubleshooting

### Issue: Import Errors

**Error**: `ModuleNotFoundError: No module named 'orby'`

**Solution**:
```bash
# Reinstall the package
pip install -e .

# Verify Python is using the correct environment
which python
python -c "import sys; print(sys.path)"
```

### Issue: WARC Server Not Building

**Error**: `Error: npm not found. Please install Node.js and npm.`

**Solution**:
```bash
# Install Node.js and npm
# macOS:
brew install node

# Ubuntu/Debian:
sudo apt install nodejs npm

# Then rebuild
cd src/orby/subtask_benchmark/webreplay-standalone
npm install
npm run build
```

### Issue: Playwright Browser Not Found

**Error**: `Executable doesn't exist at /path/to/browser`

**Solution**:
```bash
# Install Playwright browsers
playwright install chromium

# Or install all browsers
playwright install
```

### Issue: API Key Not Found

**Error**: `AuthenticationError: No API key provided`

**Solution**:
```bash
# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
EOF

# Or export directly
export ANTHROPIC_API_KEY=your_key_here
```

### Issue: Timeout Errors

**Error**: Tasks timing out frequently

**Solution**:
- Increase `timeout_secs` in config
- Reduce `max_steps` for faster completion
- Check internet connection (for online tasks)
- Reduce `threads` to avoid resource contention

### Issue: Memory Errors

**Error**: `MemoryError` or system slowdown

**Solution**:
- Reduce `threads` in config (try threads: 1 or 2)
- Close other applications
- Use `headless: true` in config
- Increase system swap space

### Issue: CUDA/GPU Errors

**Error**: CUDA or GPU-related errors

**Solution**:
The package uses CPU-only PyTorch by default. If you need GPU:

```bash
# Uninstall CPU version
pip uninstall torch

# Install GPU version
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

---

## Advanced Usage

### Running with Different Agents

Edit the config to use different agents:

```yaml
agents:
  run1:
    name: sva_v3  # Or other available agents
    model_config_name: claude
```

Available agents in `src/orby/digitalagent/agent/`:
- `sva_v4` (recommended)
- `sva_v3`
- `sva_v2`
- Other agents (check directory)

### Using Different Models

```yaml
model_configs:
  gpt4:
    provider: openai
    name: gpt-4-turbo
    temperature: 0

  claude_opus:
    provider: anthropic
    name: claude-3-opus-20240229
    temperature: 0

agents:
  gpt4_run:
    name: sva_v4
    model_config_name: gpt4

  claude_run:
    name: sva_v4
    model_config_name: claude_opus
```

### Running Multiple Agents in Parallel

```yaml
agents:
  claude_run:
    name: sva_v4
    model_config_name: claude

  gpt4_run:
    name: sva_v4
    model_config_name: gpt4
```

### Using Weights & Biases

```yaml
runner:
  wandb_project: my_project
  wandb_entity: my_team  # Optional
```

Ensure `WANDB_API_KEY` is set in `.env`.

---

## Performance Tips

### For Faster Evaluation
1. Use `headless: true` in config
2. Increase `threads` (but watch resource usage)
3. Use `max_examples: N` for subset testing
4. Reduce `max_steps` for simpler tasks

### For Better Accuracy
1. Use `temperature: 0` for deterministic results
2. Set a consistent `seed` for reproducibility
3. Use higher-quality models (claude-opus, gpt-4)
4. Increase `timeout_secs` for complex tasks

### For Cost Optimization
1. Start with small `max_examples` for testing
2. Use cheaper models (claude-haiku, gpt-3.5)
3. Monitor token usage in W&B

---

## Next Steps

After successful test runs:

1. **Run full evaluation**: Use the complete config with `max_examples: -1`
2. **Analyze results**: Check the results JSON and trajectories
3. **Experiment**: Try different agents, models, or configurations
4. **Contribute**: Share improvements and findings

For more details, see:
- [README.md](README.md) - Project overview
- [Documentation Site](https://orby-ai-engineering.github.io/warc-bench/) - Full documentation
- [GitHub Issues](https://github.com/orby-ai-engineering/warc-bench/issues) - Report problems

---

## Quick Reference

```bash
# Full installation
pip install -e . && playwright install

# Test installation
python scripts/test_imports.py

# Quick test run (3 examples)
python3.12 scripts/run_eval.py scripts/eval_configs/quick_test.yaml

# Full evaluation
python3.12 scripts/run_eval.py scripts/eval_configs/subtask.yaml

# Check results
ls -la test_results/
cat test_results/*/summary.json
```
