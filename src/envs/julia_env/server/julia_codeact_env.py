"""
Julia Code Action Environment.

This environment mirrors the PythonCodeActEnv but runs Julia code instead.
It executes Julia code using JuliaExecutor, captures output,
tracks the last exit code, and returns a JuliaObservation.
"""

import re
import uuid

from core.env_server import Environment
from core.tools import JuliaExecutor
from ..models import JuliaAction, JuliaObservation, JuliaState
from .julia_transforms import create_safe_julia_transform


class JuliaCodeActEnv(Environment):
    """
    Julia Code Action Environment for executing code and tracking state.

    This environment executes Julia code submitted as CodeAction during step,
    maintains the last exit code in its state, and returns results wrapped
    in CodeObservation.

    Example:
        >>> env = JuliaCodeActEnv()
        >>> obs = env.reset()
        >>> action = CodeAction(code='println("Hello, Julia!")')
        >>> obs = env.step(action)
        >>> print(obs.stdout)  # "Hello, Julia!\n"
        >>> print(obs.exit_code)  # 0
        >>> print(env.state.last_exit_code)  # 0
    """

    def __init__(self):
        """Initialize the Julia Code Act Environment."""
        self._executor = JuliaExecutor()
        self._state = JuliaState()
        self.transform = create_safe_julia_transform()

    def reset(self) -> JuliaObservation:
        """
        Reset environment for a fresh Julia execution session.
        Returns an empty JuliaObservation with exit_code=0.
        """
        self._state = JuliaState(episode_id=str(uuid.uuid4()), step_count=0)
        self._state.last_exit_code = 0
        self._state.last_code_compiles = True
        self._executor = JuliaExecutor()

        observation = JuliaObservation(
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
        

    def step(self, action: JuliaAction) -> JuliaObservation:
        """
        Execute Julia code and return the result as JuliaObservation.
        
        Two-stage execution:
        1. Run core_code only → check if it compiles/executes
        2. Run core_code + test_code → get test results
        """
        if not isinstance(action, JuliaAction):
            raise ValueError(f"Expected JuliaAction, got {type(action)}")

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
        observation = JuliaObservation(
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
        Parse Julia test output to count passed/failed tests.
        
        Julia's Test module outputs results like:
        "Test Summary:      | Pass  Fail  Total  Time"
        "Add function Tests |    1     1      2  1.5s"
        
        Also checks error messages:
        "Some tests did not pass: 1 passed, 1 failed, 0 errored, 0 broken."
        
        Args:
            stdout: Standard output from Julia execution
            stderr: Standard error from Julia execution
            
        Returns:
            Tuple of (tests_passed, tests_failed)
        """
        # Combine stdout and stderr for analysis
        passed = 0
        failed = 0
        output = stdout + "\n" + stderr
        
        # Method 1: Look for "Some tests did not pass" error message
        # Pattern: "Some tests did not pass: X passed, Y failed, Z errored, W broken."
        error_pattern = r"Some tests did not pass:\s*(\d+)\s+passed,\s*(\d+)\s+failed"
        match = re.search(error_pattern, output)
        
        if match:
            passed = int(match.group(1))
            failed = int(match.group(2))
            return passed, failed
        
        # Method 2: Look for Test Summary table
        # Two possible formats:
        # With failures: "Test Summary:      | Pass  Fail  Total  Time"
        #                "Add function Tests |    3     1      4  0.5s"
        # No failures:   "Test Summary:      | Pass  Total  Time"
        #                "Add function Tests |    1      1  0.0s"
        summary_lines = output.split('\n')
        for i, line in enumerate(summary_lines):
            if 'Test Summary:' in line and i + 1 < len(summary_lines):
                header_line = line
                next_line = summary_lines[i + 1]
                
                # Check if "Fail" column exists in header
                has_fail_column = 'Fail' in header_line
                
                if has_fail_column:
                    # Pattern: Pass  Fail  Total (3 numbers)
                    numbers = re.findall(r'\|\s*(\d+)\s+(\d+)\s+(\d+)', next_line)
                    if numbers:
                        passed = int(numbers[0][0])
                        failed = int(numbers[0][1])
                        return passed, failed
                else:
                    # Pattern: Pass  Total (2 numbers) - no failures!
                    numbers = re.findall(r'\|\s*(\d+)\s+(\d+)', next_line)
                    if numbers:
                        passed = int(numbers[0][0])
                        failed = 0
                        return passed, failed
        
        return passed, failed

    def _calculate_reward(self, code_compiles: bool, tests_passed: int, tests_failed: int) -> int:
        """
        Optimized integer reward for Julia GRPO.
        Strong signal shaping: rewards correctness, penalizes instability,
        and gives higher incentive for near-perfect results.
        """

        # Code doesn't compile — immediate strong penalty
        if not code_compiles:
            return -3

        reward = 2  # base reward for successful compilation

        total_tests = tests_passed + tests_failed

        # If no tests are found — discourage empty completions
        if total_tests == 0:
            return -2

        # Perfect solution
        if tests_failed == 0 and tests_passed > 0:
            reward += 6  # strong boost for perfect solutions
            return min(reward, 10)

        # Partial success — scale based on success ratio
        success_ratio = tests_passed * 100 // total_tests  # integer %
        if success_ratio >= 90:
            reward += 5
        elif success_ratio >= 75:
            reward += 3
        elif success_ratio >= 50:
            reward += 1
        else:
            reward -= 2  # mostly failed

        # Consistency bonus for some passed tests even if not perfect
        if tests_passed > 0 and tests_failed <= tests_passed // 2:
            reward += 1

        # Heavy penalty if tests mostly fail
        if tests_failed > tests_passed:
            reward -= 3

        # Reward caps for stability
        reward = max(-5, min(reward, 10))

        return reward


    @property
    def state(self) -> JuliaState:
        """Return current environment state."""
        return self._state
