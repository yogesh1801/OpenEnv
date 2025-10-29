"""
envs/ruby_env/ruby_transforms.py
--------------------------------
Safety and quality transforms for Ruby code.
"""

import re
from core.env_server.base_transforms import CompositeTransform
from core.env_server.interfaces import Transform
from ..models import RubyObservation


# -------------------------
# Safety Transform
# -------------------------
class RubySafetyTransform(Transform):
    """Detects dangerous Ruby operations and penalizes them with a negative reward."""

    def __init__(self, penalty: float = -3.0):
        self.penalty = penalty
        self.dangerous_patterns = [
            r"`",                    # Backticks for shell execution
            r"system\(",             # System calls
            r"exec\(",               # Exec calls
            r"spawn\(",              # Spawn processes
            r"eval\(",               # Eval is dangerous
            r"File\.delete",         # File deletion
            r"File\.unlink",         # File deletion
            r"FileUtils\.rm",        # File removal
            r"Dir\.delete",          # Directory deletion
            r"require\s+['\"]open-uri['\"]",  # Network access
            r"Net::HTTP",            # HTTP requests
            r"open\(",               # Open can be used for URLs
            r"IO\.popen",            # Process pipes
            r"Kernel\.fork",         # Forking processes
        ]

    def __call__(self, observation):
        # Only act on RubyObservation objects
        if not isinstance(observation, RubyObservation):
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
class RubyQualityTransform(Transform):
    """Evaluates and rewards Ruby code quality."""

    def __init__(self, concise_bonus=1, max_length_threshold=120):
        self.concise_bonus = concise_bonus
        self.max_length_threshold = max_length_threshold

    def __call__(self, observation):
        # Only act on RubyObservation objects
        if not isinstance(observation, RubyObservation):
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
def create_safe_ruby_transform():
    """Combines safety and quality transforms into one pipeline."""
    return CompositeTransform([RubySafetyTransform(), RubyQualityTransform()])

