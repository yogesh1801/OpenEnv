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
        self._executor = JuliaExecutor()

        observation = JuliaObservation(
            stdout="",
            stderr="",
            exit_code=0,
            reward=0.0,
            metadata={"last_code": ""},
            tests_passed=0,
            tests_failed=0
        )

        observation = self._apply_transform(observation)
        return observation
        

    def step(self, action: JuliaAction) -> JuliaObservation:
        """
        Execute Julia code and return the result as JuliaObservation.
        """
        if not isinstance(action, JuliaAction):
            raise ValueError(f"Expected JuliaAction, got {type(action)}")

        # Execute the code using JuliaExecutor
        result = self._executor.run(action.code)

        # Parse test results
        tests_passed, tests_failed = self._parse_test_results(result.stdout, result.stderr)

        # Calculate reward
        reward = self._calculate_reward(result.exit_code, tests_passed, tests_failed)

        # Update environment state
        self._state.step_count += 1
        self._state.last_exit_code = result.exit_code
        self._state.total_tests_passed = tests_passed
        self._state.total_tests_failed = tests_failed

        # Build observation
        observation = JuliaObservation(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            reward=reward,
            metadata={"last_code": action.code},
            tests_passed=tests_passed,
            tests_failed=tests_failed
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
                        # total = int(numbers[0][2])
                        return passed, failed
                else:
                    # Pattern: Pass  Total (2 numbers) - no failures!
                    numbers = re.findall(r'\|\s*(\d+)\s+(\d+)', next_line)
                    if numbers:
                        passed = int(numbers[0][0])
                        failed = 0  # No fail column means 0 failures
                        # total = int(numbers[0][1])
                        return passed, failed
        
        return passed, failed

    def _calculate_reward(self, exit_code: int, tests_passed: int, tests_failed: int) -> float:
        """
        Calculate reward based on execution results.
        
        Reward structure:
        - Failed execution (exit != 0): -0.5
        - Clean execution (exit 0): +0.2
        - Each test passed: +0.3
        - Each test failed: -0.2
        - All tests passed (>0): +0.5 bonus
        
        Args:
            exit_code: Process exit code
            tests_passed: Number of tests passed
            tests_failed: Number of tests failed
            
        Returns:
            Reward value (float)
        """
        reward = 0.0
        
        if exit_code != 0:
            return -0.5
        
        reward += 0.2

        total_tests = tests_passed + tests_failed
        
        reward += 0.3 * (tests_passed / total_tests) - 0.2 * (tests_failed / total_tests)

        if tests_passed == total_tests:
            reward += 0.5
        
        return reward

    @property
    def state(self) -> JuliaState:
        """Return current environment state."""
        return self._state
