import logging
import os
from datetime import datetime


class Logger:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not Logger._initialized:
            self.logger = logging.getLogger("eta_register")
            self.logger.setLevel(logging.DEBUG)

            # Create logs directory if it doesn't exist
            log_dir = os.path.expanduser("~/.eta-register/logs")
            # just for testing make it ./log
            # log_dir = "./log"
            os.makedirs(log_dir, exist_ok=True)

            # File handler
            log_file = os.path.join(
                log_dir, f'eta_register_{datetime.now().strftime("%Y%m%d")}.log'
            )
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            # Formatter
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # Add handlers
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

            Logger._initialized = True

    def debug(self, message):
        print(message)  # Print to console first
        self.logger.debug(message)

    def info(self, message):
        print(message)  # Print to console first
        self.logger.info(message)

    def warning(self, message):
        print(message)  # Print to console first
        self.logger.warning(message)

    def error(self, message):
        print(message)  # Print to console first
        self.logger.error(message)

    def critical(self, message):
        print(message)  # Print to console first
        self.logger.critical(message)


# Create a global logger instance
logger = Logger()
