# Orby Web Agent

A web agent framework using WARC file servers and BrowserGym environments for automated web interaction and benchmarking.

📖 **[View Full Documentation](https://orby-ai-engineering.github.io/warc-bench/)** | 🐙 **[GitHub Repository](https://github.com/orby-ai-engineering/warc-bench)**

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/orby-ai-engineering/warc-bench.git
cd warc-bench

# Install in editable mode
pip install -e .
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

### Importing Modules

```python
# Import the main package
import orby

# Import subtask benchmark components
from orby.subtask_benchmark import config, evaluator

# Import agent implementations
from orby.digitalagent.agent import SvaV4
from orby.digitalagent.model import FoundationModel

# Import utilities
from orby.prompt_utils import template

# Import protocol buffers for visualization
from orby.protos.fm import action_data_pb2, trajectory_data_pb2
```

### Key Agent: SvaV4

The main agent implementation is `SvaV4`, located in `src/orby/digitalagent/agent/sva_v4.py`. This is a pure-vision agent designed for short-horizon tasks (typically 5 steps or less).

**Features:**
- Single model call for efficiency
- Combined task completion evaluation and action generation
- Supports BrowserGym actions: click, type, scroll, hover, drag_and_release, key_press, wait, complete

**Example:**
```python
from orby.digitalagent.agent.sva_v4 import SvaV4
from orby.digitalagent.model import FoundationModel

agent = SvaV4(
    actions="browsergym",
    model_configs={"executor": {"model": "claude-3-opus"}},
)
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
Benchmark runner that provides:
- WARC file rendering and serving
- Task evaluation framework
- Environment configurations
- Synthetic data generation

**Key Modules:**
- `environments/`: Environment setup and configuration
- `evaluator/`: Task completion verification
- `webreplay-standalone/`: Node.js WARC server

### 2. `orby.digitalagent`
Agent implementations and evaluation framework:
- Multiple agent architectures (primary: `sva_v4`)
- Foundation model interfaces (OpenAI, Anthropic, Fireworks)
- Evaluation runners and metrics
- Trajectory recording and visualization

**Key Agent Files:**
- `agent/sva_v4.py`: Main vision agent (keep)
- `agent/agent.py`: Base agent class
- `model/fm.py`: Foundation model interface
- `evaluation/eval_runner.py`: Evaluation orchestration

### 3. `orby.prompt_utils`
Utilities for managing prompt templates:
- Template loading and formatting
- Prompt composition helpers

### 4. `orby.protos`
Protocol buffer definitions for visualization:
- Action data structures
- LLM interaction data
- Trajectory data for recording agent behavior

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

### Running Scripts

```bash
# Test package imports
python scripts/test_imports.py

# Check WARC server
python scripts/webreplay_server_check.py
```

### Adding New Agents

New agent implementations should:
1. Extend `orby.digitalagent.agent.Agent` base class
2. Be placed in `src/orby/digitalagent/agent/`
3. Follow the pattern established by `sva_v4.py`

## Dependencies

Core dependencies (see `pyproject.toml` for full list):
- `playwright>=1.48.0` - Browser automation
- `openai==1.55.3` - OpenAI API
- `anthropic==0.40.0` - Anthropic API
- `browsergym~=0.13.3` - Browser gym environment
- `torch==2.3.1` - PyTorch for ML models
- `transformers==4.46.2` - Hugging Face transformers
- `streamlit==1.39.0` - Visualization UI

## License

MIT

## Contributing

This is an academic research project. Please ensure all contributions maintain compatibility with BrowserGym environments and follow the established agent architecture patterns.
