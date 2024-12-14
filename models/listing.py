from sqlalchemy import Column, String, Text, TIMESTAMP, Float, Boolean, BigInteger, text
import uuid
from datetime import datetime
from models.base import Base
from reid.settings import REID_CODE


class Listing(Base):
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

    def reid_id_generator(self, db):
        code = REID_CODE[self.source]
        yr_mo = datetime.now().strftime(f"REID_%y_%m_{code}")
        q = text(
            "SELECT reid_id FROM listing WHERE reid_id LIKE :yr_mo ORDER BY reid_id DESC LIMIT 1;"
        )
        last_reid_id = db.execute(q, {"yr_mo": yr_mo + "%"}).fetchone()
        if last_reid_id:
            index = int(last_reid_id[0].split("_")[-1]) + 1
        else:
            index = 1
        reid_id = f"{yr_mo}_{index:03d}"
        # check url existing
        q = text(f"SELECT url FROM listing WHERE url='{self.url}';")
        existing_url = db.execute(q).fetchone()
        if not existing_url:
            self.reid_id = reid_id

    def classify_tab(self):
        if self.price >= 78656000000 and self.currency == "IDR":
            self.tab = "LUXURY LISTINGS"
        elif self.price >= 5000000 and self.currency == "USD":
            self.tab = "LUXURY LISTINGS"

    def compare(self, new_data):
        changes = 0
        fields_to_compare = [
            "price",
            "currency",
            "availability",
            "is_available",
            "is_off_plan",
            "image_url",
            "description",
            "location",
            "leasehold_years",
            "contract_type",
            "property_type",
            "bedrooms",
            "bathrooms",
            "build_size",
            "land_size",
            "land_zoning",
            "property_id",
            "listed_date",
        ]
        for attr in fields_to_compare:
            old_value = getattr(self, attr)
            new_value = new_data.get(attr)
            if attr == "availability":
                if new_value != "Available":
                    self.is_available = False
                    self.sold_at = datetime.now().replace(
                        day=1,
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                    changes += 1
                    continue
            # replace the value if the new value is different
            elif attr in ["leasehold_years"]:
                if new_value != old_value:
                    setattr(self, attr, new_value)
                    changes += 1
                    continue
            # fill the missing value
            if new_value and not old_value:
                setattr(self, attr, new_value)
                changes += 1
            # override the value if the new value is different and not empty
            elif new_value and old_value and new_value != old_value:
                setattr(self, attr, new_value)
                changes += 1
        return changes > 0
