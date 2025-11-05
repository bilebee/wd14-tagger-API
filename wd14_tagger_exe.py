#!/usr/bin/env python3
"""
Standalone executable for WD14 Tagger API
This is a simplified version that only works as a standalone application
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path so we can import tagger modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock modules that might not be available in standalone mode
try:
    import safehttpx
except ImportError:
    import types
    safehttpx = types.ModuleType('safehttpx')
    safehttpx.__version__ = "1.0.0"
    sys.modules['safehttpx'] = safehttpx

# Initialize PIL
try:
    from PIL import Image, ImageFile
    Image.init()
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except ImportError:
    print("Warning: PIL/Pillow not available")

# Create FastAPI app
try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    app = FastAPI(title="WD14 Tagger API", version="1.0.0")
except ImportError as e:
    print(f"Error importing FastAPI: {e}")
    sys.exit(1)

# Serve static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

def main():
    """
    Main function that mimics the behavior of run_server.bat:
    python standalone.py --port 8080 --host 0.0.0.0
    """
    print("Starting WD14 Tagger Server...")
    print()
    
    # Import uvicorn here to ensure all mocks are in place
    try:
        import uvicorn
    except ImportError as e:
        print(f"Error importing uvicorn: {e}")
        print("Please make sure you have installed all required dependencies")
        print("Make sure you have installed the required packages:")
        print("  pip install fastapi uvicorn pillow pydantic")
        print("For full functionality, you might also need:")
        print("  pip install gradio onnxruntime tensorflow huggingface-hub")
        return 1
    
    # Set default arguments to match run_server.bat
    host = "0.0.0.0"
    port = 8080
    
    # Import standalone module components
    try:
        import standalone
        # Mount the standalone app to preserve middleware, routes, and state
        app.mount("/", standalone.app)
    except ImportError:
        print("Error: Could not import standalone module")
        return 1
    except Exception as e:
        print(f"Error importing standalone app: {e}")
        return 1
    
    # Refresh models
    try:
        from tagger import utils
        utils.refresh_interrogators()
        print(f"Available models: {list(utils.interrogators.keys())}")
    except Exception as e:
        print(f"Warning: Error loading models: {e}")
    
    # Run the API with default parameters from run_server.bat
    print(f"Starting WD14 Tagger API on http://{host}:{port}")
    print("Available endpoints:")
    print("  GET  / - API documentation and usage examples")
    print("  GET  /ui - Web interface for image tagging")
    print("  POST /tagger/v1/interrogate - Interrogate an image")
    print("  POST /tagger/v1/interrogate-categorized - Interrogate an image with categorized tags")
    print("  GET  /tagger/v1/interrogators - List available models")
    print("  POST /tagger/v1/unload-interrogators - Unload models from memory")
    
    try:
        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"\nError occurred while starting the server: {e}")
        print("Please make sure you have installed all required dependencies")
        print("Make sure you have installed the required packages:")
        print("  pip install fastapi uvicorn pillow pydantic")
        print("For full functionality, you might also need:")
        print("  pip install gradio onnxruntime tensorflow huggingface-hub")
        return 1
    
    print("\nServer stopped.")
    return 0

if __name__ == "__main__":
    sys.exit(main())