"""
AdapterRegistry — discovers which adapter can handle a given file.

Usage:
    registry = AdapterRegistry()
    registry.register(ZerodhaAdapter())
    registry.register(ICICIAdapter())

    adapter = registry.detect(file_content, filename)
    if adapter:
        transactions = adapter.parse(file_content)
"""

from backend.services.import_engine.adapter import ImportAdapter


class AdapterRegistry:
    """Registry of all available import adapters."""

    def __init__(self) -> None:
        self._adapters: list[ImportAdapter] = []

    def register(self, adapter: ImportAdapter) -> None:
        """Register a new adapter."""
        self._adapters.append(adapter)

    def detect(self, content: str, filename: str | None = None) -> ImportAdapter | None:
        """
        Auto-detect which adapter can handle this file.
        Returns the first adapter whose detect() returns True, or None.
        """
        for adapter in self._adapters:
            try:
                if adapter.detect(content, filename):
                    return adapter
            except Exception:
                continue
        return None

    def get_by_source(self, source: str) -> ImportAdapter | None:
        """Get adapter by source name (e.g. 'ZERODHA')."""
        for adapter in self._adapters:
            if adapter.source.value == source.upper():
                return adapter
        return None

    @property
    def available_sources(self) -> list[str]:
        """List all registered source names."""
        return [a.source.value for a in self._adapters]
