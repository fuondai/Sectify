#!/usr/bin/env python3
"""Script to ensure all necessary directories exist for Sectify application."""

import os
from pathlib import Path

def setup_directories():
    """Create all necessary directories for the application."""
    # Get project root directory
    project_root = Path(__file__).parent.parent
    
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
        dir_path = project_root / directory
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ {directory}")
        except Exception as e:
            print(f"❌ Failed to create {directory}: {e}")
    
    print("✅ Directory setup completed!")

if __name__ == "__main__":
    setup_directories() 