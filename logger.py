import logging
import os

FORMAT = logging.Formatter('%(asctime)s [%(threadName)s %(module)s %(lineno)d] %(levelname)s: %(message)s')


def get_logger(name):
    log_filename = f"logs/{name}.log"
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(FORMAT)
    logger.addHandler(ch)

    # File Handler
    ch = logging.FileHandler(log_filename)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(FORMAT)
    logger.addHandler(ch)
    logger.propagate = False

    return logger
