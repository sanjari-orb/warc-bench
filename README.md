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

## Project Structure

This is a monorepo combining multiple components into a unified `orby` package:

```
warc-bench/
├── src/orby/                          # Main package namespace
│   ├── __init__.py
│   ├── subtask_benchmark/             # Benchmark runner with WARC server
│   │   ├── environments/              # Environment configurations
│   │   ├── replays/                   # WARC replay files
│   │   ├── webreplay-standalone/      # Node.js WARC server (requires npm build)
│   │   ├── config/                    # Configuration management
│   │   ├── utils/                     # Utility functions
│   │   ├── evaluator/                 # Task evaluation logic
│   │   └── synthetic_data_gen/        # Synthetic data generation
│   │
│   ├── digitalagent/                  # Agent implementations and evaluation
│   │   ├── agent/                     # Agent implementations (sva_v4, etc.)
│   │   ├── model/                     # Foundation model interfaces
│   │   ├── evaluation/                # Evaluation runners and metrics
│   │   ├── actions/                   # BrowserGym action definitions
│   │   ├── prompts/                   # Agent prompts
│   │   ├── utils/                     # Utilities (includes visualizer_utils)
│   │   ├── vision_grounder/           # Vision-based grounding
│   │   ├── rewards/                   # Reward models and trajectory evaluation
│   │   └── environments/              # Environment wrappers
│   │
│   ├── prompt_utils/                  # Prompt template management
│   │   ├── template.py                # Template handling
│   │   └── utils.py                   # Prompt utilities
│   │
│   └── protos/                        # Protocol buffer definitions
│       ├── fm/                        # Compiled protobuf files
│       │   ├── action_data_pb2.py
│       │   ├── llm_data_pb2.py
│       │   └── trajectory_data_pb2.py
│       ├── action_data.proto          # Proto definitions
│       ├── llm_data.proto
│       └── trajectory_data.proto
│
├── scripts/                           # Utility scripts
│   ├── test_imports.py                # Test package imports
│   ├── webreplay_server_check.py      # Verify WARC server
│   ├── generate_benchmark_json.py     # Generate benchmark data
│   └── analyze_task_types.py          # Task analysis
│
├── pyproject.toml                     # Unified package configuration
├── setup.py                           # Setup script
└── custom_build.py                    # Custom build for webreplay-standalone
```

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

# For development with additional tools
pip install -e ".[dev]"
```

The installation will automatically:
1. Install all Python dependencies from `pyproject.toml`
2. Build the `webreplay-standalone` Node.js binary for serving WARC files
3. Install the `orby` package with all submodules

### BrowserGym Dependency

This project depends on BrowserGym, which should be installed separately. The BrowserGym repository is located at `~/orby/BrowserGym`.

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

### Training with RLVR

WARC-Bench supports training with Reinforcement Learning with Verifiable Rewards (RLVR). The benchmark provides automatic reward signals based on task completion:

```python
from orby.digitalagent.rewards import verifiable_reward
from orby.digitalagent.evaluation import eval_loop

# Training loop with RLVR
for episode in range(num_episodes):
    trajectory = agent.run_episode(task)
    reward = verifiable_reward.compute(trajectory, task.goal)
    agent.update_policy(trajectory, reward)
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

## Migration Notes

This monorepo combines code from four previous repositories:

1. **subtask-benchmark** → `orby.subtask_benchmark`
   - Docker code removed
   - WARC server code retained

2. **digital-agent** → `orby.digitalagent`
   - Only `sva_v4` agent and dependencies kept
   - Visualization code simplified
   - Evaluation code retained

3. **prompt-template-manager** → `orby.prompt_utils`
   - Utils integrated for agent usage

4. **protos** → `orby.protos`
   - Visualization objects retained

### Import Changes

**Old imports:**
```python
from subtask_benchmark.config import Config
from prompt_template_manager import Template
from fm.trajectory_data_pb2 import TrajectoryData
```

**New imports:**
```python
from orby.subtask_benchmark.config import Config
from orby.prompt_utils import Template
from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
```

## Development

### Running Benchmark Scripts

```bash
# Test package imports
python scripts/test_imports.py

# Verify WARC server is working
python scripts/webreplay_server_check.py

# Generate benchmark statistics
python scripts/generate_benchmark_json.py

# Analyze task type distribution
python scripts/analyze_task_types.py
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

### Training Custom Models

```bash
# Supervised fine-tuning
python -m orby.digitalagent.evaluation.eval_runner \
    --mode train \
    --training_type sft \
    --model your-model

# RLVR training (after SFT)
python -m orby.digitalagent.evaluation.eval_runner \
    --mode train \
    --training_type rlvr \
    --checkpoint path/to/sft/model
```

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
