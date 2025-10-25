"""
Julia Code Action Environment.

This environment mirrors the PythonCodeActEnv but runs Julia code instead.
It executes Julia code using JuliaExecutor, captures output,
tracks the last exit code, and returns a JuliaObservation.
"""

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

        observation = self.transform(observation)
        return observation
        

    def step(self, action: JuliaAction) -> JuliaObservation:
        """
        Execute Julia code and return the result as JuliaObservation.
        """
        if not isinstance(action, JuliaAction):
            raise ValueError(f"Expected JuliaAction, got {type(action)}")

        # Execute the code using JuliaExecutor
        result = self._executor.run(action.code)

        # Update environment state
        self._state.step_count += 1
        self._state.last_exit_code = result.exit_code

        # Build observation
        observation = JuliaObservation(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            reward=0.0,
            metadata={"last_code": action.code},
            tests_passed=0,
            tests_failed=0
        )

        # Apply safety and quality transforms
        observation = self.transform(observation)

        return observation

    @property
    def state(self) -> JuliaState:
        """Return current environment state."""
        return self._state
