from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCK = "block"
    HUMAN = "human"


@dataclass(frozen=True, slots=True)
class ContractRisk:
    code: str
    level: RiskLevel
    message: str
