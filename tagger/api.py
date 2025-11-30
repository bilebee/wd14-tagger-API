"""API module for FastAPI"""
from typing import Callable, Dict, Optional, List
from threading import Lock
from secrets import compare_digest
import asyncio
from collections import defaultdict
from hashlib import sha256
import string
from random import choices
import os

# Standalone mode without Stable Diffusion
shared = None
queue_lock = Lock()
HAS_SD = False

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tagger import utils  # pylint: disable=import-error
from tagger import api_models as models  # pylint: disable=import-error

# For standalone operation
try:
    import base64
    from io import BytesIO
    from PIL import Image
except ImportError:
    pass

def decode_base64_to_image(encoding):
    """Standalone version of decode_base64_to_image"""
    if encoding is None:
        raise HTTPException(status_code=400, detail="Image data is None")
        
    if not encoding:
        raise HTTPException(status_code=400, detail="Empty image data")
        
    # Handle data URL format: data:image/jpeg;base64,/9j/...
    if isinstance(encoding, str) and encoding.startswith("data:image/"):
        try:
            encoding = encoding.split(";")[1].split(",")[1]
        except IndexError:
            raise HTTPException(status_code=400, detail="Invalid data URL format")
    
    try:
        image = Image.open(BytesIO(base64.b64decode(encoding, validate=True)))
        return image
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid encoded image: {str(e)}") from e


