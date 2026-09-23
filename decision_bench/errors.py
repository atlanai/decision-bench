class CallError(Exception):
    """A provider call failed. `metadata` keeps usage/cost that was still reported (a paid failure)."""

    def __init__(self, message, *, raw=None, retryable=False, status=None, metadata=None):
        super().__init__(message)
        self.raw, self.retryable, self.status = raw, retryable, status
        self.metadata = metadata or {}
