"""Pydantic models for FastAPI responses"""
from typing import Dict, List, Optional
from pydantic import BaseModel


class TaggerInterrogateRequest(BaseModel):
    image: str
    threshold: float = 0.5
    queue: str = ''
    name_in_queue: str = ''


class TaggerInterrogateBatchRequest(BaseModel):
    images: List[str]
    threshold: float = 0.5


class TaggerInterrogateResponse(BaseModel):
    caption: Dict[str, Dict[str, float]]


class TaggerInterrogateBatchResponse(BaseModel):
    captions: List[Dict[str, Dict[str, float]]]


class TaggerInterrogateCategorizedResponse(BaseModel):
    ratings: Dict[str, float]
    characters: Dict[str, float]
    tags: Dict[str, float]


class TaggerInterrogateSingleResponse(BaseModel):
    ratings: Dict[str, float]
    tags: Dict[str, Dict[str, float]]  # tag name -> {category: int, confidence: float}
