class StudyCoachError(Exception):
    """Base class for public domain errors."""


class DuplicateDateError(StudyCoachError):
    pass


class RecordNotFoundError(StudyCoachError):
    pass


class DataStoreError(StudyCoachError):
    pass


class AIProviderError(StudyCoachError):
    pass
