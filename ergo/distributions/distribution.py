"""
Base Distribution Class

Specifies interface for specific Distribution Classes
"""

from abc import ABC, abstractmethod


class Distribution(ABC):
    @abstractmethod
    def ppf(self, q):
        ...

    def percentiles(self, percentiles=None):
        from . import conditions

        if percentiles is None:
            percentiles = [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
        values = [self.ppf(q) for q in percentiles]
        return [
            conditions.IntervalCondition(percentile, max=float(value))
            for (percentile, value) in zip(percentiles, values)
        ]
