from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(slots=True)
class ACLMessage:
    performative: str
    sender: str
    receiver: str
    content: Dict[str, Any] = field(default_factory=dict)
