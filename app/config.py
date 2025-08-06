from .logger import logger
import json

class Config:
    """Configuration settings loaded from config.json."""
    def __init__(self):
        self.OllamaURL = ""
        self.ModelProviderURI = ""
        self.ModelProviderModel = ""
        self.ModelProviderAPIKey = ""
        self.Collection = ""
        self.ChromaDBURL = ""
        self.ChromDBTenants = ""
        self.ChromaDBDatabase = ""

config = Config()

def load_config(config_path: str) -> Config:
    global config
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            config.OllamaURL = data.get("OllamaURL", "")
            config.ModelProviderURI = data.get("ModelProviderURI", "")
            config.ModelProviderModel = data.get("ModelProviderModel", "")
            config.ModelProviderAPIKey = data.get("ModelProviderAPIKey", "")
            config.Collection = data.get("Collection", "")
            config.ChromaDBURL = data.get("ChromaDBURL", "")
            config.ChromDBTenants = data.get("ChromDBTenants", "")
            config.ChromaDBDatabase = data.get("ChromaDBDatabase", "")
    except FileNotFoundError:
        logger.critical("config.json not found. Please create one.")
        raise
    except json.JSONDecodeError as e:
        logger.critical(f"Failed to parse config.json: {e}")
        raise
