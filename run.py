#!/usr/bin/env python3
"""
Simple script to run the Box Office API locally for development.
"""

import uvicorn
from app.core.config import config
from app.core.logging import setup_logging


if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    print("🎭 Starting Ayush_Kumar_Agrawal's Box Office API...")
    print(f"📡 Server will be available at: http://{config.host}:{config.port}")
    print(f"📚 API Documentation at: http://{config.host}:{config.port}/docs")
    print(f"🔍 Health check at: http://{config.host}:{config.port}/api/v1/health")
    print(f"📊 Metrics at: http://{config.host}:{config.port}/metrics")
    print()
    print("Press Ctrl+C to stop the server")
    print()
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
