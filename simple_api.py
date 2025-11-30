"""Simple API for WD14 Tagger"""
import os
import sys
import argparse
import json
from typing import Dict, List, AsyncIterator
from threading import Lock
from io import BytesIO
import asyncio
from contextlib import asynccontextmanager
from PIL import Image
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Add the project root to the path so we can import tagger modules
sys.path.insert(0, os.path.dirname(__file__))

from tagger import utils

# Models
class InterrogateResponse(BaseModel):
    ratings: Dict[str, float]
    characters: Dict[str, float]
    tags: Dict[str, float]

# Global variables
queue_lock = Lock()
interrogator_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan event handler to manage startup and shutdown events"""
    global interrogator_instance
    
    # Startup logic
    try:
        # Create default config file if it doesn't exist
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            default_config = """model:
  default: wd14

tagging:
  max_tags_per_category: 1000
  min_tag_score: 0.05

server:
  host: 127.0.0.1
  port: 8080
  reload: false

paths:
  deepdanbooru: null
  onnx: null
  hf_cache: null

authentication:
  enabled: false
  username: null
  password: null
"""
            with open(config_path, "w") as f:
                f.write(default_config)
            print(f"Created default config file at {config_path}")
        
        # Load the default model
        interrogator_instance = load_default_model()
        print("Application startup complete.")
        yield
    finally:
        # Shutdown logic (if needed)
        print("Application shutdown complete.")

app = FastAPI(title="WD14 Tagger API", version="1.0.0", lifespan=lifespan)

def load_default_model():
    """Load the default model"""
    utils.refresh_interrogators()
    
    # Try to get default model from environment or configuration
    default_model = os.environ.get('DEFAULT_MODEL')
    
    # If no default model specified, use the first available
    if not default_model or default_model not in utils.interrogators:
        available_models = list(utils.interrogators.keys())
        if available_models:
            default_model = available_models[0]
        else:
            raise RuntimeError("No models available")
    
    # Load the model
    interrogator_instance = utils.interrogators[default_model]
    if interrogator_instance.model is None:
        interrogator_instance.load()
        
    print(f"Successfully loaded model: {default_model}")
    return interrogator_instance

def get_tag_categories():
    """Get tag categories from the loaded model"""
    if hasattr(interrogator_instance, 'tags') and interrogator_instance.tags is not None:
        tags_df = interrogator_instance.tags
    else:
        return {}
        
    # Create a mapping from tag name to category if tags data is available
    tag_categories = {}
    if 'name' in tags_df.columns and 'category' in tags_df.columns:
        for _, row in tags_df.iterrows():
            tag_categories[row['name']] = row['category']
            
    return tag_categories

def apply_tag_filters(tags: Dict[str, float]) -> Dict[str, float]:
    """Apply tag filtering based on configuration settings"""
    # Default values
    max_tags_per_category = 1000
    min_tag_score = 0.05
    
    # Apply minimum score filter
    filtered_tags = {k: v for k, v in tags.items() if v >= min_tag_score}
    
    # Apply maximum tags per category filter
    if len(filtered_tags) > max_tags_per_category:
        # Sort by score descending and take top N
        sorted_tags = sorted(filtered_tags.items(), key=lambda x: x[1], reverse=True)
        filtered_tags = dict(sorted_tags[:max_tags_per_category])
        
    return filtered_tags

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint returning frontend HTML"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>WD14 Tagger</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .upload-area {
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 30px;
            text-align: center;
            margin: 20px 0;
            cursor: pointer;
            transition: border-color 0.3s;
        }
        .upload-area:hover {
            border-color: #999;
        }
        .upload-area.dragover {
            border-color: #4CAF50;
            background-color: #f8fff8;
        }
        #imagePreview {
            max-width: 100%;
            max-height: 300px;
            margin: 10px auto;
            display: none;
        }
        .form-group {
            margin: 20px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="range"] {
            width: 100%;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
            margin: 10px 0;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        #result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }
        .success {
            background-color: #dff0d8;
            border: 1px solid #d6e9c6;
            color: #3c763d;
        }
        .error {
            background-color: #f2dede;
            border: 1px solid #ebccd1;
            color: #a94442;
        }
        .category-container {
            margin: 20px 0;
        }
        .category-title {
            font-weight: bold;
            font-size: 1.2em;
            margin: 10px 0 5px 0;
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }
        .tags-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .tag {
            background-color: #e1f5fe;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        .tag.character {
            background-color: #fce4ec;
        }
        .tag.rating {
            background-color: #fff3e0;
        }
        .confidence {
            font-weight: bold;
            margin-left: 5px;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WD14 Tagger</h1>
        <p>Upload an image to get AI-generated tags</p>
        
        <div class="upload-area" id="uploadArea">
            <p>Drag & drop an image here or click to select</p>
            <p><small>Supported formats: JPG, PNG, WEBP</small></p>
            <input type="file" id="imageInput" accept="image/*" class="hidden">
        </div>
        <img id="imagePreview" alt="Image preview">
        
        <div class="form-group">
            <label for="threshold">Threshold (0.0 - 1.0):</label>
            <input type="number" id="threshold" min="0" max="1" step="0.01" value="0.5">
        </div>
        
        <button id="interrogateBtn" disabled>Interrogate Image</button>
        
        <div id="result"></div>
        
        <div id="tagsContainer" class="hidden">
            <div class="category-container">
                <div class="category-title">Ratings</div>
                <div id="ratingsTags" class="tags-container"></div>
            </div>
            
            <div class="category-container">
                <div class="category-title">Characters</div>
                <div id="charactersTags" class="tags-container"></div>
            </div>
            
            <div class="category-container">
                <div class="category-title">General Tags</div>
                <div id="generalTags" class="tags-container"></div>
            </div>
        </div>
    </div>

    <script>
        // DOM elements
        const uploadArea = document.getElementById('uploadArea');
        const imageInput = document.getElementById('imageInput');
        const imagePreview = document.getElementById('imagePreview');
        const thresholdInput = document.getElementById('threshold');
        const interrogateBtn = document.getElementById('interrogateBtn');
        const resultDiv = document.getElementById('result');
        const tagsContainer = document.getElementById('tagsContainer');
        const ratingsTags = document.getElementById('ratingsTags');
        const charactersTags = document.getElementById('charactersTags');
        const generalTags = document.getElementById('generalTags');
        
        // State
        let selectedFile = null;
        
        // Event listeners
        uploadArea.addEventListener('click', () => imageInput.click());
        imageInput.addEventListener('change', handleImageSelect);
        interrogateBtn.addEventListener('click', interrogateImage);
        
        // Handle drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            if (e.dataTransfer.files.length) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });
        
        // Functions
        function handleImageSelect(e) {
            if (e.target.files.length) {
                handleFileSelection(e.target.files[0]);
            }
        }
        
        function handleFileSelection(file) {
            if (!file.type.match('image.*')) {
                showError('Please select an image file (JPG, PNG, WEBP)');
                return;
            }
            
            selectedFile = file;
            interrogateBtn.disabled = false;
            
            // Show image preview
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.src = e.target.result;
                imagePreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
            
            // Clear previous results
            resultDiv.style.display = 'none';
            tagsContainer.classList.add('hidden');
        }
        
        async function interrogateImage() {
            if (!selectedFile) {
                showError('Please select an image first');
                return;
            }
            
            const threshold = parseFloat(thresholdInput.value);
            if (isNaN(threshold) || threshold < 0 || threshold > 1) {
                showError('Please enter a valid threshold between 0 and 1');
                return;
            }
            
            // Disable button and show loading state
            interrogateBtn.disabled = true;
            interrogateBtn.textContent = 'Processing...';
            resultDiv.style.display = 'none';
            tagsContainer.classList.add('hidden');
            
            try {
                // Prepare form data
                const formData = new FormData();
                formData.append('image', selectedFile);
                formData.append('threshold', threshold);
                
                // Send request
                const response = await fetch('/interrogate', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Show success message
                showSuccess('Image processed successfully!');
                
                // Display tags
                displayTags(data);
            } catch (error) {
                console.error('Error:', error);
                showError('Failed to process image: ' + error.message);
            } finally {
                // Restore button
                interrogateBtn.disabled = false;
                interrogateBtn.textContent = 'Interrogate Image';
            }
        }
        
        function displayTags(data) {
            // Clear previous tags
            ratingsTags.innerHTML = '';
            charactersTags.innerHTML = '';
            generalTags.innerHTML = '';
            
            // Display ratings
            Object.entries(data.ratings).forEach(([tag, confidence]) => {
                const tagElement = createTagElement(tag, confidence, 'rating');
                ratingsTags.appendChild(tagElement);
            });
            
            // Display characters
            Object.entries(data.characters).forEach(([tag, confidence]) => {
                const tagElement = createTagElement(tag, confidence, 'character');
                charactersTags.appendChild(tagElement);
            });
            
            // Display general tags
            Object.entries(data.tags).forEach(([tag, confidence]) => {
                const tagElement = createTagElement(tag, confidence, 'general');
                generalTags.appendChild(tagElement);
            });
            
            // Show tags container
            tagsContainer.classList.remove('hidden');
        }
        
        function createTagElement(name, confidence, category) {
            const tagElement = document.createElement('div');
            tagElement.className = `tag ${category}`;
            
            const confidenceElement = document.createElement('span');
            confidenceElement.className = 'confidence';
            confidenceElement.textContent = confidence.toFixed(2);
            
            tagElement.textContent = name + ' ';
            tagElement.appendChild(confidenceElement);
            
            return tagElement;
        }
        
        function showSuccess(message) {
            resultDiv.className = 'success';
            resultDiv.innerHTML = message;
            resultDiv.style.display = 'block';
        }
        
        function showError(message) {
            resultDiv.className = 'error';
            resultDiv.innerHTML = message;
            resultDiv.style.display = 'block';
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/interrogate", response_model=InterrogateResponse)
async def interrogate(
    image: UploadFile = File(...),
    threshold: float = Form(0.0)
):
    """Interrogate an image and return categorized tags"""
    global interrogator_instance
    
    if interrogator_instance is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    # Read image file
    try:
        image_content = await image.read()
        pil_image = Image.open(BytesIO(image_content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    # Perform interrogation
    with queue_lock:
        ratings, tags = interrogator_instance.interrogate(pil_image)

    # Get tag categories
    tag_categories = get_tag_categories()
    
    # Apply tag filters
    filtered_tags = apply_tag_filters(tags)
    
    # Apply threshold filter but always include ratings
    threshold_filtered_tags = {k: v for k, v in filtered_tags.items() if v >= threshold}

    # Categorize tags
    characters = {}
    general_tags = {}
    
    for tag, confidence in threshold_filtered_tags.items():
        category = tag_categories.get(tag, -1)  # Default to -1 if not found
        
        # Categorize based on category number directly
        if category == 4:
            characters[tag] = confidence
        elif category == 0:
            general_tags[tag] = confidence
        # Ratings are handled separately and already in the 'ratings' dict

    return InterrogateResponse(
        ratings=ratings,
        characters=characters,
        tags=general_tags
    )

def main():
    # Try to load configuration
    config = {}
    try:
        import yaml
        config_path = "config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")

    # Get server configuration with defaults
    server_config = config.get('server', {})
    default_host = server_config.get('host', '127.0.0.1')
    default_port = server_config.get('port', 8080)
    default_reload = server_config.get('reload', False)

    parser = argparse.ArgumentParser(description="WD14 Tagger Simple API")
    parser.add_argument("--host", type=str, default=default_host, help="Host to run the API on")
    parser.add_argument("--port", type=int, default=default_port, help="Port to run the API on")
    parser.add_argument("--reload", action="store_true", default=default_reload, help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"Starting WD14 Tagger Simple API on http://{args.host}:{args.port}")
    print("Available endpoints:")
    print("  GET  / - Frontend interface")
    print("  POST /interrogate - Interrogate an image")
    
    uvicorn.run(
        "simple_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()