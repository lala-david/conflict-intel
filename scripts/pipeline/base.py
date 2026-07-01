"""Connector interface — every source is a small module with a uniform contract."""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ExtractResult:
    """Outcome of one connector run (for health/observability)."""
    source: str
    records: list[dict] = field(default_factory=list)
    ok: bool = True
    error: str = ""


class Connector:
    """A data source: a name + fetch() returning raw record dicts."""

    name: str = "base"

    def fetch(self) -> list[dict]:  # pragma: no cover - interface
        raise NotImplementedError

    def run(self) -> ExtractResult:
        """Fetch with error isolation so one bad source never kills the run."""
        try:
            records = self.fetch() or []
            return ExtractResult(self.name, records, ok=True)
        except Exception as e:  # noqa: BLE001 - collectors must never crash the run
            return ExtractResult(self.name, [], ok=False, error=str(e))


class FnConnector(Connector):
    """Adapt an existing fetch function (sources.py etc.) into a Connector."""

    def __init__(self, name: str, fn: Callable, *args, **kwargs):
        self.name = name
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def fetch(self) -> list[dict]:
        return self._fn(*self._args, **self._kwargs)
