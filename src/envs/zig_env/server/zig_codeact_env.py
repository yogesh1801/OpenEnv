"""
Zig Code Action Environment.

This environment mirrors the JuliaCodeActEnv but runs Zig code instead.
It executes Zig code using ZigExecutor, captures output,
tracks the last exit code, and returns a ZigObservation.
"""

import re
import uuid

from core.env_server import Environment
from core.tools import ZigExecutor
from ..models import ZigAction, ZigObservation, ZigState
from .zig_transforms import create_safe_zig_transform


class ZigCodeActEnv(Environment):
    """
    Zig Code Action Environment for executing code and tracking state.

    This environment executes Zig code submitted as ZigAction during step,
    maintains the last exit code in its state, and returns results wrapped
    in ZigObservation.

    Example:
        >>> env = ZigCodeActEnv()
        >>> obs = env.reset()
        >>> action = ZigAction(
        ...     core_code='const std = @import("std");\\npub fn main() void { std.debug.print("Hello, Zig!\\n", .{}); }',
        ...     test_code=''
        ... )
        >>> obs = env.step(action)
        >>> print(obs.stdout)  # "Hello, Zig!\n"
        >>> print(obs.exit_code)  # 0
        >>> print(env.state.last_exit_code)  # 0
    """

    def __init__(self):
        """Initialize the Zig Code Act Environment."""
        self._executor = ZigExecutor()
        self._state = ZigState()
        self.transform = create_safe_zig_transform()

    def reset(self) -> ZigObservation:
        """
        Reset environment for a fresh Zig execution session.
        Returns an empty ZigObservation with exit_code=0.
        """
        self._state = ZigState(episode_id=str(uuid.uuid4()), step_count=0)
        self._state.last_exit_code = 0
        self._state.last_code_compiles = True
        self._executor = ZigExecutor()

        observation = ZigObservation(
            stdout="",
            stderr="",
            exit_code=0,
            reward=0.0,
            metadata={
                "core_code": "",
                "test_code": ""
            },
            tests_passed=0,
            tests_failed=0,
            code_compiles=True
        )

        observation = self._apply_transform(observation)
        return observation
        

    def step(self, action: ZigAction) -> ZigObservation:
        """
        Execute Zig code and return the result as ZigObservation.
        
        Two-stage execution:
        1. Run core_code only → check if it compiles/executes
        2. Run core_code + test_code → get test results
        """
        if not isinstance(action, ZigAction):
            raise ValueError(f"Expected ZigAction, got {type(action)}")

        # Stage 1: Execute core_code only to check compilation
        core_result = self._executor.run(action.core_code)
        code_compiles = core_result.exit_code == 0
        
        # Stage 2: Execute core_code + test_code to get test results
        combined_code = action.core_code + "\n\n" + action.test_code
        full_result = self._executor.run(combined_code)
        
        # Parse test results from combined execution
        tests_passed, tests_failed = self._parse_test_results(full_result.stdout, full_result.stderr)

        # Calculate reward based on compilation and test results
        reward = self._calculate_reward(code_compiles, tests_passed, tests_failed)

        # Update environment state
        self._state.step_count += 1
        self._state.last_exit_code = full_result.exit_code
        self._state.last_code_compiles = code_compiles
        self._state.total_tests_passed = tests_passed
        self._state.total_tests_failed = tests_failed

        # Build observation (use full_result output, but code_compiles flag from core)
        observation = ZigObservation(
            stdout=full_result.stdout,
            stderr=full_result.stderr,
            exit_code=full_result.exit_code,
            reward=reward,
            metadata={
                "core_code": action.core_code,
                "test_code": action.test_code
            },
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            code_compiles=code_compiles
        )

        # Apply safety and quality transforms
        observation = self._apply_transform(observation)

        return observation

    def _parse_test_results(self, stdout: str, stderr: str) -> tuple[int, int]:
        """
        Parse Zig test output to count passed/failed tests.
        
        Zig's test runner outputs results like:
        "All 3 tests passed."
        or
        "1 passed; 1 failed."
        
        Args:
            stdout: Standard output from Zig execution
            stderr: Standard error from Zig execution
            
        Returns:
            Tuple of (tests_passed, tests_failed)
        """
        # Combine stdout and stderr for analysis
        passed = 0
        failed = 0
        output = stdout + "\n" + stderr
        
        # Method 1: Look for "All X tests passed"
        all_pass_pattern = r"All (\d+) tests? passed"
        match = re.search(all_pass_pattern, output)
        if match:
            passed = int(match.group(1))
            failed = 0
            return passed, failed
        
        # Method 2: Look for "X passed; Y failed"
        summary_pattern = r"(\d+) passed[;,]\s*(\d+) failed"
        match = re.search(summary_pattern, output)
        if match:
            passed = int(match.group(1))
            failed = int(match.group(2))
            return passed, failed
        
        # Method 3: Look for individual test results
        # Zig outputs lines like:
        # "Test [1/3] test_name... PASS"
        # "Test [2/3] test_name... FAIL"
        pass_count = len(re.findall(r"Test \[\d+/\d+\].*?PASS", output))
        fail_count = len(re.findall(r"Test \[\d+/\d+\].*?FAIL", output))
        
        if pass_count > 0 or fail_count > 0:
            return pass_count, fail_count
        
        return passed, failed

    def _calculate_reward(self, code_compiles: bool, tests_passed: int, tests_failed: int) -> int:
        """
        Optimized integer reward for Zig GRPO.
        Strong signal shaping: rewards correctness, penalizes instability,
        and gives higher incentive for near-perfect results.
        """

        # Code doesn't compile — immediate strong penalty
        if not code_compiles:
            return -3

        reward = 1

        reward += 3 * tests_passed - 1 * tests_failed

        if tests_failed == 0 and tests_passed > 0:
            reward += 2

        return reward


    @property
    def state(self) -> ZigState:
        """Return current environment state."""
        return self._state

