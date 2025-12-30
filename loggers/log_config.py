import logging
from os import path
from pathlib import Path

log_dir = Path.home() / 'PycharmProjects/SideScollerUnderwater/loggers'


def setup_logging():
    """Configure loggers for the entire SideScrollerUnderwater project."""
    # --- Define log file paths --
    basic_log_path = path.join(log_dir, "basic.log")
    error_log_path = path.join(log_dir, "errors.log")
    test_log_path = path.join(log_dir, "test.log")

    # --- Set handlers to log by severity --- #
    error_handler = logging.FileHandler(error_log_path, mode="w", encoding="utf-8")
    error_handler.setLevel(logging.WARNING)

    basic_handler = logging.FileHandler(basic_log_path, mode="w", encoding="utf-8")
    basic_handler.setLevel(logging.INFO)

    # --- Configure basic loggers ---
    logging.basicConfig(
        level=logging.INFO,  # Can be DEBUG, INFO, WARNING, ERROR, CRITICAL
        # filename=...,
        # filemode='w',
        format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            error_handler,
            basic_handler,
            logging.StreamHandler(),  # also log to console
        ]
    )

    # # --- Create a custom logger ---
    # logger = loggers.getLogger(__name__)

    # --- Add an extra file handler (test.log) ---
    # handler = loggers.FileHandler(test_log_path)
    # formatter = loggers.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    # handler.setFormatter(formatter)
    # logger.addHandler(handler)

    # --- Example log message ---
    logging.info("Logging initialized. Logs stored in %s", log_dir)
    logging.info("Test the custom logger")


if __name__ == "__main__":
    setup_logging()