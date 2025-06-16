# run.py
import uvicorn
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

def setup_directories():
    """Create all necessary directories for the application."""
    # List of directories that need to exist
    directories = [
        "hls",
        "hls/keys", 
        "uploads_encrypted",
        "uploads_originals",
        "uploads_temp",
        "app/static/css",
        "app/static/js"
    ]
    
    print("🔧 Setting up Sectify directories...")
    
    for directory in directories:
        dir_path = Path(directory)
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ {directory}")
        except Exception as e:
            print(f"❌ Failed to create {directory}: {e}")
    
    print("✅ Directory setup completed!")

if __name__ == "__main__":
    # Setup directories first
    setup_directories()
    
    # Get host and port from environment variables or use default values
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    
    # reload=True helps automatically reload the server when code changes
    # very useful in a development environment
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
