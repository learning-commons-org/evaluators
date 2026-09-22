from enum import StrEnum

class ScopeAndSequenceFullView(StrEnum):
    FULL = "full"

    def __str__(self) -> str:
        return str(self.value)
