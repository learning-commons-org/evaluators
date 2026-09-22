from enum import StrEnum

class ScopeAndSequenceSummaryView(StrEnum):
    SUMMARY = "summary"

    def __str__(self) -> str:
        return str(self.value)
