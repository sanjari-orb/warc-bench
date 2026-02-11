# Trajectory Viewer Guide

The trajectory viewer is a local Streamlit-based web application that allows you to visualize and inspect agent trajectories from evaluation runs.

## Overview

When you run evaluations with the `debug_dir` parameter, the system saves:
- `trajectory.pb.xz`: Compressed protobuf file containing the full trajectory data
- `results.json`: Summary metrics (reward, steps, agent info)
- Screenshots and agent reasoning for each step

## Setup

### 1. Ensure Streamlit is installed

Streamlit should already be installed via `requirements.txt`:
```bash
pip install streamlit
```

### 2. Run evaluations with local output

Update your evaluation config YAML to save outputs locally (instead of S3):

```yaml
# scripts/eval_configs/example.yaml
run_name: my_eval

runner:
  threads: 4
  output_dir: ./eval_outputs  # Use local path to save trajectories (not S3!)
  timeout_secs: 600

model_configs:
  claude:
    provider: anthropic
    name: claude-sonnet-4-20250514
    temperature: 0

agents:
  run1:
    name: sva_v4
    model_config_name: claude

benchmarks:
  subtaskbench:
    dataset: subtaskbench_test
    max_steps: 20
    headless: false
    example_ids:
      - browsergym/subtaskbench.online.0
      - browsergym/subtaskbench.online.1
```

**Important**: The `output_dir` in the `runner` section determines where trajectories are saved. Use a local path (e.g., `./eval_outputs`) instead of an S3 path (e.g., `s3://bucket/path`) to view trajectories locally.

### 3. Run your evaluation

```bash
python scripts/run_eval.py scripts/eval_configs/example.yaml
```

This will save trajectories in the `eval_outputs/` directory with structure:
```
eval_outputs/
├── browsergym_subtaskbench.online.0/
│   ├── trajectory.pb.xz
│   └── results.json
├── browsergym_subtaskbench.online.1/
│   ├── trajectory.pb.xz
│   └── results.json
...
```

## Using the Viewer

### Launch the viewer

```bash
streamlit run scripts/trajectory_viewer.py
```

This will:
1. Open your browser automatically (usually at http://localhost:8501)
2. Display the trajectory viewer interface

### Viewer Interface

The viewer has two main sections:

#### Sidebar (Configuration)
- **Evaluation Output Directory**: Path to where your trajectories are saved (default: `./eval_outputs`)
- **Select Trajectory**: Dropdown to choose which trajectory to view

#### Main Panel
- **Metadata Bar**: Shows success/failure status, reward, number of steps, agent name, and model
- **Goal**: Displays the task goal that the agent was trying to achieve
- **Trajectory Steps**: Expandable sections for each action taken by the agent

#### Step Details
Each step shows:
- **Action**: The BrowserGym action that was executed
- **Agent Reasoning**: The model's chain-of-thought or reasoning (if available)
- **Screenshot**: Visual snapshot after the action was taken (with click locations highlighted)
- **Full Observation**: Collapsed section with detailed environment feedback

## Features

### Visual Feedback
- Screenshots show the webpage state after each action
- Click locations are highlighted with red rectangles when available
- Success/failure indicators with color coding

### Agent Introspection
- View the agent's reasoning and thought process
- See the exact action strings executed
- Inspect LLM interactions and responses

### Navigation
- Easy browsing between multiple trajectories
- Expandable/collapsible steps for focused inspection
- Metrics summary at a glance

## Troubleshooting

### No trajectories found
**Problem**: The viewer shows "No trajectories found"

**Solutions**:
1. Make sure you ran evaluations with `debug_dir` set in your config
2. Check that the directory path in the sidebar is correct
3. Verify that `.pb.xz` files exist in the output directory

### Error loading trajectory
**Problem**: "Error loading trajectory: [error message]"

**Solutions**:
1. Ensure the protobuf files are not corrupted
2. Check that you have the correct version of the `orby` package installed
3. Verify that the trajectory was saved completely (evaluation didn't crash mid-save)

### Screenshots not displaying
**Problem**: "No screenshot available" or image loading errors

**Solutions**:
1. Some older trajectories may not have screenshot data
2. Check that the viewport data is being saved correctly in newer runs
3. Ensure PIL/Pillow is installed: `pip install Pillow`

## Advanced Usage

### Custom Output Directory

You can specify a different output directory in the sidebar text input. The viewer will recursively search for all `trajectory.pb.xz` files.

### Batch Viewing

To view multiple evaluation runs:
1. Organize them in separate subdirectories under your base output dir
2. The viewer will find all trajectories recursively
3. Use the dropdown to switch between different runs

### Exporting Data

To programmatically access trajectory data:

```python
import lzma
from orby.protos.fm.trajectory_data_pb2 import TrajectoryData

# Load a trajectory
with lzma.open("eval_outputs/task_id/trajectory.pb.xz", 'rb') as f:
    trajectory = TrajectoryData()
    trajectory.ParseFromString(f.read())

# Access data
print(f"Goal: {trajectory.goal}")
print(f"Number of actions: {len(trajectory.actions)}")

for i, action in enumerate(trajectory.actions):
    print(f"Step {i}: {action.browser_gym_action.action_string}")
```

## Comparison to Previous Orby Website

The previous trajectory viewer was hosted on the internal Orby website and required:
- Uploading trajectories to S3
- Access to internal infrastructure
- Network connectivity to view

This **local viewer** provides:
- ✅ No external dependencies
- ✅ Works completely offline
- ✅ Instant access without uploads
- ✅ Privacy - your data stays local
- ✅ Easy to customize and extend
- ✅ Open source and portable

## Future Enhancements

Potential improvements you can add:
- Side-by-side comparison of multiple trajectories
- Filtering by success/failure
- Search functionality for specific actions
- Export to video/GIF
- Performance metrics visualization
- Diff view between consecutive screenshots
