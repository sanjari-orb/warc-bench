import subprocess
import os
import orby.subtask_benchmark
from orby.subtask_benchmark.config import get_config
from pathlib import Path
import os
import signal
import atexit
import psutil
import time
import json
import threading
import shutil
from abc import ABC, abstractmethod


class WebServerSessionHandler(ABC):
    def __init__(self, task_id: str, debugging_port: int = 9222) -> None:
        """
        Initialize a WebServerSessionHandler.
        """
        self.task_id = task_id
        self.task_config = self.get_task_config(task_id)
        self.debugging_port = debugging_port

        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def get_task_config(self, task_id: str):
        # Load configuration using the config module
        all_configs = get_config()
        for config in all_configs:
            if config["task_id"] == task_id:
                return config
        raise ValueError(f"Task ID {task_id} not found in config file.")

    def _signal_handler(self, sig, frame):
        """Handle signals to ensure cleanup before exit"""
        self.cleanup()
        os._exit(0)

    def _kill_process_on_port(self, port):
        """Kill any process using the specified port"""
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    # Get connections separately
                    connections = proc.net_connections()
                    for conn in connections:
                        if hasattr(conn, "laddr") and conn.laddr.port == port:
                            print(
                                f"Killing process {proc.info['pid']} using port {port}"
                            )
                            try:
                                parent = psutil.Process(proc.info["pid"])
                                for child in parent.children(recursive=True):
                                    child.kill()
                                parent.kill()
                            except psutil.NoSuchProcess:
                                pass
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    # Skip processes we can't access
                    continue
        except Exception as e:
            print(f"Error checking processes on port {port}: {e}")

    def cleanup(self):
        """Cleanup when the server is destroyed."""
        try:
            if self.server_process:
                pgid = os.getpgid(self.server_process.pid)
                print(f"Cleaning up process group {pgid}")

                # First try graceful termination
                os.killpg(pgid, signal.SIGTERM)

                # Wait for a short time for graceful shutdown
                for _ in range(5):
                    if self.server_process.poll() is not None:
                        break
                    time.sleep(0.2)

                # If still running, force kill
                if self.server_process.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)

                self.server_process = None

            # Additionally, clean up any remaining processes on the port
            self._kill_process_on_port(self.debugging_port)
        except (ProcessLookupError, OSError) as e:
            print(f"Error during cleanup: {e}")

    @abstractmethod
    def construct_command(self):
        pass

    def _start_server(self, command: str):
        """Start the static web app server in the background."""
        # First check if port is already in use and kill processes
        self._kill_process_on_port(self.debugging_port)

        print(f"Starting server with command: {command}")
        self.server_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

        # Start a thread to read and print output
        server_ready = threading.Event()

        def read_output():
            while True:
                if not self.server_process or self.server_process.poll() is not None:
                    break
                line = self.server_process.stdout.readline()
                if not line:
                    break
                print(line.strip())
                # Check for indicators that the server is ready
                if self.server_ready_indicator in line:
                    server_ready.set()

                # Capture user data directory path for cleanup (for WebReplay online tasks)
                if (
                    hasattr(self, "task_id")
                    and hasattr(self, "user_data_dir")
                    and self.task_id
                    and self.task_id.startswith("online")
                    and "Created temporary user data directory for online task:" in line
                ):
                    # Extract the directory path from the log line
                    try:
                        self.user_data_dir = line.split(
                            "Created temporary user data directory for online task: "
                        )[1].strip()
                        print(
                            f"Captured user data directory for cleanup: {self.user_data_dir}"
                        )
                    except IndexError:
                        print(
                            "Warning: Could not extract user data directory path from log line"
                        )

        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()

        # Wait for the server to be ready with a timeout as fallback
        max_wait_time = 60  # seconds
        server_ready.wait(timeout=max_wait_time)
        if not server_ready.is_set():
            print(
                f"\033[31m Error: Static server didn't report ready status within {max_wait_time} seconds. Continuing anyway... \033[0m"
            )


