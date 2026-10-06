from functools import lru_cache
from importlib.metadata import PackageMetadata, PackageNotFoundError, metadata

DISTRIBUTION_NAME = "async-payments-service"
FALLBACK_VERSION = "0.0.0+unknown"


@lru_cache
def _distribution() -> PackageMetadata | None:
    try:
        return metadata(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return None


def _field(name: str, default: str) -> str:
    package = _distribution()
    value = package[name] if package is not None else None
    return value or default


def service_version() -> str:
    return _field("Version", FALLBACK_VERSION)


def service_title() -> str:
    return _field("Name", DISTRIBUTION_NAME).replace("-", " ").replace("_", " ").title()
