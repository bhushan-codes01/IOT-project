"""Conservative prototype rule for temperature-based fire risk."""
from dataclasses import dataclass
from enum import Enum


class FireLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    EMERGENCY = "EMERGENCY"


@dataclass(frozen=True)
class FireAssessment:
    level: FireLevel
    fire_status: bool
    message: str


def assess_fire_risk(temperature: float, threshold: float = 50.0) -> FireAssessment:
    """Temperature is a prototype signal, not proof or certified fire detection."""
    if temperature >= threshold:
        return FireAssessment(
            FireLevel.EMERGENCY,
            True,
            "Temperature reached the configured emergency threshold",
        )
    if temperature >= threshold * 0.8:
        return FireAssessment(
            FireLevel.WARNING,
            False,
            "Temperature is approaching the configured threshold",
        )
    return FireAssessment(FireLevel.NORMAL, False, "No temperature threshold alert")
