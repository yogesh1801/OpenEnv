"""
R Code Action Environment.

This environment mirrors the JuliaCodeActEnv but runs R code instead.
It executes R code using RExecutor, captures output,
tracks the last exit code, and returns an RObservation.
"""

import re
import uuid

from core.env_server import Environment
from core.tools import RExecutor
from ..models import RAction, RObservation, RState
from .r_transforms import create_safe_r_transform


class RCodeActEnv(Environment):
    """
    R Code Action Environment for executing code and tracking state.

    This environment executes R code submitted as CodeAction during step,
    maintains the last exit code in its state, and returns results wrapped
    in CodeObservation.

    Example:
        >>> env = RCodeActEnv()
        >>> obs = env.reset()
        >>> action = CodeAction(code='print("Hello, R!")')
        >>> obs = env.step(action)
        >>> print(obs.stdout)  # "[1] \"Hello, R!\"\n"
        >>> print(obs.exit_code)  # 0
        >>> print(env.state.last_exit_code)  # 0
    """

    def __init__(self):
        """Initialize the R Code Act Environment."""
        self._executor = RExecutor()
        self._state = RState()
        self.transform = create_safe_r_transform()

    def reset(self) -> RObservation:
        """
        Reset environment for a fresh R execution session.
        Returns an empty RObservation with exit_code=0.
        """
        self._state = RState(episode_id=str(uuid.uuid4()), step_count=0)
        self._state.last_exit_code = 0
        self._state.last_code_compiles = True
        self._executor = RExecutor()

        observation = RObservation(
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
        

    def step(self, action: RAction) -> RObservation:
        """
        Execute R code and return the result as RObservation.
        
        Two-stage execution:
        1. Run core_code only → check if it compiles/executes
        2. Run core_code + test_code → get test results
        """
        if not isinstance(action, RAction):
            raise ValueError(f"Expected RAction, got {type(action)}")

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
        observation = RObservation(
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
        Parse R test output to count passed/failed tests.
        
        R's testthat package outputs results like:
        "Test passed 🎊"
        "Test failed 😱"
        
        Or with test_that:
        "✔ | F W S  OK | Context"
        "✔ |     0 | my_test"
        
        Args:
            stdout: Standard output from R execution
            stderr: Standard error from R execution
            
        Returns:
            Tuple of (tests_passed, tests_failed)
        """
        # Combine stdout and stderr for analysis
        passed = 0
        failed = 0
        output = stdout + "\n" + stderr
        
        # Method 1: Look for testthat summary line
        # Pattern: "[ FAIL N | WARN W | SKIP S | PASS P ]"
        summary_pattern = r"\[\s*FAIL\s+(\d+)\s*\|\s*WARN\s+\d+\s*\|\s*SKIP\s+\d+\s*\|\s*PASS\s+(\d+)\s*\]"
        match = re.search(summary_pattern, output)
        
        if match:
            failed = int(match.group(1))
            passed = int(match.group(2))
            return passed, failed
        
        # Method 2: Look for individual test results
        # Count "Test passed" messages
        passed_matches = re.findall(r"Test passed", output, re.IGNORECASE)
        passed = len(passed_matches)
        
        # Count "Test failed" or "Failure" messages
        failed_matches = re.findall(r"(Test failed|Failure\s*\(|Error\s*\()", output, re.IGNORECASE)
        failed = len(failed_matches)
        
        # Method 3: Look for testthat table format
        # "✔ | F W S  OK | Context"
        # "✔ |     0 | my_test"
        # or
        # "✖ |     1 | my_test"
        table_lines = output.split('\n')
        for line in table_lines:
            # Look for lines with checkmark or X followed by numbers
            check_match = re.search(r'[✔✓]\s*\|\s*(\d+)\s+\d+\s+\d+\s+(\d+)', line)
            if check_match:
                failed += int(check_match.group(1))
                passed += int(check_match.group(2))
                continue
            
            cross_match = re.search(r'[✖✗❌]\s*\|\s*(\d+)\s+\d+\s+\d+\s+(\d+)', line)
            if cross_match:
                failed += int(cross_match.group(1))
                passed += int(cross_match.group(2))
                continue
        
        # Method 4: expect_equal, expect_true etc. success/failure
        # Count individual expect_* calls that passed (no error message follows)
        expect_calls = re.findall(r'expect_\w+', output)
        if expect_calls and passed == 0 and failed == 0:
            # If we found expect calls but no other indicators, count errors
            error_count = len(re.findall(r'Error\s*:', output))
            if error_count > 0:
                failed = error_count
                passed = max(0, len(expect_calls) - error_count)
            else:
                # No errors means all passed
                passed = len(expect_calls)
        
        return passed, failed

    def _calculate_reward(self, code_compiles: bool, tests_passed: int, tests_failed: int) -> int:
        """
        Optimized integer reward for R GRPO.
        Strong signal shaping: rewards correctness, penalizes instability,
        and gives higher incentive for near-perfect results.
        """

        # Code doesn't compile — immediate strong penalty
        if not code_compiles:
            return -3

        reward = 1

        if tests_failed == 0 and tests_passed > 0:
            reward += 6 
            return reward

        reward += 3 * tests_passed - 1 * tests_failed

        return reward


    @property
    def state(self) -> RState:
        """Return current environment state."""
        return self._state

