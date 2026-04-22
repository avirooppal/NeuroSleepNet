"""
TransparentProxy — makes nsn.wrap(agent) a true transparent proxy.

Contracts:
  isinstance(wrapped, OriginalClass)  → True
  wrapped.__class__.__name__          → matches original
  wrapped.__doc__, __module__         → preserved
  All call signatures preserved (positional, keyword, *args, **kwargs)
"""
import functools
from typing import Any


class TransparentProxy:
    """
    Wraps an agent so callers cannot distinguish it from the original.
    The NSN-augmented call is injected transparently.

    Usage:
        wrapped = TransparentProxy(original_agent, augmented_callable)
        # isinstance(wrapped, type(original_agent)) → True
        # wrapped(query) → augmented_callable(query)
    """

    def __init__(self, original: Any, augmented_callable: Any):
        self._original = original
        self._augmented = augmented_callable

        # Preserve identity metadata
        try:
            functools.update_wrapper(self, original)
        except (TypeError, AttributeError):
            pass

        # Override __class__ so isinstance() checks pass
        # This is the standard technique used by mock libraries and proxies.
        self.__class__ = type(
            type(original).__name__,
            (TransparentProxy, type(original)),
            {"__init__": TransparentProxy.__init__},
        )

    def __call__(self, *args, **kwargs):
        """Route all calls through the augmented callable."""
        return self._augmented(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate all attribute access to the original agent."""
        return getattr(self._original, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting proxy internals; everything else goes to original."""
        if name.startswith('_') or name in ('__class__', '__dict__', '__wrapped__'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._original, name, value)

    def __repr__(self) -> str:
        return f"NSN({repr(self._original)})"

    def __str__(self) -> str:
        return str(self._original)
