"""Logging configuration for the application"""
import logging
import os
from src.config.settings import settings


def setup_logging():
    """Configure logging for the application"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(settings.log_level)

    if logger.handlers:
        return logger

    file_handler = logging.FileHandler("logs/agent.log")
    file_handler.setLevel(settings.log_level)
    file_handler.setFormatter(logging.Formatter(log_format))

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(settings.log_level)
    stream_handler.setFormatter(logging.Formatter(log_format))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


# Initialize logger
logger = setup_logging()
