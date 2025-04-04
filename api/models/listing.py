from sqlalchemy import (
    Column,
    String,
    Text,
    TIMESTAMP,
    Float,
    Boolean,
    BigInteger,
)
import uuid
from datetime import datetime
from sqlalchemy.orm import relationship
from models.base import Base


class CheckerListing(Base):
    __tablename__ = "listing"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id = Column(String, nullable=True)
    reid_id = Column(String, nullable=False)
    source = Column(String, nullable=False)
    scraped_at = Column(TIMESTAMP, default=datetime.now())
    created_at = Column(TIMESTAMP, default=datetime.now())
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    url = Column(Text, nullable=False, unique=True)
    image_url = Column(Text, nullable=False, default="")
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=False, default="")
    region = Column(String, nullable=True)
    location = Column(String, nullable=True)
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    leasehold_years = Column(Float, nullable=True)
    contract_type = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    listed_date = Column(String, nullable=True)
    bedrooms = Column(Float, nullable=True)
    bathrooms = Column(Float, nullable=True)
    build_size = Column(Float, nullable=True)
    land_size = Column(Float, nullable=True)
    land_zoning = Column(String, nullable=True)
    price = Column(BigInteger, nullable=False)
    currency = Column(String, nullable=False)
    is_available = Column(Boolean, default=True)
    availability = Column(String, default="Available")
    is_off_plan = Column(Boolean, default=False)
    sold_at = Column(TIMESTAMP, nullable=True)
    is_excluded = Column(Boolean, default=False)
    excluded_by = Column(String, nullable=True)
    tab = Column(String, default="DATA")
