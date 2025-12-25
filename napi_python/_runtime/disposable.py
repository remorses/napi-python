"""
Base class for disposable resources.

Reference: https://github.com/toyobayashi/emnapi/blob/main/packages/runtime/src/Disaposable.ts
"""

from abc import ABC, abstractmethod


class Disposable(ABC):
    """Base class for resources that need explicit cleanup."""

    @abstractmethod
    def dispose(self) -> None:
        """Clean up resources."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.dispose()
