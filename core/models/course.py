from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class PriceInfo:
    price: float
    final_price: float
    currency: str
    symbol: str
    country_code: str


@dataclass
class CourseInfo:
    title: str
    brief: str
    duration: str
    instructor: str
    instructor_bio: str
    description: str
    requirements: str
    learning_objectives: List[str]
    units: List[Dict]
    reviews: List[Dict]
    preview: Optional[str] = None
    price: PriceInfo = None
