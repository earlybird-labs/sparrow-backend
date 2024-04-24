# logger.py

import logging


class Logger:
    """
    A reusable logger class that configures and provides a logger.
    """

    def __init__(
        self,
        name=__name__,
        level=logging.INFO,
        format_string="%(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d - %(funcName)s - %(message)s",
    ):
        """
        Initializes the Logger instance with the specified name, level, and format.

        :param name: Name of the logger, defaults to __name__ to use the name of the module where it is used.
        :param level: Logging level, defaults to logging.INFO.
        :param format_string: Format of the log messages.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        formatter = logging.Formatter(format_string)

        # Create console handler and set level and formatter
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(ch)

    def get_logger(self):
        """
        Returns the configured logger.

        :return: Configured logger object.
        """
        return self.logger


# Example usage:
logger_instance = Logger(__name__, logging.INFO)
logger = logger_instance.get_logger()
