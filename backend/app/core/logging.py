import logging
import sys
from app.core.config import settings


def setup_logging():
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Suppress verbose 3rd party logs
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    return logging.getLogger("app")


logger = setup_logging()
