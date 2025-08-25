#!/usr/bin/env python3
"""
Standalone version of WD14 Tagger that can run without Stable Diffusion WebUI
"""
import os
import sys
import argparse
from pathlib import Path
import base64
from io import BytesIO

from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from PIL import Image, ImageFile

# Add current directory to Python path so we can import tagger modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tagger.api import Api
from tagger import utils
from tagger.interrogator import Interrogator
from tagger import settings

# Initialize PIL
Image.init()
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Create FastAPI app
app = FastAPI(title="WD14 Tagger API", version="1.0.0")

# Serve static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

# Root endpoint with welcome message and API documentation
@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WD14 Tagger API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            code { background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
            pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
            .endpoint { margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; background-color: #f9f9f9; }
            .model-info { margin: 20px 0; padding: 15px; border-left: 4px solid #00cc7a; background-color: #f9f9f9; }
        </style>
    </head>
    <body>
        <h1>WD14 Tagger API</h1>
        <p>Welcome to the WD14 Tagger API. This standalone API allows you to interrogate images and get tags without requiring the Stable Diffusion WebUI.</p>
        
        <div class="endpoint">
            <h2>Web Interface</h2>
            <p><a href="/ui">Click here to access the web interface</a></p>
        </div>
        
        <div class="endpoint">
            <h2>Available Endpoints</h2>
            <p><strong>GET</strong> <code>/</code> - This page (API documentation)</p>
            <p><strong>GET</strong> <code>/ui</code> - Web interface for image tagging</p>
            <p><strong>GET</strong> <code>/tagger/v1/interrogators</code> - List available models</p>
            <p><strong>POST</strong> <code>/tagger/v1/interrogate</code> - Interrogate an image</p>
            <p><strong>POST</strong> <code>/tagger/v1/interrogate-categorized</code> - Interrogate an image with categorized tags</p>
            <p><strong>POST</strong> <code>/tagger/v1/unload-interrogators</code> - Unload models from memory</p>
        </div>

        <div class="endpoint">
            <h2>Example Usage</h2>
            <h3>Get available models:</h3>
            <pre>curl -X GET "http://127.0.0.1:8000/tagger/v1/interrogators"</pre>
            
            <h3>Interrogate an image:</h3>
            <pre>curl -X POST "http://127.0.0.1:8000/tagger/v1/interrogate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "image": "base64_encoded_image",
    "model": "wd-v1-4-moat-tagger.v2",
    "threshold": 0.5
}'</pre>
            
            <h3>Interrogate an image with categorized tags:</h3>
            <pre>curl -X POST "http://127.0.0.1:8000/tagger/v1/interrogate-categorized" \\
  -H "Content-Type: application/json" \\
  -d '{
    "image": "base64_encoded_image",
    "model": "wd-v1-4-moat-tagger.v2",
    "threshold": 0.5
}'</pre>
        </div>
        
        <div class="model-info">
            <h2>Local Model Support</h2>
            <p>This standalone version supports loading local models. To use local models:</p>
            <ol>
                <li>Create a directory structure as shown below</li>
                <li>Place your model files in the appropriate directories</li>
                <li>Restart the server to detect new models</li>
            </ol>
            
            <h3>Directory Structure:</h3>
            <pre>models/
├── deepdanbooru/
│   └── [model_name]/
│       ├── project.json
│       └── [other model files]
└── TaggerOnnx/
    └── [model_name]/
        ├── [model_name].onnx
        └── selected_tags.csv</pre>
            
            <h3>Supported Model Types:</h3>
            <ul>
                <li><strong>DeepDanbooru Models</strong> - Place in <code>models/deepdanbooru/[model_name]/</code></li>
                <li><strong>ONNX Models</strong> - Place in <code>models/TaggerOnnx/[model_name]/</code></li>
            </ul>
        </div>
        
        <div class="model-info">
            <h2>Downloading Models</h2>
            <p>Models can be automatically downloaded from HuggingFace or manually placed in the directories above.</p>
            
            <h3>Automatic Download (HuggingFace):</h3>
            <p>Supported models will be automatically downloaded when first used:</p>
            <ul>
                <li>WD14 ViT v1 and v2</li>
                <li>WD14 ConvNeXT v1 and v2</li>
                <li>WD14 ConvNeXTV2 v1</li>
                <li>WD14 SwinV2 v1</li>
                <li>WD14 moat tagger v2</li>
                <li>ML-Danbooru models</li>
            </ul>
            
            <h3>Manual Download:</h3>
            <p>To manually download models, visit the following repositories:</p>
            <ul>
                <li><a href="https://huggingface.co/SmilingWolf" target="_blank">SmilingWolf HuggingFace Repository</a></li>
                <li><a href="https://github.com/KichangKim/DeepDanbooru/releases" target="_blank">DeepDanbooru Models</a></li>
                <li><a href="https://huggingface.co/deepghs/ml-danbooru-onnx" target="_blank">ML-Danbooru ONNX Models</a></li>
            </ul>
        </div>

        <div class="endpoint">
            <h2>Authentication</h2>
            <p>To add authentication, set the <code>API_AUTH</code> environment variable:</p>
            <pre>API_AUTH=username:password python standalone.py</pre>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# Web UI endpoint
@app.get("/ui", response_class=HTMLResponse)
async def web_ui():
    # Get available models
    utils.refresh_interrogators()
    models = list(utils.interrogators.keys())
    default_model = models[0] if models else ""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WD14 Tagger - Web Interface</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            select, input[type="number"], input[type="file"] {{ width: 100%; padding: 8px; }}
            button {{ background-color: #007acc; color: white; padding: 10px 20px; border: none; cursor: pointer; }}
            button:hover {{ background-color: #005a9e; }}
            #result {{ margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #007acc; }}
            #image-preview {{ max-width: 100%; margin-top: 20px; }}
            .hidden {{ display: none; }}
            .tag-list {{ display: flex; flex-wrap: wrap; gap: 10px; }}
            .tag {{ background-color: #e9e9e9; padding: 5px 10px; border-radius: 15px; }}
            .model-info {{ margin-top: 20px; padding: 15px; border-left: 4px solid #00cc7a; background-color: #f9f9f9; }}
            .category {{ margin-bottom: 20px; }}
            .category h3 {{ margin-top: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WD14 Tagger - Web Interface</h1>
            <form id="tagging-form">
                <div class="form-group">
                    <label for="image">Select Image:</label>
                    <input type="file" id="image" name="image" accept="image/*" required>
                </div>
                
                <div class="form-group">
                    <label for="model">Model:</label>
                    <select id="model" name="model" required>
                        {''.join(f'<option value="{model}" {"selected" if model == default_model else ""}>{model}</option>' for model in models)}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="threshold">Threshold:</label>
                    <input type="number" id="threshold" name="threshold" step="0.01" min="0" max="1" value="0.5">
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="categorized" name="categorized"> 
                        Show categorized tags (characters, regular tags)
                    </label>
                </div>
                
                <button type="submit">Get Tags</button>
            </form>
            
            <div id="loading" class="hidden">
                <p>Processing image...</p>
            </div>
            
            <img id="image-preview" class="hidden" alt="Preview">
            
            <div id="result" class="hidden">
                <h2>Results</h2>
                <div id="tags-container"></div>
            </div>
            
            <div class="model-info">
                <h2>Local Models</h2>
                <p>To use local models, place them in the appropriate directories and restart the server:</p>
                <ul>
                    <li><strong>DeepDanbooru Models</strong>: <code>models/deepdanbooru/[model_name]/</code></li>
                    <li><strong>ONNX Models</strong>: <code>models/TaggerOnnx/[model_name]/</code></li>
                </ul>
                <p>After placing models, refresh this page to see them in the model selection dropdown.</p>
            </div>
        </div>

        <script>
            document.getElementById('image').addEventListener('change', function(e) {{
                const file = e.target.files[0];
                if (file) {{
                    const reader = new FileReader();
                    reader.onload = function(e) {{
                        const preview = document.getElementById('image-preview');
                        preview.src = e.target.result;
                        preview.classList.remove('hidden');
                    }};
                    reader.readAsDataURL(file);
                }}
            }});
            
            document.getElementById('tagging-form').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const form = new FormData(this);
                const imageFile = form.get('image');
                const categorized = document.getElementById('categorized').checked;
                
                if (!imageFile) {{
                    alert('Please select an image');
                    return;
                }}
                
                // Show loading
                document.getElementById('loading').classList.remove('hidden');
                document.getElementById('result').classList.add('hidden');
                
                try {{
                    // Convert image to base64
                    const base64Image = await new Promise((resolve) => {{
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(imageFile);
                    }});
                    
                    // Determine endpoint based on categorization option
                    const endpoint = categorized ? '/tagger/v1/interrogate-categorized' : '/tagger/v1/interrogate';
                    
                    // Send request to API
                    const response = await fetch(endpoint, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            image: base64Image,
                            model: form.get('model'),
                            threshold: parseFloat(form.get('threshold'))
                        }})
                    }});
                    
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    
                    const data = await response.json();
                    
                    // Display results
                    if (categorized) {{
                        displayCategorizedResults(data);
                    }} else {{
                        displayResults(data.caption);
                    }}
                }} catch (error) {{
                    console.error('Error:', error);
                    alert('Error processing image: ' + error.message);
                }} finally {{
                    document.getElementById('loading').classList.add('hidden');
                }}
            }});
            
            function displayResults(caption) {{
                const resultDiv = document.getElementById('result');
                const tagsContainer = document.getElementById('tags-container');
                
                tagsContainer.innerHTML = '';
                
                // Display ratings
                if (caption.rating && Object.keys(caption.rating).length > 0) {{
                    const ratingsDiv = document.createElement('div');
                    ratingsDiv.className = 'category';
                    ratingsDiv.innerHTML = '<h3>Ratings</h3>';
                    const ratingsList = document.createElement('div');
                    ratingsList.className = 'tag-list';
                    
                    for (const [rating, confidence] of Object.entries(caption.rating)) {{
                        const tag = document.createElement('span');
                        tag.className = 'tag';
                        tag.textContent = `${{rating}} (${{confidence.toFixed(3)}})`;
                        ratingsList.appendChild(tag);
                    }}
                    
                    ratingsDiv.appendChild(ratingsList);
                    tagsContainer.appendChild(ratingsDiv);
                }}
                
                // Display tags
                if (caption.tag && Object.keys(caption.tag).length > 0) {{
                    const tagsDiv = document.createElement('div');
                    tagsDiv.className = 'category';
                    tagsDiv.innerHTML = '<h3>Tags</h3>';
                    const tagsList = document.createElement('div');
                    tagsList.className = 'tag-list';
                    
                    // Sort tags by confidence
                    const sortedTags = Object.entries(caption.tag)
                        .sort((a, b) => b[1] - a[1]);
                    
                    for (const [tag, confidence] of sortedTags) {{
                        const tagElement = document.createElement('span');
                        tagElement.className = 'tag';
                        tagElement.textContent = `${{tag}} (${{confidence.toFixed(3)}})`;
                        tagsList.appendChild(tagElement);
                    }}
                    
                    tagsDiv.appendChild(tagsList);
                    tagsContainer.appendChild(tagsDiv);
                }}
                
                resultDiv.classList.remove('hidden');
            }}
            
            function displayCategorizedResults(data) {{
                const resultDiv = document.getElementById('result');
                const tagsContainer = document.getElementById('tags-container');
                
                tagsContainer.innerHTML = '';
                
                // Display ratings
                if (data.ratings && Object.keys(data.ratings).length > 0) {{
                    const ratingsDiv = document.createElement('div');
                    ratingsDiv.className = 'category';
                    ratingsDiv.innerHTML = '<h3>Ratings</h3>';
                    const ratingsList = document.createElement('div');
                    ratingsList.className = 'tag-list';
                    
                    for (const [rating, confidence] of Object.entries(data.ratings)) {{
                        const tag = document.createElement('span');
                        tag.className = 'tag';
                        tag.textContent = `${{rating}} (${{confidence.toFixed(3)}})`;
                        ratingsList.appendChild(tag);
                    }}
                    
                    ratingsDiv.appendChild(ratingsList);
                    tagsContainer.appendChild(ratingsDiv);
                }}
                
                // Display characters
                if (data.characters && Object.keys(data.characters).length > 0) {{
                    const charactersDiv = document.createElement('div');
                    charactersDiv.className = 'category';
                    charactersDiv.innerHTML = '<h3>Characters</h3>';
                    const charactersList = document.createElement('div');
                    charactersList.className = 'tag-list';
                    
                    // Sort characters by confidence
                    const sortedCharacters = Object.entries(data.characters)
                        .sort((a, b) => b[1] - a[1]);
                    
                    for (const [character, confidence] of sortedCharacters) {{
                        const tagElement = document.createElement('span');
                        tagElement.className = 'tag';
                        tagElement.textContent = `${{character}} (${{confidence.toFixed(3)}})`;
                        charactersList.appendChild(tagElement);
                    }}
                    
                    charactersDiv.appendChild(charactersList);
                    tagsContainer.appendChild(charactersDiv);
                }}
                
                // Display regular tags
                if (data.tags && Object.keys(data.tags).length > 0) {{
                    const tagsDiv = document.createElement('div');
                    tagsDiv.className = 'category';
                    tagsDiv.innerHTML = '<h3>Tags</h3>';
                    const tagsList = document.createElement('div');
                    tagsList.className = 'tag-list';
                    
                    // Sort tags by confidence
                    const sortedTags = Object.entries(data.tags)
                        .sort((a, b) => b[1] - a[1]);
                    
                    for (const [tag, confidence] of sortedTags) {{
                        const tagElement = document.createElement('span');
                        tagElement.className = 'tag';
                        tagElement.textContent = `${{tag}} (${{confidence.toFixed(3)}})`;
                        tagsList.appendChild(tagElement);
                    }}
                    
                    tagsDiv.appendChild(tagsList);
                    tagsContainer.appendChild(tagsDiv);
                }}
                
                resultDiv.classList.remove('hidden');
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# Initialize the tagger API
api = Api(app, None, prefix="/tagger/v1")

# Custom exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

def refresh_models():
    """Refresh the list of available models"""
    try:
        utils.refresh_interrogators()
        print(f"Available models: {list(utils.interrogators.keys())}")
    except Exception as e:
        print(f"Error loading models: {e}")

def main():
    parser = argparse.ArgumentParser(description="WD14 Tagger Standalone API")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the API on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the API on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--deepdanbooru-path", type=str, help="Path to DeepDanbooru models")
    parser.add_argument("--onnxtagger-path", type=str, help="Path to ONNX models")
    parser.add_argument("--hf-cache-dir", type=str, help="HuggingFace cache directory")
    
    args = parser.parse_args()
    
    # Set custom paths if provided
    if args.deepdanbooru_path:
        os.environ['DEEPDANBOORU_PROJECTS_PATH'] = args.deepdanbooru_path
        
    if args.onnxtagger_path:
        os.environ['ONNXTAGGER_PATH'] = args.onnxtagger_path
        
    if args.hf_cache_dir:
        os.environ['HF_HOME'] = args.hf_cache_dir
    
    # Refresh models
    refresh_models()
    
    # Run the API
    print(f"Starting WD14 Tagger API on http://{args.host}:{args.port}")
    print("Available endpoints:")
    print("  GET  / - API documentation and usage examples")
    print("  GET  /ui - Web interface for image tagging")
    print("  POST /tagger/v1/interrogate - Interrogate an image")
    print("  POST /tagger/v1/interrogate-categorized - Interrogate an image with categorized tags")
    print("  GET  /tagger/v1/interrogators - List available models")
    print("  POST /tagger/v1/unload-interrogators - Unload models from memory")
    
    uvicorn.run(
        "standalone:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()