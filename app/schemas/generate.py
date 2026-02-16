from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any

class GenerateRequest(BaseModel):
    url: HttpUrl   #this helps with url validation
    dimension: List[str]
    setup_scripts: Optional[str | List[str]] = None

class GenerateResponse(BaseModel):
    url: HttpUrl
    report: Dict[str, Any]


