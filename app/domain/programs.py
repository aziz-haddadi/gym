from enum import StrEnum


class ProgramStepType(StrEnum):
    WORKOUT = "workout"
    REST = "rest"


PROGRAM_STEP_TYPE_VALUES = tuple(item.value for item in ProgramStepType)
