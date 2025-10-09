import logging

logging.basicConfig(
    level=logging.DEBUG,  # Can be INFO, WARNING, ERROR, CRITICAL
    format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("game")