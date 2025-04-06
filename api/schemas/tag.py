from typing import List
from pydantic import BaseModel


class TagResponse(BaseModel):
    id: str
    name: str
    is_solved: bool
    is_ignored: bool

    class Config:
        from_attributes = True


class TagCount(BaseModel):
    id: str
    name: str
    count: int


class TagList(BaseModel):
    tags: List[TagCount]

    class Config:
        from_attributes = True


class BulkMarkAsSolvedOrIgnored(BaseModel):
    property_ids: List[str]
    mode: str = "solved"

    class Config:
        from_attributes = True
