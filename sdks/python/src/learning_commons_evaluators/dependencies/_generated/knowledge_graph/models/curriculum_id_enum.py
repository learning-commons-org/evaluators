from enum import StrEnum

class CurriculumIdENUM(StrEnum):
    IM360 = "im360"

    def __str__(self) -> str:
        return str(self.value)
