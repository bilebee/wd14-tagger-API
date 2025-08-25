"""API module for FastAPI"""
from typing import Callable, Dict, Optional
from threading import Lock
from secrets import compare_digest
import asyncio
from collections import defaultdict
from hashlib import sha256
import string
from random import choices
import os

try:
    from modules import shared  # pylint: disable=import-error
    from modules.api.api import decode_base64_to_image  # pylint: disable=E0401
    from modules.call_queue import queue_lock  # pylint: disable=import-error
    HAS_SD = True
except ImportError:
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
    if encoding.startswith("data:image/"):
        encoding = encoding.split(";")[1].split(",")[1]
    try:
        image = Image.open(BytesIO(base64.b64decode(encoding)))
        return image
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid encoded image") from e


class Api:
    """Api class for FastAPI"""
    def __init__(
        self, app: FastAPI, qlock: Lock, prefix: Optional[str] = None
    ) -> None:
        self.credentials = {}
        if HAS_SD and shared and shared.cmd_opts and shared.cmd_opts.api_auth:
            for auth in shared.cmd_opts.api_auth.split(","):
                user, password = auth.split(":")
                self.credentials[user] = password
        elif not HAS_SD:
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
        elif self.credentials and not HAS_SD:
            # With authentication in standalone mode
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

    async def add_to_queue(self, m, q, n='', i=None, t=0.0) -> Dict[
        str, Dict[str, float]
    ]:
        """ add an interrogation to the queue """
        if q not in self.queue:
            self.queue[q] = asyncio.Queue()
            self.res[q].clear()
            self.tasks[q] = asyncio.create_task(self.run_batch(q))

        if n == '':
            await self.queue[q].put((m, i, t))
        else:
            await self.queue[q].put((m, i, t, n))

    async def run_batch(self, q) -> None:
        """ run a batch of interrogations """
        # wait for the first image to be added to the queue
        m, i, t, *n = await self.queue[q].get()
        n = n[0] if n else ''

        # collect all queued images
        batch = [(m, i, t, n)]
        while not self.queue[q].empty():
            m, i, t, *n = await self.queue[q].get()
            n = n[0] if n else ''
            batch.append((m, i, t, n))

        # run the interrogator against the batch
        interrogator = utils.interrogators[batch[0][0]]
        with self.queue_lock:
            # batch process
            if hasattr(interrogator, 'large_batch_interrogate'):
                # large batch handling
                images = []
                names = []
                for _, i, _, n in batch:
                    images.append(decode_base64_to_image(i))
                    names.append(n)
                res = interrogator.large_batch_interrogate(images)
                for i, r in enumerate(res.splitlines()):
                    self.res[q][names[i]] = {"tag": {}, "rating": {}}
                    # TODO: parse result properly
            else:
                # regular batch handling
                for m, i, t, n in batch:
                    image = decode_base64_to_image(i)
                    res = {"tag": {}, "rating": {}}
                    res["rating"], tags = interrogator.interrogate(image)
                    for k, v in tags.items():
                        if v > t:
                            res["tag"][k] = v
                    self.res[q][n] = res

        # signal that the batch is complete
        self.running_batches[q] = {}

    async def queue_interrogation(self, m, q, n='', i=None, t=0.0) -> Dict[
        str, Dict[str, float]
    ]:
        """ queue an interrogation, or add to batch """
        if n == '':
            task = asyncio.create_task(self.add_to_queue(m, q))
        else:
            if n == '<sha256>':
                n = sha256(i).hexdigest()
                if n in self.res[q]:
                    return self.running_batches
            elif n in self.res[q]:
                # clobber name if it's already in the queue
                j = 0
                while f'{n}#{j}' in self.res[q]:
                    j += 1
                n = f'{n}#{j}'
            self.res[q][n] = {}
            # add image to queue
            task = asyncio.create_task(self.add_to_queue(m, q, n, i, t))
        return await task


def on_app_started(_, app: FastAPI):
    Api(app, queue_lock, '/tagger/v1')