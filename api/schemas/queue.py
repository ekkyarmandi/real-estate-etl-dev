from typing import List
from pydantic import BaseModel


class StatusUpdate(BaseModel):
    status: str


class QueueItemUpdate(BaseModel):
    id: int
    status: str


class BulkStatusUpdate(BaseModel):
    items: List[QueueItemUpdate]
