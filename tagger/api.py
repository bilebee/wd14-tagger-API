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

from fastapi import FastAPI, Depends, HTTPException
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
        self.credentials = {}
        # In standalone mode, check for environment variables
        api_auth = os.environ.get("API_AUTH", "")
        if api_auth:
            for auth in api_auth.split(","):
                user, password = auth.split(":")
                self.credentials[user] = password

        self.app = app
        self.queue: Dict[str, asyncio.Queue] = {}
        self.res: Dict[str, Dict[str, Dict[str, float]]] = \
            defaultdict(dict)
        self.queue_lock = qlock if qlock else Lock()
        self.tasks: Dict[str, asyncio.Task] = {}

        self.runner: Optional[asyncio.Task] = None
        self.prefix = prefix
        self.running_batches: Dict[str, Dict[str, float]] = \
            defaultdict(lambda: defaultdict(int))

        self.add_api_route(
            'interrogate',
            self.endpoint_interrogate,
            methods=['POST'],
            response_model=models.TaggerInterrogateResponse
        )

        self.add_api_route(
            'interrogate-batch',
            self.endpoint_interrogate_batch,
            methods=['POST'],
            response_model=models.TaggerInterrogateBatchResponse
        )

        self.add_api_route(
            'interrogate-categorized',
            self.endpoint_interrogate_categorized,
            methods=['POST'],
            response_model=models.TaggerInterrogateCategorizedResponse
        )

        self.add_api_route(
            'interrogators',
            self.endpoint_interrogators,
            methods=['GET'],
            response_model=models.TaggerInterrogatorsResponse
        )

        self.add_api_route(
            'unload-interrogators',
            self.endpoint_unload_interrogators,
            methods=['POST']
        )

    def add_api_route(
        self, path: str, endpoint: Callable, **kwargs
    ) -> None:
        """Add an API route with optional authentication."""
        if self.prefix:
            path = f"{self.prefix}/{path}"

        if self.credentials and HAS_SD and shared and shared.cmd_opts and shared.cmd_opts.api_auth:
            # With authentication
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

            self.app.add_api_route(path, endpoint, dependencies=[Depends(auth)], **kwargs)
        else:
            # Without authentication
            self.app.add_api_route(path, endpoint, **kwargs)

    def endpoint_interrogate(self, req: models.TaggerInterrogateRequest):
        """ one file interrogation, queueing, or batch results """
        if req.image is None:
            raise HTTPException(404, 'Image not found')

        if req.model not in utils.interrogators:
            raise HTTPException(404, 'Model not found')

        m, q, n = (req.model, req.queue, req.name_in_queue)
        res: Dict[str, Dict[str, float]] = {}

        if q != '' or n != '':
            if q == '':
                # generate a random queue name, not in use
                while True:
                    q = ''.join(choices(string.ascii_uppercase +
                                string.digits, k=8))
                    if q not in self.queue:
                        break
                print(f'WD14 tagger api generated queue name: {q}')
            res = asyncio.run(self.queue_interrogation(m, q, n, req.image,
                              req.threshold), debug=True)
        else:
            image = decode_base64_to_image(req.image)
            interrogator = utils.interrogators[m]
            res = {"tag": {}, "rating": {}}
            with self.queue_lock:
                res["rating"], tag = interrogator.interrogate(image)

            for k, v in tag.items():
                if v > req.threshold:
                    res["tag"][k] = v

        return models.TaggerInterrogateResponse(caption=res)

    def endpoint_interrogate_batch(self, req: models.TaggerInterrogateBatchRequest):
        """ batch interrogation of multiple images with categorized results """
        if not req.images:
            raise HTTPException(400, 'No images provided')

        if req.model not in utils.interrogators:
            raise HTTPException(404, 'Model not found')

        interrogator = utils.interrogators[req.model]
        
        # Load tags database for the model to get category information
        tags_df = None
        if hasattr(interrogator, 'tags') and interrogator.tags is not None:
            tags_df = interrogator.tags
        else:
            # Load the tags file if not already loaded
            if req.images:
                image = decode_base64_to_image(req.images[0])
                with self.queue_lock:
                    interrogator.load()
                    # We don't actually need to interrogate here, just load the model
                    # to access the tags data
                    _, _ = interrogator.interrogate(image)
                tags_df = interrogator.tags

        # Create a mapping from tag name to category if tags data is available
        tag_categories = {}
        if tags_df is not None and 'name' in tags_df.columns and 'category' in tags_df.columns:
            for _, row in tags_df.iterrows():
                tag_categories[row['name']] = row['category']

        images = [decode_base64_to_image(img) for img in req.images]
        results: List[Dict[str, Dict[str, float]]] = []

        # Process images
        with self.queue_lock:
            for img in req.images:
                try:
                    image = decode_base64_to_image(img)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid encoded image: {str(e)}") from e
                    
                ratings, tags = interrogator.interrogate(image)
                
                # Filter tags by threshold
                filtered_tags = {k: v for k, v in tags.items() if v > req.threshold}

                # Categorize tags
                characters = {}
                regular_tags = {}
                
                for tag, confidence in filtered_tags.items():
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

        if req.model not in utils.interrogators:
            raise HTTPException(404, 'Model not found')

        # Load tags database for the model to get category information
        interrogator = utils.interrogators[req.model]
        if hasattr(interrogator, 'tags') and interrogator.tags is not None:
            tags_df = interrogator.tags
        else:
            # Load the tags file if not already loaded
            image = decode_base64_to_image(req.image)
            with self.queue_lock:
                interrogator.load()
                # We don't actually need to interrogate here, just load the model
                # to access the tags data
                _, _ = interrogator.interrogate(image)
            tags_df = interrogator.tags

        # Create a mapping from tag name to category
        tag_categories = {}
        if 'name' in tags_df.columns and 'category' in tags_df.columns:
            for _, row in tags_df.iterrows():
                tag_categories[row['name']] = row['category']

        image = decode_base64_to_image(req.image)
        with self.queue_lock:
            ratings, tags = interrogator.interrogate(image)

        # Filter tags by threshold
        filtered_tags = {k: v for k, v in tags.items() if v > req.threshold}

        # Categorize tags
        characters = {}
        regular_tags = {}
        
        for tag, confidence in filtered_tags.items():
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

    def endpoint_interrogators(self):
        # Refresh interrogators in case new models were added
        utils.refresh_interrogators()
        return models.TaggerInterrogatorsResponse(
            models=list(utils.interrogators.keys())
        )

    def endpoint_unload_interrogators(self):
        unloaded_models = 0

        for i in utils.interrogators.values():
            if i.unload():
                unloaded_models = unloaded_models + 1

        return f"Successfully unload {unloaded_models} model(s)"