"""
Protocol buffer definitions for visualization and trajectory data.

This package contains the compiled protobuf definitions for:
- action_data: Action-related data structures
- llm_data: LLM-related data structures
- trajectory_data: Trajectory recording and visualization
"""

# Re-export commonly used protobufs for convenience
from orby.protos.fm.action_data_pb2 import *
from orby.protos.fm.llm_data_pb2 import *
from orby.protos.fm.trajectory_data_pb2 import *
