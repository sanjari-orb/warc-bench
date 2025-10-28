import os
import subprocess
import sys
import shutil
from setuptools.command.build_py import build_py


class BuildPyCommand(build_py):
    """Custom build command that runs npm build in webreplay-standalone and ensures files are copied to the package."""

    def run(self):
        # Run the standard build_py first to create the directory structure
        build_py.run(self)

        # Run npm build in webreplay-standalone directory
        project_root = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(project_root, "src")
        package_dir = os.path.join(src_dir, "orby", "subtask_benchmark")
        webreplay_dir = os.path.join(package_dir, "webreplay-standalone")

        if os.path.exists(webreplay_dir):
            print("Building webreplay-standalone...")
            try:
                # Check if npm is installed
                subprocess.check_call(["npm", "--version"], stdout=subprocess.PIPE)

                # Change to webreplay directory
                old_dir = os.getcwd()
                os.chdir(webreplay_dir)

                # Install npm dependencies if needed
                subprocess.check_call(["npm", "install"], stdout=subprocess.PIPE)

                # Run npm build
                subprocess.check_call(["npm", "run", "build"], stdout=subprocess.PIPE)

                # Change back to original directory
                os.chdir(old_dir)
                print("Successfully built webreplay-standalone")

                # Make sure the build directory includes the right directory structure
                build_lib_dir = self.build_lib
                target_webreplay_dir = os.path.join(
                    build_lib_dir, "orby", "subtask_benchmark", "webreplay-standalone"
                )

                # Ensure the directory exists
                os.makedirs(target_webreplay_dir, exist_ok=True)

                # Copy the contents, including the dist/ directory
                for item in os.listdir(webreplay_dir):
                    source_path = os.path.join(webreplay_dir, item)
                    target_path = os.path.join(target_webreplay_dir, item)

                    if os.path.isdir(source_path):
                        if os.path.exists(target_path):
                            shutil.rmtree(target_path)
                        shutil.copytree(source_path, target_path)
                    else:
                        shutil.copy2(source_path, target_path)

                print(f"Copied webreplay-standalone to {target_webreplay_dir}")

            except subprocess.CalledProcessError:
                print("Error: Failed to build webreplay-standalone", file=sys.stderr)
                raise
            except FileNotFoundError:
                print(
                    "Error: npm not found. Please install Node.js and npm.",
                    file=sys.stderr,
                )
                raise
        else:
            print(
                f"Warning: webreplay-standalone directory not found at {webreplay_dir}",
                file=sys.stderr,
            )
