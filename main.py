# main.py
from src import run
from loggers import setup_logging

import logging

# Initialize loggers once at startup
setup_logging()
logger = logging.getLogger(__name__)


def main():
    logger.info("Game starting up...")

    # --- rest of your game loop ---
    try:
        # Example of normal game logic
        logger.debug("Loading game assets...")
        # your code here

    except Exception as e:
        logger.exception("Unhandled exception occurred: %s", e)

if __name__ == "__main__":
    main()
    run()
