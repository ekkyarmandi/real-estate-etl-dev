from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    Integer,
    Date,
    DateTime,
    func,
)
from models.base import Base


class CheckerListing(Base):
    __tablename__ = "listing"

    id = Column(Integer, primary_key=True)
    reid_id = Column(String)
    source = Column(String)
    scraped_at = Column(Date)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    sold_at = Column(Date)
    url = Column(String, unique=True)
    title = Column(String)
    description = Column(String, default="")
    image_url = Column(String)
    property_id = Column(String)
    location = Column(String)
    contract_type = Column(String)
    leasehold_years = Column(Float)
    property_type = Column(String)
    listed_date = Column(String)
    price = Column(Float)
    currency = Column(String, default="IDR")
    bedrooms = Column(Float)
    bathrooms = Column(Float)
    build_size = Column(Float)
    land_size = Column(Integer)
    is_available = Column(Boolean, default=True)
    available_text = Column(String)
    is_off_plan = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    is_excluded = Column(Boolean, default=False)
    excluded_by = Column(String)
