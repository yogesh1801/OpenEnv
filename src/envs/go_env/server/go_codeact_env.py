"""
Go Code Action Environment.

This environment mirrors the JuliaCodeActEnv but runs Go code instead.
It executes Go code using GoExecutor, captures output,
tracks the last exit code, and returns a GoObservation.
"""

import re
import uuid

from core.env_server import Environment
from core.tools import GoExecutor
from ..models import GoAction, GoObservation, GoState
from .go_transforms import create_safe_go_transform


class GoCodeActEnv(Environment):
    """
    Go Code Action Environment for executing code and tracking state.

    This environment executes Go code submitted as GoAction during step,
    maintains the last exit code in its state, and returns results wrapped
    in GoObservation.

    Example:
        >>> env = GoCodeActEnv()
        >>> obs = env.reset()
        >>> action = GoAction(
        ...     core_code='package main\\n\\nimport "fmt"\\n\\nfunc main() {\\n    fmt.Println("Hello, Go!")\\n}',
        ...     test_code=''
        ... )
        >>> obs = env.step(action)
        >>> print(obs.stdout)  # "Hello, Go!\n"
        >>> print(obs.exit_code)  # 0
        >>> print(env.state.last_exit_code)  # 0
    """

    def __init__(self):
        """Initialize the Go Code Act Environment."""
        self._executor = GoExecutor()
        self._state = GoState()
        self.transform = create_safe_go_transform()

    def reset(self) -> GoObservation:
        """
        Reset environment for a fresh Go execution session.
        Returns an empty GoObservation with exit_code=0.
        """
        self._state = GoState(episode_id=str(uuid.uuid4()), step_count=0)
        self._state.last_exit_code = 0
        self._state.last_code_compiles = True
        self._executor = GoExecutor()

        observation = GoObservation(
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
        

    def step(self, action: GoAction) -> GoObservation:
        """
        Execute Go code and return the result as GoObservation.
        
        Two-stage execution:
        1. Run core_code only → check if it compiles/executes
        2. Run core_code + test_code → get test results
        """
        if not isinstance(action, GoAction):
            raise ValueError(f"Expected GoAction, got {type(action)}")

        # Stage 1: Execute core_code only to check compilation
        core_result = self._executor.run(action.core_code)
        code_compiles = core_result.exit_code == 0
        
        # Stage 2: If test_code is provided, execute tests
        if action.test_code.strip():
            # For Go, we need to run tests separately
            test_result = self._executor.run_with_tests(action.core_code, action.test_code)
            full_result = test_result
        else:
            # No tests, just use core result
            full_result = core_result
        
        # Parse test results from test execution
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
        observation = GoObservation(
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
        Parse Go test output to count passed/failed tests.
        
        Go test output format:
        - "PASS" at the end means all tests passed
        - "FAIL" means some tests failed
        - Individual test results: "--- PASS: TestName (0.00s)" or "--- FAIL: TestName (0.00s)"
        - Summary: "PASS" or "FAIL TestPackage 0.001s"
        - Also: "ok  	package	0.001s" for pass, "FAIL	package	0.001s" for fail
        
        Args:
            stdout: Standard output from Go execution
            stderr: Standard error from Go execution
            
        Returns:
            Tuple of (tests_passed, tests_failed)
        """
        passed = 0
        failed = 0
        output = stdout + "\n" + stderr
        
        # Count individual test passes and failures
        # Pattern: "--- PASS: TestName (duration)"
        pass_pattern = r"--- PASS:\s+(\w+)"
        fail_pattern = r"--- FAIL:\s+(\w+)"
        
        pass_matches = re.findall(pass_pattern, output)
        fail_matches = re.findall(fail_pattern, output)
        
        passed = len(pass_matches)
        failed = len(fail_matches)
        
        # If no individual test results found, check overall result
        if passed == 0 and failed == 0:
            # Check if all tests passed
            if re.search(r"^PASS\s*$", output, re.MULTILINE) or re.search(r"^ok\s+", output, re.MULTILINE):
                # This means tests ran but we didn't catch individual results
                # Look for "testing:" or "RUN" to see if tests actually ran
                if "=== RUN" in output or "testing:" in output:
                    # Tests ran but we couldn't parse individual results
                    # Assume at least 1 test passed since overall result is PASS
                    passed = 1
            elif re.search(r"^FAIL", output, re.MULTILINE):
                # Overall FAIL but couldn't parse individual tests
                # Assume at least 1 test failed
                failed = 1
        
        return passed, failed

    def _calculate_reward(self, code_compiles: bool, tests_passed: int, tests_failed: int) -> int:
        """
        Optimized integer reward for Go GRPO.
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
    def state(self) -> GoState:
        """Return current environment state."""
        return self._state

