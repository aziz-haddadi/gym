from enum import StrEnum


class MuscleGroup(StrEnum):
    CHEST = "Chest"
    BACK = "Back"
    SHOULDERS = "Shoulders"
    BICEPS = "Biceps"
    TRICEPS = "Triceps"
    FOREARMS = "Forearms"
    LEGS = "Legs"
    CORE = "Core"
    CARDIO = "Cardio"
    OTHER = "Other"


MUSCLE_GROUP_VALUES = tuple(group.value for group in MuscleGroup)
