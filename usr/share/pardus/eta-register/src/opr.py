#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import locale
import gettext
import logging
from config import APPNAME, TRANSLATIONS_PATH

# --- Environment Setup for pkexec ---
# Add the script's directory to the Python path to find local modules.
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# --- Basic Translation Setup ---
try:
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.textdomain(APPNAME)
    _ = gettext.gettext
except Exception as e:
    # We might not have a logger yet, so print to stderr as a fallback.
    print(f"Warning: Could not set up translations: {e}", file=sys.stderr)
    _ = str # Fallback


try:
    from config import PACKAGE_TO_INSTALL
    from logger import logger
except ImportError as e:
    # If we can't import, we can't log, so print to stderr and exit.
    print(f"FATAL: Could not import required modules: {e}", file=sys.stderr)
    sys.exit(1)

# The logger from logger.py is configured with both a file and a console handler.
# For this script, we only want the file handler to be active. The raw output
# for the UI is handled by print(). We remove the console/stream handler here
# to prevent formatted log messages from appearing in the installer's UI.
for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler):
        logger.removeHandler(handler)


def run_installation():
    """
    Runs the package installation command and prints its output in real-time.
    """
    command = ["apt-get", "install", "-y", PACKAGE_TO_INSTALL]
    
    logger.info("Executing command: {command}".format(command=' '.join(command)))

    try:
        # Start the subprocess
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            text=True,
            bufsize=1  # Line-buffered
        )

        # Read and print output line by line in real-time
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                # Print directly to stdout so the installer UI can capture it raw
                print(line, flush=True)
                # Also, log the output to the file with a timestamp for debugging
                logger.info("[apt] {line}".format(line=line))
        
        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            logger.info("Installation completed successfully.")
            return 0
        else:
            logger.error("Installation failed with exit code {return_code}.".format(return_code=return_code))
            return return_code

    except FileNotFoundError:
        logger.error("apt-get not found. The system might be misconfigured.")
        return 1
    except Exception as e:
        logger.error("An unexpected error occurred: {e}".format(e=e))
        return 1

def start_service(service_name):
    """
    Enables and starts a systemd service.
    """
    if not service_name:
        logger.error("No service name provided to start_service function.")
        return 1

    command = ["systemctl", "enable", "--now", service_name]
    logger.info("Executing command: {command}".format(command=' '.join(command)))
    
    try:
        # We don't need to capture output for the UI here, just the result.
        result = subprocess.run(
            command,
            check=True, # Raises CalledProcessError if command returns non-zero
            capture_output=True,
            text=True
        )
        logger.info("Service {service} started successfully.".format(service=service_name))
        logger.debug("systemctl stdout: {stdout}".format(stdout=result.stdout))
        return 0
    except FileNotFoundError:
        logger.error("systemctl not found. The system might be misconfigured.")
        return 1
    except subprocess.CalledProcessError as e:
        logger.error("Failed to start service {service}. Exit code: {code}".format(service=service_name, code=e.returncode))
        logger.error("systemctl stderr: {stderr}".format(stderr=e.stderr))
        return e.returncode
    except Exception as e:
        logger.error("An unexpected error occurred while starting service {service}: {e}".format(service=service_name, e=e))
        return 1


if __name__ == "__main__":
    logger.info("--- Installer Operation (opr.py) Starting ---")

    if len(sys.argv) > 1 and sys.argv[1] == 'start-service':
        if len(sys.argv) > 2:
            service_to_start = sys.argv[2]
            logger.info("Operation: Start service '{service}'".format(service=service_to_start))
            exit_code = start_service(service_to_start)
        else:
            logger.error("Operation 'start-service' requires a service name argument.")
            exit_code = 1
    else:
        # Default operation is installation
        logger.info("Operation: Install package")
        exit_code = run_installation()

    logger.info("--- Installer Operation (opr.py) Finished with exit code {exit_code} ---".format(exit_code=exit_code))
    sys.exit(exit_code)
