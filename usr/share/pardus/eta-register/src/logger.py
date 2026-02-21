import logging
import sys
from pathlib import Path
from datetime import datetime
from config import APPNAME, LOG_FILE

def setup_logger():
    """
    Sets up a robust, centralized logger for the application.
    - Logs to a single file: /var/log/eta-register.log
    - If writing to the system-wide log path fails, it logs to the console only.
    - Always logs WARNING and higher to the console (stderr).
    """
    logger = logging.getLogger(APPNAME)
    logger.setLevel(logging.INFO)

    # Prevent adding multiple handlers if this function is called more than once
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')
    
    file_handler = None

    # --- Attempt to configure the system-wide log file ---
    try:
        # Path format: /var/log/eta-register/YYYY/MM/DD/HH.log
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

    except (IOError, OSError) as e:
        # This is expected if the app is run by a non-root user.
        # The console logger below will handle the output.
        pass

    # --- Always add a console handler for critical messages ---
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO) # Show all logs in terminal
    logger.addHandler(console_handler)

    if not file_handler:
        # This warning will go to the console handler
        logger.warning(f"Could not write to log file {LOG_FILE}. File logging is disabled.")

    return logger

# Create a single logger instance to be used across the application
logger = setup_logger()
