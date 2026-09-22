from enum import StrEnum

class NormalizedStatementTypeENUM(StrEnum):
    OTHER = "Other"
    STANDARD = "Standard"
    STANDARD_GROUPING = "Standard Grouping"

    def __str__(self) -> str:
        return str(self.value)
