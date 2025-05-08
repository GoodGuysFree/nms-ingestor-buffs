import logging
import sys
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init()

def create_logger(script_name, log_file):
    """
    Create a logger with colored console output and colorless file output.
    Console output mimics Discord's logging style with timestamps.
    Logs are written to the specified log_file, with script_name distinguishing entries.

    Args:
        script_name (str): Name of the script for log prefix.
        log_file (str): Path to the log file.

    Returns:
        logging.Logger: Configured logger instance.
    """
    if not script_name:
        script_name = Path(sys.argv[0]).stem if sys.argv[0] else 'script'

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)  # Capture all levels

    # Remove any existing handlers to prevent duplicates
    logger.handlers.clear()

    # File handler (matches console format, without color)
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Stream handler (colored, with timestamp)
    stream_handler = logging.StreamHandler(sys.stdout)
    def colored_formatter(record):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        message = record.getMessage()
        color = {
            'INFO': Fore.CYAN,
            'DEBUG': Fore.LIGHTBLACK_EX,
            'WARNING': Fore.YELLOW,
            'ERROR': Fore.RED
        }.get(level, Fore.WHITE)
        return f"{timestamp} {color}{level:<8}{Style.RESET_ALL} {Fore.YELLOW}{script_name}{Style.RESET_ALL} {message}"
    stream_handler.setFormatter(logging.Formatter(fmt='%(message)s'))
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.format = colored_formatter
    logger.addHandler(stream_handler)

    return logger