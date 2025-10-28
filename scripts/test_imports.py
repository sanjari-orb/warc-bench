#!/usr/bin/env python3
"""Test script to verify imports from orby package."""

# Try to import the package
import orby
import orby.subtask_benchmark

print(
    f"Successfully imported orby version {orby.__version__}"
)

# Try to import submodules
try:
    import orby.subtask_benchmark.config

    print("✅ Successfully imported orby.subtask_benchmark.config")
except ImportError as e:
    print(f"❌ Failed to import orby.subtask_benchmark.config: {e}")

try:
    import orby.subtask_benchmark.evaluator

    print("✅ Successfully imported orby.subtask_benchmark.evaluator")
except ImportError as e:
    print(f"❌ Failed to import orby.subtask_benchmark.evaluator: {e}")

try:
    import orby.subtask_benchmark.utils

    print("✅ Successfully imported orby.subtask_benchmark.utils")
except ImportError as e:
    print(f"❌ Failed to import orby.subtask_benchmark.utils: {e}")

# Print out all attributes to verify dynamic imports worked
print("\nAvailable attributes in orby.subtask_benchmark:")
for attr in dir(orby.subtask_benchmark):
    if not attr.startswith("_"):
        print(f"  - {attr}")
