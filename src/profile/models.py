from typing import Dict, List
from pydantic import BaseModel


class UserProfileOut(BaseModel):
    interests: List[str]
    knowledge_levels: Dict[str, str]
    last_updated: str
