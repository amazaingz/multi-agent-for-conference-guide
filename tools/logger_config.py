"""
Centralized logging configuration for the application.
"""

import logging


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name, defaults to the calling module's __name__

    Returns:
        Configured logger instance
    """
    # Configure logging if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    return logging.getLogger(name)
