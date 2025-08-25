
import os
import logging
from colorlog import ColoredFormatter

def initialize_logger(log_name, log_level, log_dir):
    LOG_LEVELS = {
            "NOTSET": logging.NOTSET,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }

    formatter = ColoredFormatter(
            "%(log_color)s[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'white,bold',
                'NOTSET': 'cyan,bold',
                'WARNING': 'yellow',
                'ERROR': 'red,bold',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )

    p = os.path.split(log_dir)[0]
    os.makedirs(p, exist_ok=True)
    # if not os.path.exists('./log'):
    #     os.makedirs('./log')

    logger = logging.getLogger(log_name)
    logger.setLevel(LOG_LEVELS[log_level.upper()])

    if not logger.hasHandlers():
        
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        file_handler = logging.FileHandler(filename=log_dir)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

def seg_logger(logger):
    global LOGGER
    LOGGER = logger

def get_logger():
    return LOGGER

LOGGER = None