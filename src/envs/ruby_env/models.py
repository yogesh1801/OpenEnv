# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Ruby Environment.

The Ruby environment executes Ruby code and provides feedback through
compilation and unit test results.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.env_server.types import Action, Observation, State


@dataclass(kw_only=True)
class RubyAction(Action):
    """
    Action for the Ruby environment - code to execute.
    
    Attributes:
        core_code: Core Ruby code to execute
        test_code: Test code to execute (using Minitest)
    """
    core_code: str
    test_code: str

@dataclass(kw_only=True)
class RubyObservation(Observation):
    """
    Observation from the Ruby environment - execution results.
    
    Attributes:
        stdout: Standard output from Ruby execution
        stderr: Standard error from Ruby execution
        exit_code: Exit code (0 = success, non-zero = error)
        execution_time: Time taken to execute in seconds
        tests_passed: Number of tests passed (if tests were run)
        tests_failed: Number of tests failed (if tests were run)
        code_compiles: Whether the core code compiled/executed successfully
    """
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    code_compiles: bool = True


@dataclass
class RubyState(State):
    """
    State for Ruby environment.
    
    Attributes:
        episode_id: Unique episode identifier
        step_count: Number of steps taken in episode
        last_exit_code: Exit code from last execution
        total_tests_passed: Cumulative tests passed in episode
        total_tests_failed: Cumulative tests failed in episode
    """
    last_exit_code: int = 0
    last_code_compiles: bool = True
    total_tests_passed: int = 0
    total_tests_failed: int = 0

