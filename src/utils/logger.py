import logging
import os
from logging.handlers import RotatingFileHandler

from src.config import settings


def setup_logger(name: str = "automated_report_generator") -> logging.Logger:
    logger = logging.getLogger(name)

    # If logger is already configured, don't add handlers again
    if logger.handlers:
        return logger

    logger.setLevel(settings.log_level)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback if logs directory is not writable (e.g. some restricted environments)
        print(f"Failed to setup file log handler: {e}")

    return logger


# Shared main logger instance
logger = setup_logger()
