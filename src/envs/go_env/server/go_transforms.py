"""
envs/go_env/go_transforms.py
--------------------------------
Safety and quality transforms for Go code.
"""

import re
from core.env_server.base_transforms import CompositeTransform
from core.env_server.interfaces import Transform
from ..models import GoObservation


# -------------------------
# Safety Transform
# -------------------------
class GoSafetyTransform(Transform):
    """Detects dangerous Go operations and penalizes them with a negative reward."""

    def __init__(self, penalty: float = -3.0):
        self.penalty = penalty
        self.dangerous_patterns = [
            r"os\.Remove",
            r"os\.RemoveAll",
            r"os\.Exit",
            r"os\.Exec",
            r"os\.StartProcess",
            r"syscall\.",
            r"unsafe\.",
            r"exec\.Command",
            r"http\.Get",
            r"http\.Post",
            r"net\.Dial",
            r"ioutil\.WriteFile",
            r"os\.WriteFile",
            r"os\.Create",
            r"os\.OpenFile",
        ]

    def __call__(self, observation):
        # Only act on GoObservation objects
        if not isinstance(observation, GoObservation):
            return observation

        # Extract last executed code from metadata
        code = observation.metadata.get("last_code", "") if observation.metadata else ""

        for pattern in self.dangerous_patterns:
            if re.search(pattern, code):
                # Apply penalty and record violation
                observation.reward = (observation.reward or 0.0) + self.penalty
                observation.metadata = observation.metadata or {}
                observation.metadata["safety_violation"] = pattern
                return observation

        # Safe code gets neutral reward
        observation.reward = observation.reward or 0.0
        return observation


# -------------------------
# Quality Transform
# -------------------------
class GoQualityTransform(Transform):
    """Evaluates and rewards Go code quality."""

    def __init__(self, concise_bonus=1, max_length_threshold=120):
        self.concise_bonus = concise_bonus
        self.max_length_threshold = max_length_threshold

    def __call__(self, observation):
        # Only act on GoObservation objects
        if not isinstance(observation, GoObservation):
            return observation

        code = observation.metadata.get("last_code", "") if observation.metadata else ""
        reward = observation.reward or 0.0

        # Reward concise code
        if len(code.strip()) <= self.max_length_threshold:
            reward += self.concise_bonus
        else:
            reward -= 0.1  # slight penalty for verbosity

        observation.reward = reward
        return observation


# -------------------------
# Composite Transform
# -------------------------
def create_safe_go_transform():
    """Combines safety and quality transforms into one pipeline."""
    return CompositeTransform([GoSafetyTransform(), GoQualityTransform()])

