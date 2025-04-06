from sqlalchemy import (
    Column,
    String,
    TIMESTAMP,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from models.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(TIMESTAMP, default=datetime.now())
    updated_at = Column(TIMESTAMP, default=datetime.now(), onupdate=datetime.now())
    name = Column(String, nullable=False)
    property_id = Column(
        String, ForeignKey("property.id", ondelete="CASCADE"), nullable=False
    )
    is_solved = Column(Boolean, default=False)
    is_ignored = Column(Boolean, default=False)

    property = relationship("Property", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("property_id", "name", name="_property_name_uc"),
    )

    def __repr__(self):
        return f"<Tag name='{self.name}' is_solved='{self.is_solved}' is_ignored='{self.is_ignored}'/>"
