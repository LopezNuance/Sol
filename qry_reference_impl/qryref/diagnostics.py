from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class Diagnostic:
    rule_id: str
    category: str
    severity: str
    target: str
    message: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def diag(rule_id: str, category: str, target: str, message: str, severity: str = "error") -> Diagnostic:
    return Diagnostic(rule_id=rule_id, category=category, severity=severity, target=target, message=message)
