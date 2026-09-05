from dataclasses import dataclass


@dataclass
class Check:
    name: str
    label: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "label": self.label, "passed": self.passed, "detail": self.detail}
