from enum import StrEnum

class AdoptionStatusENUM(StrEnum):
    ADOPTED = "Adopted"
    DRAFT = "Draft"
    IMPLEMENTED = "Implemented"
    PROPOSED = "Proposed"
    RETIRED = "Retired"

    def __str__(self) -> str:
        return str(self.value)