class Api:
    """Api class for FastAPI"""
    def __init__(
        self, app: FastAPI, qlock: Lock, prefix: Optional[str] = None
    ) -> None:
        self.app = app
        self.queue_lock = qlock if qlock else Lock()
        
        # Initialize credentials dictionary
        self.credentials = {}
        
        # In standalone mode, check for environment variables
        api_auth = os.environ.get("API_AUTH", "")
        if api_auth and len(api_auth) > 0:
            for auth in api_auth.split(","):
                if ":" in auth:
                    user, password = auth.split(":", 1)
                    self.credentials[user] = password

        # Add routes
        self._add_routes(prefix or "")


    def _add_routes(self, prefix: str):
        """Add API routes with prefix"""
        # Add index endpoint
        if self.credentials and len(self.credentials) > 0:
            self.app.add_api_route(
                f"{prefix}/",
                self.endpoint_index,
                methods=["GET"],
                dependencies=[Depends(self._get_auth())]
            )
        else:
            self.app.add_api_route(
                f"{prefix}/",
                self.endpoint_index,
                methods=["GET"]
            )
            
        # Add interrogate endpoint
        if self.credentials and len(self.credentials) > 0:
            self.app.add_api_route(
                f"{prefix}/interrogate",
                self.endpoint_interrogate,
                methods=["POST"],
                response_model=models.TaggerInterrogateSingleResponse,
                dependencies=[Depends(self._get_auth())]
            )
        else:
            self.app.add_api_route(
                f"{prefix}/interrogate",
                self.endpoint_interrogate,
                methods=["POST"],
                response_model=models.TaggerInterrogateSingleResponse
            )

        # Add interrogate-categorized endpoint
        if self.credentials and len(self.credentials) > 0:
            self.app.add_api_route(
                f"{prefix}/interrogate-categorized",
                self.endpoint_interrogate_categorized,
                methods=["POST"],
                response_model=models.TaggerInterrogateCategorizedResponse,
                dependencies=[Depends(self._get_auth())]
            )
        else:
            self.app.add_api_route(
                f"{prefix}/interrogate-categorized",
                self.endpoint_interrogate_categorized,
                methods=["POST"],
                response_model=models.TaggerInterrogateCategorizedResponse
            )

    def _get_auth(self):
        """Get authentication dependency"""
        security = HTTPBasic()
        
        def auth(credentials: HTTPBasicCredentials = Depends(security)):
            if credentials.username in self.credentials and compare_digest(
                credentials.password, self.credentials[credentials.username]
            ):
                return True

            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        return auth

    def _get_default_interrogator(self):
        """Get the default interrogator based on configuration or first available"""
        # Try to get default model from environment or configuration
        try:
            from tagger.config import ConfigManager
            config_manager = ConfigManager()
            default_model = config_manager.get('model.default')
        except ImportError:
            default_model = os.environ.get('DEFAULT_MODEL')
        
        # If no default model specified, use the first available
        if not default_model or default_model not in utils.interrogators:
            available_models = list(utils.interrogators.keys())
            if available_models:
                default_model = available_models[0]
            else:
                raise HTTPException(status_code=503, detail="No models available")
        
        return utils.interrogators[default_model], default_model

    def _apply_tag_filters(self, tags: Dict[str, float]) -> Dict[str, float]:
        """Apply tag filtering based on configuration settings"""
        try:
            from tagger.config import ConfigManager
            config_manager = ConfigManager()
        except ImportError:
            # Default values if config not available
            max_tags_per_category = 1000
            min_tag_score = 0.05
            config_manager = None
            
        if config_manager:
            max_tags_per_category = config_manager.get('tagging.max_tags_per_category', 1000)
            min_tag_score = config_manager.get('tagging.min_tag_score', 0.05)
        
        # Apply minimum score filter
        filtered_tags = {k: v for k, v in tags.items() if v >= min_tag_score}
        
        # Apply maximum tags per category filter
        if len(filtered_tags) > max_tags_per_category:
            # Sort by score descending and take top N
            sorted_tags = sorted(filtered_tags.items(), key=lambda x: x[1], reverse=True)
            filtered_tags = dict(sorted_tags[:max_tags_per_category])
            
        return filtered_tags

    def endpoint_index(self):
        """Index endpoint returning API documentation"""
        import os
        html_file = os.path.join(os.path.dirname(__file__), '..', 'static', 'index.html')
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Return basic API information when HTML documentation is not available
            return {
                "message": "WD14 Tagger API",
                "endpoints": {
                    "GET /": "This API documentation",
                    "POST /interrogate": "Interrogate an image",
                    "POST /interrogate-categorized": "Interrogate an image with categorized tags"
                },
                "note": "Use POST requests to the /interrogate endpoint to analyze images"
            }

    def endpoint_interrogate(self, 
                           image: UploadFile = File(...),
                           threshold: float = Form(0.0)):
        """Interrogate an image and return tags with categories"""
        # Read image file
        try:
            image_content = image.file.read()
            pil_image = Image.open(BytesIO(image_content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}") from e

        # Get default interrogator
        interrogator, _ = self._get_default_interrogator()
        
        # Ensure model is loaded to access tags data
        with self.queue_lock:
            if interrogator.model is None:
                interrogator.load()
            
            # Perform interrogation
            ratings, tags = interrogator.interrogate(pil_image)

        # Get tag categories using the helper method
        tag_categories = self._get_tag_categories(interrogator)

        # Apply tag filters
        filtered_tags = self._apply_tag_filters(tags)
        
        # Apply threshold filter but always include ratings
        threshold_filtered_tags = {k: v for k, v in filtered_tags.items() if v >= threshold}

        # Format tags with names and category numbers
        formatted_tags = {}
        for tag, confidence in threshold_filtered_tags.items():
            category = tag_categories.get(tag, -1)  # Default to -1 if not found
            formatted_tags[tag] = {
                "category": category,
                "confidence": confidence
            }

        return models.TaggerInterrogateSingleResponse(
            ratings=ratings,
            tags=formatted_tags
        )

    def _get_tag_categories(self, interrogator):
        """Helper method to get tag categories from an interrogator"""
        # Load tags database for the model to get category information
        if hasattr(interrogator, 'tags') and interrogator.tags is not None:
            tags_df = interrogator.tags
        else:
            # Return empty dict if tags are not available
            return {}
            
        # Create a mapping from tag name to category if tags data is available
        tag_categories = {}
        if 'name' in tags_df.columns and 'category' in tags_df.columns:
            for _, row in tags_df.iterrows():
                tag_categories[row['name']] = row['category']
                
        return tag_categories

    def endpoint_interrogate_batch(self, req: models.TaggerInterrogateBatchRequest):
        """ batch interrogation of multiple images with categorized results """
        if not req.images:
            raise HTTPException(400, 'No images provided')

        # Use default model instead of requiring model parameter
        interrogator, _ = self._get_default_interrogator()
        tag_categories = self._get_tag_categories(interrogator)
        
        results: List[Dict[str, Dict[str, float]]] = []

        # Process images
        with self.queue_lock:
            for img in req.images:
                try:
                    image = decode_base64_to_image(img)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid encoded image: {str(e)}") from e
                    
                ratings, tags = interrogator.interrogate(image)
                
                # Apply tag filters
                filtered_tags = self._apply_tag_filters(tags)
                
                # Apply threshold filter
                threshold_filtered_tags = {k: v for k, v in filtered_tags.items() if v > req.threshold}

                # Categorize tags
                characters = {}
                regular_tags = {}
                
                for tag, confidence in threshold_filtered_tags.items():
                    category = tag_categories.get(tag, -1)  # Default to -1 if not found
                    if category == 4:
                        characters[tag] = confidence
                    else:
                        regular_tags[tag] = confidence

                # Format result in categorized structure
                result = {
                    "ratings": ratings,
                    "characters": characters,
                    "tags": regular_tags
                }
                results.append(result)

        return models.TaggerInterrogateBatchResponse(captions=results)

    def endpoint_interrogate_categorized(self, req: models.TaggerInterrogateRequest):
        """ one file interrogation with categorized tags """
        if req.image is None:
            raise HTTPException(404, 'Image not found')

        # Use default model instead of requiring model parameter
        interrogator, _ = self._get_default_interrogator()
        tag_categories = self._get_tag_categories(interrogator)

        image = decode_base64_to_image(req.image)
        with self.queue_lock:
            ratings, tags = interrogator.interrogate(image)

        # Apply tag filters
        filtered_tags = self._apply_tag_filters(tags)
        
        # Apply threshold filter
        threshold_filtered_tags = {k: v for k, v in filtered_tags.items() if v > req.threshold}

        # Categorize tags
        characters = {}
        regular_tags = {}
        
        for tag, confidence in threshold_filtered_tags.items():
            category = tag_categories.get(tag, -1)  # Default to -1 if not found
            if category == 4:
                characters[tag] = confidence
            else:
                regular_tags[tag] = confidence

        return models.TaggerInterrogateCategorizedResponse(
            ratings=ratings,
            characters=characters,
            tags=regular_tags
        )

    # The endpoint_interrogate_single method has been removed as its functionality
    # has been merged into endpoint_interrogate

    def endpoint_interrogators(self):
        # Refresh interrogators in case new models were added
        utils.refresh_interrogators()
        return models.TaggerInterrogatorsResponse(
            models=list(utils.interrogators.keys())
        )

    def endpoint_unload_interrogators(self):
        # Note: In the new approach, we don't allow unloading models
        # as they are managed by the server configuration
        return "Model unloading is disabled in this configuration"