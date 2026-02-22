"""NEXUS service registry — lightweight dependency injection."""

from __future__ import annotations

from typing import TypeVar

from nexus.core.errors import NexusError

T = TypeVar("T")


class ServiceNotFoundError(NexusError):
    """Requested service is not registered."""


class Registry:
    """Service locator / lightweight DI container."""

    def __init__(self) -> None:
        self._services: dict[type, object] = {}

    def register(self, service_type: type[T], instance: T) -> None:
        """Register a service instance by its type."""
        self._services[service_type] = instance

    def get(self, service_type: type[T]) -> T:
        """Retrieve a registered service. Raises ServiceNotFoundError if missing."""
        instance = self._services.get(service_type)
        if instance is None:
            raise ServiceNotFoundError(f"Service {service_type.__name__} not registered")
        return instance  # type: ignore[return-value]

    def has(self, service_type: type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services
