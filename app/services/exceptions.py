class ServiceError(Exception):
    """Base error raised by the application layer."""


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class AuthenticationError(ServiceError):
    pass


class InputError(ServiceError):
    pass
