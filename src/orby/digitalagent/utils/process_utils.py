import os
import multiprocessing
import signal
import psutil
import datetime
import time


def get_process_tree(pid):
    """
    Recursively gets all child processes of a given PID.
    """
    try:
        parent_process = psutil.Process(pid)
        children = parent_process.children(recursive=True)
        return [parent_process] + children
    except psutil.NoSuchProcess:
        return []


def print_process_info(process):
    """Prints various information about a process given its PID."""
    try:
        print(f"--- Process Information for PID: {process.pid} ---")
        print(f"Name: {process.name()}")
        print(f"Executable: {process.exe()}")
        print(f"Status: {process.status()}")
        print(f"Username: {process.username()}")
        
        # Convert create_time (timestamp) to a readable format
        create_time_dt = datetime.datetime.fromtimestamp(process.create_time())
        print(f"Create Time: {create_time_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"CPU Percent: {process.cpu_percent(interval=0.1)}%") # Requires a small interval for non-zero result
        print(f"Memory Info (RSS): {process.memory_info().rss / (1024 * 1024):.2f} MB") # Resident Set Size
        print(f"Number of Threads: {process.num_threads()}")
        print(f"Command Line: {' '.join(process.cmdline())}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

 
def run_with_timeout(function, timeout_seconds, *args, **kwargs):
    # Create the multiprocessing process, passing the function and arguments
    process = multiprocessing.Process(target=function, args=args, kwargs=kwargs)
    start = time.time()
    process.start()
    process.join(timeout=timeout_seconds)

    if process.is_alive():
        is_timeout = time.time() - start > timeout_seconds

        # Kill all subprocesses including itself, usually it's node / chrome running subtask server.
        processes = get_process_tree(process.pid)
        for p in processes:
            try:
                print_process_info(p)
                os.kill(p.pid, signal.SIGKILL)
            except Exception as e:
                print(f'Exception when killing process {p.pid}: {e}')

        try:
            process.join()  # Ensure cleanup after killing
        except Exception as e:
            print(f'Exception when joining process {process.pid}: {e}')

        if is_timeout:
            # In rare cases, process.is_alive() returns True even the process
            # finishes successfully well before timeout (e.g., using only 20s).
            # So we need to check whether it's really a timeout to return the
            # TimeoutError, to avoid throwing away successful tasks.
            raise TimeoutError(
                f"Function execution exceeded timeout of {timeout_seconds} seconds."
            )
