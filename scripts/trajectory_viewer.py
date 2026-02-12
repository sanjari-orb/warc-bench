"""
Local Trajectory Viewer using Streamlit

This app allows you to view agent trajectories saved during evaluation.
Run with: streamlit run scripts/trajectory_viewer.py
"""

import streamlit as st
import os
import json
import lzma
from pathlib import Path

from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from orby.digitalagent.utils.visualizer_utils import (
    viewport_to_image,
    find_action_string,
    _result,
)


def load_trajectory(trajectory_path: str) -> TrajectoryData:
    """Load a trajectory from a .pb.xz file."""
    with lzma.open(trajectory_path, 'rb') as f:
        trajectory_data = TrajectoryData()
        trajectory_data.ParseFromString(f.read())
        return trajectory_data


def load_results_json(results_path: str) -> dict:
    """Load results.json file if it exists."""
    if os.path.exists(results_path):
        with open(results_path, 'r') as f:
            return json.load(f)
    return {}


def find_trajectory_dirs(base_dir: str) -> list:
    """Find all directories containing trajectory files."""
    trajectory_dirs = []
    base_path = Path(base_dir)

    if not base_path.exists():
        return []

    for trajectory_file in base_path.rglob("trajectory.pb.xz"):
        trajectory_dirs.append(str(trajectory_file.parent))

    return sorted(trajectory_dirs)


def main():
    st.set_page_config(page_title="WARC-Bench Trajectory Viewer", layout="wide")

    st.title("🔍 WARC-Bench Trajectory Viewer")
    st.markdown("View agent trajectories from evaluation runs")

    # Sidebar for directory selection
    with st.sidebar:
        st.header("Configuration")

        # Input for base directory
        base_dir = st.text_input(
            "Evaluation Output Directory",
            value="./eval_outputs",
            help="Directory containing evaluation outputs with trajectory files"
        )

        if not os.path.exists(base_dir):
            st.warning(f"Directory '{base_dir}' does not exist. Please create it or specify a valid path.")
            st.info("Trajectories are saved when you run evaluations with a debug_dir parameter.")
            return

        # Find all trajectory directories
        trajectory_dirs = find_trajectory_dirs(base_dir)

        if not trajectory_dirs:
            st.warning(f"No trajectories found in '{base_dir}'")
            st.info("""
            To generate trajectories, run evaluations with a debug directory:
            ```python
            # In your eval config YAML:
            debug_dir: ./eval_outputs
            ```
            """)
            return

        st.success(f"Found {len(trajectory_dirs)} trajectories")

        # Select a trajectory
        selected_dir = st.selectbox(
            "Select Trajectory",
            trajectory_dirs,
            format_func=lambda x: os.path.basename(x)
        )

    # Main content area
    if selected_dir:
        trajectory_path = os.path.join(selected_dir, "trajectory.pb.xz")
        results_path = os.path.join(selected_dir, "results.json")

        try:
            # Load trajectory and results
            trajectory = load_trajectory(trajectory_path)
            results = load_results_json(results_path)

            # Display metadata
            col1, col2, col3 = st.columns(3)

            with col1:
                result_status, result_msg = _result(trajectory)
                if "succeeded" in result_status:
                    st.success(f"✅ {result_status}")
                else:
                    st.error(f"❌ {result_status}")
                st.caption(result_msg)

            with col2:
                if results:
                    st.metric("Reward", results.get("reward", "N/A"))
                    st.metric("Steps", results.get("steps", len(trajectory.actions)))

            with col3:
                if results:
                    st.caption("**Agent**")
                    st.text(results.get("agent_name", "N/A"))
                    st.caption("**Model**")
                    model_config = json.loads(results.get("model_configs", "{}"))
                    st.text(model_config.get("name", "N/A"))

            # Display goal
            st.subheader("🎯 Goal")
            st.info(trajectory.goal if trajectory.goal else results.get("goal", "No goal specified"))

            # Display trajectory steps
            st.subheader("📋 Trajectory Steps")

            if len(trajectory.actions) == 0:
                st.warning("No actions recorded in this trajectory")
                return

            # Create tabs for each step
            for idx, action_data in enumerate(trajectory.actions):
                with st.expander(f"**Step {idx + 1}**: {find_action_string(action_data)[:100]}", expanded=(idx == 0)):
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.caption("**Action**")
                        st.code(find_action_string(action_data), language="python")

                        # Display agent prompt and thinking if available
                        if action_data.agent_state and action_data.agent_state.llm_interactions:
                            st.caption("**LLM Interaction**")
                            for llm_idx, interaction in enumerate(action_data.agent_state.llm_interactions):
                                with st.container():
                                    # Display model info
                                    if interaction.model_name:
                                        st.text(f"Model: {interaction.model_name}")

                                    # Display prompt (llm_messages)
                                    if interaction.llm_messages:
                                        st.caption("**Prompt Messages:**")
                                        for msg_idx, message in enumerate(interaction.llm_messages):
                                            # Format the message content
                                            content_parts = []
                                            for content in message.llm_contents:
                                                if content.text:
                                                    content_parts.append(content.text)
                                                elif content.image_url:
                                                    content_parts.append(f"[Image: {content.image_url}]")

                                            message_text = "\n".join(content_parts) if content_parts else "(empty message)"

                                            st.text_area(
                                                f"{message.role.capitalize()} Message",
                                                message_text,
                                                height=150,
                                                key=f"prompt_{idx}_{llm_idx}_{msg_idx}"
                                            )

                                    # Display response
                                    if interaction.response:
                                        st.caption("**Model Response:**")
                                        st.text_area(
                                            "Response",
                                            interaction.response,
                                            height=150,
                                            key=f"response_{idx}_{llm_idx}"
                                        )

                        # Show observation details below the reasoning (not nested)
                        if action_data.after_state and action_data.after_state.browser_gym_observation:
                            obs = action_data.after_state.browser_gym_observation
                            show_obs = st.checkbox("Show Full Observation", key=f"show_obs_{idx}")
                            if show_obs:
                                st.json({
                                    "reward": obs.reward,
                                    "terminated": obs.terminated,
                                    "truncated": obs.truncated,
                                    "last_action": obs.last_action,
                                    "last_action_error": obs.last_action_error,
                                })

                    with col2:
                        # Display screenshot
                        st.caption("**Screenshot (After Action)**")
                        if action_data.after_state and action_data.after_state.viewport:
                            try:
                                image = viewport_to_image(action_data.after_state.viewport, action_data)
                                st.image(image, use_column_width=True)
                            except Exception as e:
                                st.error(f"Could not load screenshot: {e}")
                        else:
                            st.info("No screenshot available for this step")

        except Exception as e:
            st.error(f"Error loading trajectory: {e}")
            st.exception(e)


if __name__ == "__main__":
    main()
