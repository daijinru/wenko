import logging
import os

# Define logger first
logger = logging.getLogger(__name__)

def setup_logger(log_dir: str):
    global logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "app.log")),
            logging.StreamHandler()
        ]
    )
    logger.info("Logger initialized.")