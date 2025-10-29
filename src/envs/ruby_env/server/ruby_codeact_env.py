"""
Ruby Code Action Environment.

This environment mirrors the JuliaCodeActEnv but runs Ruby code instead.
It executes Ruby code using RubyExecutor, captures output,
tracks the last exit code, and returns a RubyObservation.
"""

import re
import uuid

from core.env_server import Environment
from core.tools import RubyExecutor
from ..models import RubyAction, RubyObservation, RubyState
from .ruby_transforms import create_safe_ruby_transform


class RubyCodeActEnv(Environment):
    """
    Ruby Code Action Environment for executing code and tracking state.

    This environment executes Ruby code submitted as RubyAction during step,
    maintains the last exit code in its state, and returns results wrapped
    in RubyObservation.

    Example:
        >>> env = RubyCodeActEnv()
        >>> obs = env.reset()
        >>> action = RubyAction(core_code='puts "Hello, Ruby!"', test_code='')
        >>> obs = env.step(action)
        >>> print(obs.stdout)  # "Hello, Ruby!\n"
        >>> print(obs.exit_code)  # 0
        >>> print(env.state.last_exit_code)  # 0
    """

    def __init__(self):
        """Initialize the Ruby Code Act Environment."""
        self._executor = RubyExecutor()
        self._state = RubyState()
        self.transform = create_safe_ruby_transform()

    def reset(self) -> RubyObservation:
        """
        Reset environment for a fresh Ruby execution session.
        Returns an empty RubyObservation with exit_code=0.
        """
        self._state = RubyState(episode_id=str(uuid.uuid4()), step_count=0)
        self._state.last_exit_code = 0
        self._state.last_code_compiles = True
        self._executor = RubyExecutor()

        observation = RubyObservation(
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
        

    def step(self, action: RubyAction) -> RubyObservation:
        """
        Execute Ruby code and return the result as RubyObservation.
        
        Two-stage execution:
        1. Run core_code only → check if it compiles/executes
        2. Run core_code + test_code → get test results
        """
        if not isinstance(action, RubyAction):
            raise ValueError(f"Expected RubyAction, got {type(action)}")

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
        observation = RubyObservation(
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
        Parse Ruby Minitest output to count passed/failed tests.
        
        Minitest outputs results like:
        "1 runs, 1 assertions, 0 failures, 0 errors, 0 skips"
        or
        "Finished in 0.001234s, 813.01 runs/s, 813.01 assertions/s."
        "3 runs, 3 assertions, 1 failures, 0 errors, 0 skips"
        
        Args:
            stdout: Standard output from Ruby execution
            stderr: Standard error from Ruby execution
            
        Returns:
            Tuple of (tests_passed, tests_failed)
        """
        # Combine stdout and stderr for analysis
        passed = 0
        failed = 0
        output = stdout + "\n" + stderr
        
        # Method 1: Look for Minitest summary line
        # Pattern: "X runs, Y assertions, Z failures, W errors, V skips"
        summary_pattern = r"(\d+) runs?, \d+ assertions?, (\d+) failures?, (\d+) errors?, \d+ skips?"
        match = re.search(summary_pattern, output)
        
        if match:
            runs = int(match.group(1))
            failures = int(match.group(2))
            errors = int(match.group(3))
            
            # Total failures = failures + errors
            failed = failures + errors
            # Passed = runs - failed
            passed = runs - failed
            return passed, failed
        
        # Method 2: Count individual test results markers
        # Minitest uses "." for pass, "F" for failure, "E" for error
        # But these are printed inline, so count them
        pass_count = output.count(' . ')  # Passed tests often show as " . "
        fail_count = output.count(' F ') + output.count(' E ')
        
        if pass_count > 0 or fail_count > 0:
            return pass_count, fail_count
        
        return passed, failed

    def _calculate_reward(self, code_compiles: bool, tests_passed: int, tests_failed: int) -> int:
        """
        Optimized integer reward for Ruby GRPO.
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
    def state(self) -> RubyState:
        """Return current environment state."""
        return self._state

