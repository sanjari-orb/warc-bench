# WARC-Bench: Web Archive Based Benchmark for GUI Subtask Executions

A challenging benchmark with 438 tasks for evaluating multimodal AI agents on web navigation subtasks using Web ARChive files for sandboxed, realistic interactions.

🌐 **[Project Website](https://sanjari-orb.github.io/warc-bench/)** | 📄 **[arXiv Paper](https://arxiv.org/abs/2510.09872)** | 📖 **[Documentation](https://orby-ai-engineering.github.io/warc-bench/)** | 🐙 **[GitHub](https://github.com/sanjari-orb/warc-bench)** | 📊 **[Dataset](#)**

---

## Overview

Training web agents to navigate complex, real-world websites requires them to master **subtasks** - short-horizon interactions on multiple UI components (e.g., choosing the correct date in a date picker, or scrolling in a container to extract information). WARC-Bench addresses this critical capability gap with:

- **438 diverse tasks** designed to evaluate multimodal AI agents on web subtasks
- **Sandboxed interactions** with dynamic and realistic webpages using Web ARChive files
- **Challenging benchmark**: Leading computer-use models achieve up to 64.8% success rate
- **Training support**: Includes infrastructure for supervised fine-tuning (SFT) and reinforcement learning with verifiable rewards (RLVR)

### Performance Benchmarks

| Approach | Success Rate |
|----------|-------------|
| Leading frontier models | 64.8% |
| SFT models | 48.8% |
| RLVR (over SFT) | 52.8% |

Our analysis shows that mastering these subtasks is essential for robust web planning and navigation - a capability not extensively evaluated by existing benchmarks.

---

## What are Subtasks?

Subtasks are fundamental, short-horizon interactions that agents must master to navigate real-world websites effectively. Examples include:

- **Date pickers**: Selecting specific dates across various calendar UI designs
- **Scrolling containers**: Extracting information by scrolling within specific page elements
- **Dropdown menus**: Navigating and selecting from complex multi-level dropdowns
- **Form interactions**: Filling out forms with proper validation and error handling
- **Dynamic content**: Interacting with JavaScript-heavy components that update asynchronously

These capabilities form the building blocks for more complex web navigation tasks.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/orby-ai-engineering/warc-bench.git
cd warc-bench

# Install in editable mode
pip install -e .

# Run benchmark evaluation
python scripts/run_evaluation.py --agent sva_v4 --model claude-3-opus
```

See the [full documentation site](https://orby-ai-engineering.github.io/warc-bench/) for detailed installation instructions and usage examples.

## Installation

### Prerequisites

- Python >= 3.9
- Node.js and npm (required for building the WARC server)
- Git

### Install from source

```bash
# Clone the repository
cd /path/to/warc-bench

# Install in editable mode
pip install -e .
```

The installation will automatically:
1. Install all Python dependencies from `pyproject.toml`
2. Build the `webreplay-standalone` Node.js binary for serving WARC files
3. Install the `orby` package with all submodules

### BrowserGym Dependency

This project depends on BrowserGym, which should be installed separately. 

## Usage

### Running Benchmark Evaluations

```python
# Import the main package
import orby
from orby.subtask_benchmark import config, evaluator
from orby.digitalagent.agent import SvaV4
from orby.digitalagent.evaluation import eval_runner

# Configure evaluation
eval_config = {
    "benchmark_name": "warc-bench",
    "num_tasks": 438,
    "agent_type": "sva_v4",
}

# Run evaluation
results = eval_runner.run_evaluation(eval_config)
```


### Agent Architecture: SvaV4

The main agent implementation is `SvaV4`, a pure-vision agent designed for short-horizon subtasks (typically 5 steps or less).

**Features:**
- Single model call for efficiency
- Combined task completion evaluation and action generation
- Supports BrowserGym actions: click, type, scroll, hover, drag_and_release, key_press, wait, complete

**Example:**
```python
from orby.digitalagent.agent.sva_v4 import SvaV4

agent = SvaV4(
    actions="browsergym",
    model_configs={"executor": {"model": "claude-3-opus"}},
)

# Run on a single task
result = agent.run_task(task_config)
```

### WARC Server

The `webreplay-standalone` directory contains a Node.js application that serves WARC (Web ARChive) files as live websites. This allows agents to interact with archived web pages.

**Building manually:**
```bash
cd src/orby/subtask_benchmark/webreplay-standalone
npm install
npm run build
```

## Package Components

### 1. `orby.subtask_benchmark`
Core benchmark infrastructure with 438 web navigation subtasks:
- **WARC file rendering**: Sandboxed replay of archived websites
- **Task evaluation**: Automated verification of task completion
- **438 diverse tasks**: Covering date pickers, scrolling, dropdowns, forms, and dynamic content
- **Synthetic data generation**: Tools for creating additional subtask variations

**Key Modules:**
- `environments/`: 438 task configurations and environment setups
- `evaluator/`: Automated task completion verification with verifiable rewards
- `webreplay-standalone/`: Node.js WARC server for sandboxed web interactions
- `synthetic_data_gen/`: Tools for generating new subtask variations

### 2. `orby.digitalagent`
Agent implementations and training infrastructure:
- **SvaV4 agent**: Vision-based agent for short-horizon subtasks
- **SFT training**: Supervised fine-tuning infrastructure
- **RLVR training**: Reinforcement learning with verifiable rewards
- **Foundation model interfaces**: OpenAI, Anthropic, Fireworks
- **Evaluation framework**: Comprehensive metrics and trajectory recording

**Key Modules:**
- `agent/sva_v4.py`: Main vision agent achieving 48.8% (SFT) / 52.8% (RLVR) success rate
- `agent/agent.py`: Base agent class for custom implementations
- `rewards/`: Verifiable reward computation for RLVR training
- `evaluation/`: Evaluation runners, metrics, and analysis tools
- `model/`: Foundation model interfaces for multiple providers

### 3. `orby.prompt_utils`
Prompt engineering utilities:
- Template loading and formatting
- Prompt composition helpers for task instructions

### 4. `orby.protos`
Protocol buffer definitions for data interchange:
- Action data structures (BrowserGym actions)
- LLM interaction logging
- Trajectory data for visualization and analysis


## Development

### Running Benchmark Scripts

```bash
# Verify WARC server is working
python scripts/webreplay_server_check.py
```

### Adding New Tasks

To add new subtasks to the benchmark:
1. Create WARC files for the target websites
2. Define task configurations in `src/orby/subtask_benchmark/environments/`
3. Implement verification logic in `src/orby/subtask_benchmark/evaluator/`
4. Add task metadata and goals

### Adding New Agents

New agent implementations should:
1. Extend `orby.digitalagent.agent.Agent` base class
2. Be placed in `src/orby/digitalagent/agent/`
3. Follow the pattern established by `sva_v4.py`
4. Support BrowserGym action space
5. Implement task completion detection


## Dependencies

Core dependencies (see `pyproject.toml` for full list):
- `playwright>=1.48.0` - Browser automation
- `openai==1.55.3` - OpenAI API
- `anthropic==0.40.0` - Anthropic API
- `browsergym~=0.13.3` - Browser gym environment
- `torch==2.3.1` - PyTorch for ML models
- `transformers==4.46.2` - Hugging Face transformers
- `streamlit==1.39.0` - Visualization UI

## Citation

If you use WARC-Bench in your research, please cite our paper:

```bibtex
@misc{srivastava2025warcbenchwebarchivebased,
    title={WARC-Bench: Web Archive Based Benchmark for GUI Subtask Executions},
    author={Sanjari Srivastava and Gang Li and Cheng Chang and Rishu Garg and Manpreet Kaur and Charlene Y. Lee and Yuezhang Li and Yining Mao and Ignacio Cases and Yanan Xie and Peng Qi},
    year={2025},
    eprint={2510.09872},
    archivePrefix={arXiv},
    primaryClass={cs.LG},
    url={https://arxiv.org/abs/2510.09872},
}
```

## License

MIT

## Contributing

This is an academic research project accompanying the paper "WARC-Bench: Web Archive Based Benchmark for GUI Subtask Executions" ([arXiv:2510.09872](https://arxiv.org/abs/2510.09872)).

We welcome contributions that:
- Add new subtask types to the benchmark
- Improve agent implementations and training methods
- Enhance evaluation metrics and analysis tools
- Maintain compatibility with BrowserGym environments

Please open an issue or pull request to discuss your contributions.
