from enum import StrEnum

class GradeLevelENUM(StrEnum):
    K = "K"
    PK = "PK"
    VALUE_10 = "9"
    VALUE_11 = "10"
    VALUE_12 = "11"
    VALUE_13 = "12"
    VALUE_2 = "1"
    VALUE_3 = "2"
    VALUE_4 = "3"
    VALUE_5 = "4"
    VALUE_6 = "5"
    VALUE_7 = "6"
    VALUE_8 = "7"
    VALUE_9 = "8"

    def __str__(self) -> str:
        return str(self.value)
