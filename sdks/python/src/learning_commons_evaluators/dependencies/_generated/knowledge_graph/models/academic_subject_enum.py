from enum import StrEnum

class AcademicSubjectENUM(StrEnum):
    ENGLISH_LANGUAGE_ARTS = "English Language Arts"
    MATHEMATICS = "Mathematics"
    OTHER = "Other"
    SCIENCE = "Science"
    SOCIAL_STUDIES = "Social Studies"

    def __str__(self) -> str:
        return str(self.value)
