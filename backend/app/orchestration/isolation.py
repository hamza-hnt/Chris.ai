import logging
import uuid
from contextlib import contextmanager
from collections.abc import Iterator

from app.config import get_settings

logger = logging.getLogger("chris.isolation")


class IsolationError(ValueError):
    pass


def normalize_property_id(property_id: str | uuid.UUID | None) -> uuid.UUID:
    if property_id is None:
        settings = get_settings()
        message = "Repository call rejected because property_id is required."
        if settings.APP_ENV == "test":
            raise IsolationError(message)
        logger.error(message)
        raise IsolationError(message)
    if isinstance(property_id, uuid.UUID):
        return property_id
    return uuid.UUID(str(property_id))


@contextmanager
def scoped(property_id: str | uuid.UUID | None) -> Iterator[uuid.UUID]:
    normalized = normalize_property_id(property_id)
    settings = get_settings()
    if settings.APP_ENV in {"development", "test"}:
        logger.info("Scoped repository access property_id=%s", normalized)
    yield normalized
