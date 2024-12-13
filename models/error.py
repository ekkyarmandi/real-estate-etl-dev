from sqlalchemy import Column, String, TIMESTAMP, Text, ForeignKey
import uuid
from datetime import datetime
from models.base import Base


class Error(Base):
    __tablename__ = "error"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(Text, nullable=False)
    error_message = Column(Text, nullable=False)
