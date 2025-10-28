from orby.digitalagent.agent.sva_v3 import SvaV3
from orby.protos.fm.trajectory_data_pb2 import TrajectoryData
from orby.digitalagent.actions.browsergym_actions import complete
from orby.digitalagent.utils import file_utils
from orby.trajectory_collector.utils import data_utils


class ReplaySvaV3(SvaV3):
    """
    The ReplaySvaV3 agent replays actions from a recorded trajectory.
    It takes a TrajectoryData proto and replays its actions in sequence.
    It also verifies that the screenshots match the ones in the original trajectory.
    """

    def __init__(
        self,
        actions: str,
        model_configs: dict,
        reward_model_configs: dict | None = None,
        action_history_length: int = -1,
        image_mse_threshold: float = 0.02,
        replay_params: dict = {},
    ):
        # Initialize with empty model configs since we won't use them
        super().__init__(
            actions=actions,
            model_configs=model_configs,
            reward_model_configs=reward_model_configs,
            action_history_length=action_history_length,
        )
        self.image_mse_threshold = image_mse_threshold

        self.replay_params = replay_params
        assert "replay_trajectory_proto" in self.replay_params, "replay_trajectory_proto is required"
        trajectory = TrajectoryData()
        with file_utils.open(self.replay_params["replay_trajectory_proto"], "rb") as f:
            trajectory.ParseFromString(f.read())
        self.original_trajectory = trajectory

    def reset(self, goal, html, screenshot, goal_image_urls=[]):
        super().reset(goal, html, screenshot, goal_image_urls)
        self.current_step = 0
        self.replay_failed = False
        if (
            self.original_trajectory.actions[0].browser_gym_action.action_string
            == "START_OF_TRAJECTORY"
        ):
            print("Skipping first step START_OF_TRAJECTORY")
            self.current_step = 1

    def update(self, html, screenshot, trace):
        super().update(html, screenshot, trace)

        # Verify screenshot matches the one in trajectory
        # Skip verification for first step
        if self.current_step > 0 and self.current_step < len(
            self.original_trajectory.actions
        ):
            expected_screenshot = self.original_trajectory.actions[
                self.current_step
            ].before_state.viewport.screenshot.content
            if data_utils.screenshots_differ(
                screenshot,
                expected_screenshot,
                self.image_mse_threshold,
                normalize=True,
            ):
                self.replay_failed = True

    def act(self, **kwargs):
        return self._act(**kwargs)

    def _act(self, **kwargs):
        """Wrapper to avoid duplicate tracing when calling from child class"""
        if self.replay_failed:
            return complete(infeasible_reason="Replay failed"), {}

        # Get the current step from the trajectory
        action_data = self.original_trajectory.actions[self.current_step]
        action_string = action_data.browser_gym_action.action_string
        action_state = action_data.agent_state
        self.llm_trace.append(action_state.llm_interactions)

        # Parse the last LLM interaction to get the action and thinking.
        executor_response = self._parse_model_response(action_state.llm_interactions[-1].response)
        self.response_history.append(
            [executor_response.thinking, executor_response.action]
        )

        if self.action_history_length > 0:
            self.response_history = self.response_history[-self.action_history_length :]

        # Increment the step counter
        self.current_step += 1

        # If this is the last step, check if we should return a complete action
        if self.current_step >= len(self.original_trajectory.actions):
            if self.original_trajectory.HasField("success"):
                return complete(answer=self.original_trajectory.success.answer), {}
            else:
                return (
                    complete(infeasible_reason=self.original_trajectory.failure.reason),
                    {},
                )

        # Otherwise return the action from the trajectory
        print("Replaying action:", action_string)
        return action_string, {}


class ReplayAndGenerateSvaV3(ReplaySvaV3):
    def __init__(
        self,
        actions: str,
        model_configs: dict,
        reward_model_configs: dict | None = None,
        action_history_length: int = -1,
        image_mse_threshold: float = 0.02,
        replay_params: dict = {},
    ):
        super().__init__(
            actions,
            model_configs,
            reward_model_configs,
            action_history_length,
            image_mse_threshold,
            replay_params,
        )
        assert (
            "replay_skip_last_steps" in self.replay_params
        ), "replay_skip_last_steps is required"
        self.replay_skip_last_steps = self.replay_params["replay_skip_last_steps"]
        self.replay_steps = (
            len(self.original_trajectory.actions) - self.replay_skip_last_steps
        )

    def act(self, **kwargs):
        if self.current_step < self.replay_steps:
            # Replay the trajectory
            return super()._act(**kwargs)
        elif self.current_step >= self.replay_steps:
            # Call the original act method to generate new action
            return super(ReplaySvaV3, self)._act(**kwargs)
