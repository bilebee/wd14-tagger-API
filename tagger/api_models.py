"""Purpose: Pydantic models for the API."""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class TaggerInterrogateRequest(BaseModel):
    """Interrogate request model"""
    image: str = Field(
        title='Image',
        description='Base64 encoded image.',
        default=None
    )
    model: str = Field(
        title='Model',
        description='The interrogate model used.',
    )
    threshold: float = Field(
        title='Threshold',
        description='The threshold used for the interrogate model.',
        default=0.0,
    )
    queue: str = Field(
        title='Queue',
        description='name of queue; leave empty for single response',
        default='',
    )
    name_in_queue: str = Field(
        title='Name',
        description='name to queue image as or use <sha256>. leave empty to '
                    'retrieve the final response',
        default='',
    )


class TaggerInterrogateResponse(BaseModel):
    """Interrogate response model"""
    caption: Dict[str, Dict[str, float]] = Field(
        title='Caption',
        description='The generated captions for the image.'
    )


class TaggerInterrogateCategorizedResponse(BaseModel):
    """Interrogate response model with categorized tags"""
    ratings: Dict[str, float] = Field(
        title='Ratings',
        description='Rating tags (general, sensitive, questionable, explicit)'
    )
    characters: Dict[str, float] = Field(
        title='Characters',
        description='Character tags (category 4)'
    )
    tags: Dict[str, float] = Field(
        title='Tags',
        description='Regular tags (all other categories)'
    )


class TaggerInterrogatorsResponse(BaseModel):
    """Interrogators response model"""
    models: List[str] = Field(
        title='Models',
        description=''
    )