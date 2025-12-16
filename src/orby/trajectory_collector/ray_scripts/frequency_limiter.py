"""
Class to limit the frequency of requests to a certain number per time window.
"""

import ray
import time
from collections import deque


@ray.remote
class FrequencyLimiter:
    def __init__(self, request_limit, time_window_sec):
        """
        Limit the frequency of requests to a certain number per time window.

        Args:
            request_limit (int): The number of requests allowed per time window.
            time_window_sec (int): The time window in seconds.
        """
        self.request_limit = request_limit
        self.time_window_sec = time_window_sec
        self.action_time_queue = deque()

    def wait_for(self) -> int:
        """
        Get the time needed to wait for the next request.

        Returns:
            int: The time needed to wait in seconds.
        """
        # print("FrequencyLimiter: current queue length", len(self.action_time_queue))
        if len(self.action_time_queue) >= self.request_limit:
            gap = self.action_time_queue[0] + self.time_window_sec - time.time()
            if gap > 0:
                print(f"FrequencyLimiter: waiting for {gap} secs...")
                self.action_time_queue.popleft()
                return gap
        return 0

    def update(self):
        """
        Record the timestamp of the current request.
        """
        timestamp = int(time.time())
        self.action_time_queue.append(timestamp)
        while len(self.action_time_queue) > self.request_limit:
            self.action_time_queue.popleft()
