from enum import StrEnum

class LanguageENUM(StrEnum):
    EN_US = "en-US"
    ES_US = "es-US"

    def __str__(self) -> str:
        return str(self.value)
