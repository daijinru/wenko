from app.server import app, init_app 
from app.logger import logger

if __name__ == "__main__":
    try:
        init_app() # Initialize configuration and ChromaDB
        logger.info("✅ Server running on :8080")
        # Run Flask app. host="0.0.0.0" makes it accessible externally.
        # debug=False for production, set to True for development for auto-reloading and detailed errors.
        app.run(host="0.0.0.0", port=8080, debug=False)
    except Exception as e:
        logger.critical(f"Application failed to start: {e}")
        exit(1)
