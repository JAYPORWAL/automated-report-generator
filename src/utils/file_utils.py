import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Generator

from src.utils.logger import logger


def ensure_directory(path: str) -> None:
    """Ensures a directory exists, creating it if necessary."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise


@contextmanager
def temporary_directory() -> Generator[str, None, None]:
    """Context manager to create a temporary directory and safely delete it on exit."""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        safe_remove_directory(temp_dir)


def safe_remove_directory(path: str) -> None:
    """Safely removes a directory and all of its contents, logging errors on failure."""
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            logger.info(f"Successfully cleaned up temporary directory: {path}")
        except Exception as e:
            logger.warning(f"Error cleaning up directory {path}: {e}")


def safe_remove_file(path: str) -> None:
    """Safely removes a single file, logging errors on failure."""
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"Successfully cleaned up file: {path}")
        except Exception as e:
            logger.warning(f"Error cleaning up file {path}: {e}")
