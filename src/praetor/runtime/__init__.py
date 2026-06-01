"""Runtime primitives — process singleton and startup coordination."""

from praetor.runtime.singleton import SingletonLock, SingletonLockError

__all__ = ["SingletonLock", "SingletonLockError"]
