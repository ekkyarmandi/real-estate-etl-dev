from sqlalchemy import Column, String, Text, TIMESTAMP
import uuid
from datetime import datetime
from models.base import Base


class RawData(Base):
    __tablename__ = "raw_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now(datetime.UTC))
    html = Column(Text, nullable=True)
    json = Column(Text, nullable=True)