class WebReplayServerSessionHandler(WebServerSessionHandler):
    def __init__(
        self,
        task_id: str,
        wacz_file: str = None,
        start_url: str = None,
        debugging_port: int = 9222,
        browser_args: dict = None,
        viewport_width: int = None,
        viewport_height: int = None,
    ) -> None:
        """
        Initialize a WebReplayServerSessionHandler.

        Args:
            task_id: The task ID to load from config.
            debugging_port: Port for Chrome debugging protocol (default: 9222).
            browser_args: Dictionary of browser arguments to pass to Chrome.
                          Keys are argument names, values are argument values.
                          For boolean flags, use True as the value.
                          Example: {"load-extension": "/path/to/ext", "disable-web-security": True}
            viewport_width: Width of the browser window in pixels (optional).
            viewport_height: Height of the browser window in pixels (optional).
        """
        super().__init__(task_id, debugging_port)

        self.wacz_file = wacz_file
        self.start_url = start_url
        self.browser_args = browser_args
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.webreplay_dir = Path(__file__).parent.parent / "webreplay-standalone"
        self.server_process = None
        self.server_ready_indicator = "Browser instance ready for CDP connection"
        self.user_data_dir = None  # Will store the user data directory path for cleanup

    def setup_webreplay_server(self, run_headless: bool = True) -> None:
        """
        Setup the webreplay server with the given replay configuration path and port.

        The server will be configured with:
        - Task-specific WARC file and start URL from config
        - Debugging port for CDP access
        - Optional browser arguments
        - Optional viewport dimensions (if width and height were specified)
        - Optional headless mode (enabled by default)

        Note that the user does not have to perform any cleanup, as the cleanup method is called automatically when the object is destroyed on a SIGINT or a SIGTERM signal.

        Args:
            run_headless: Whether to run the browser in headless mode (default: True)
        """
        command = self.construct_command(run_headless)
        self._start_server(command)

    def construct_command(self, run_headless: bool):
        """Construct the command to start the webreplay server."""
        print(f"Webreplay directory: {self.webreplay_dir}")
        command = f"cd {self.webreplay_dir}/ && pwd && node dist/index.js serve {os.path.join('..', self.task_config['env']['data_path'])} \"{self.task_config['env']['start_url']}\" --debugging-port {self.debugging_port}"

        if run_headless:
            command += " --headless"

        # Add task ID for online task detection
        if self.task_id:
            command += f" --task-id {self.task_id}"

        # Add timestamp if present in config
        if "timestamp" in self.task_config["env"]:
            # Convert from seconds+nanos to milliseconds since epoch
            timestamp = self.task_config["env"]["timestamp"]
            milliseconds = (timestamp["seconds"] * 1000) + (
                timestamp["nanos"] // 1_000_000
            )
            command += f" --timestamp {milliseconds}"

        # Add viewport dimensions if provided
        if self.viewport_width and self.viewport_height:
            command += f" --width {self.viewport_width} --height {self.viewport_height}"

        # Add browser arguments if provided
        if self.browser_args:
            # Convert browser args to a properly escaped JSON string
            browser_args_json = json.dumps(self.browser_args)
            # Double escape quotes for shell command
            browser_args_json = browser_args_json.replace('"', '\\"')
            command += f' --browser-arg "{browser_args_json}"'

        return command

    def cleanup(self):
        """Cleanup when the server is destroyed."""
        try:
            # First cleanup the server process (inherited behavior)
            if self.server_process:
                pgid = os.getpgid(self.server_process.pid)
                print(f"Cleaning up process group {pgid}")

                # First try graceful termination
                os.killpg(pgid, signal.SIGTERM)

                # Wait for a short time for graceful shutdown
                for _ in range(5):
                    if self.server_process.poll() is not None:
                        break
                    time.sleep(0.2)

                # If still running, force kill
                if self.server_process.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)

                self.server_process = None

            # Additionally, clean up any remaining processes on the port
            self._kill_process_on_port(self.debugging_port)

            # Clean up user data directory for online tasks
            if (
                self.task_id
                and self.task_id.startswith("online")
                and self.user_data_dir
            ):
                try:
                    if os.path.exists(self.user_data_dir):
                        print(
                            f"Cleaning up temporary user data directory: {self.user_data_dir}"
                        )
                        shutil.rmtree(self.user_data_dir)
                        print(
                            f"Successfully removed user data directory: {self.user_data_dir}"
                        )
                    self.user_data_dir = None
                except Exception as e:
                    print(
                        f"Warning: Failed to clean up user data directory {self.user_data_dir}: {e}"
                    )

        except (ProcessLookupError, OSError) as e:
            print(f"Error during cleanup: {e}")


class StaticWebAppServerSessionHandler(WebServerSessionHandler):
    def __init__(
        self,
        task_id: str,
        debugging_port: int = 9222,
        node_command: str = "npm start",
        serve_args: str = "",
    ):
        """
        Initialize a StaticWebAppServerSessionHandler.

        Args:
            app_dir: Path to the static web app directory to serve.
            port: Port to serve the app on (default: 3000).
            node_command: Command to start the static server (default: 'npx serve').
        """
        super().__init__(task_id, debugging_port)
        self.app_dir = (
            Path(__file__).parent.parent / self.task_config["env"]["data_path"]
        )
        self.node_command = node_command
        self.server_process = None
        self.server_ready_indicator = "Local:"

    def setup_static_server(self, run_headless: bool = True):
        """
        Setup the static web app server with the given directory and port.
        """
        command = self.construct_command(run_headless)
        self._start_server(command)

    def construct_command(self, run_headless: bool):
        # Example: cd ..npm start -l 3000
        command = f"cd {self.app_dir} && PORT={self.debugging_port} {self.node_command}"
        if run_headless:
            command += " --headless"
        return command
