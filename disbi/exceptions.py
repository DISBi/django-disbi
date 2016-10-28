"""
Custom DISBI exceptions.
"""

class NoRelatedMeasurementModel(Exception):
    """Raise if an experiment has no data attached to it."""
    def __init__(self, exp, *args, **kwargs):
        self.exp = exp
        super().__init__(*args, **kwargs)
        
class NotSupportedError(Exception):
    """Raise if a requested operation is not supported."""
    pass
        
class NotFoundError(Exception):
    """Raise if a value for a variable could not be set."""
    pass
