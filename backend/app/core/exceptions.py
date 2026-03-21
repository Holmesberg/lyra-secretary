"""Core application exceptions."""

class ImmutableTaskError(Exception):
    """Raised when attempting to modify an immutable task."""
    pass

class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass
