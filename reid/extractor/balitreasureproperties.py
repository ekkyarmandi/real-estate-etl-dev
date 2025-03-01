from reid.database import get_db
from models.listing import Listing
from models.rawdata import RawData
from rich.progress import track
import re
import json

from reid.func import define_property_type


def extract_balitreasureproperties():
    db = next(get_db())
    listings = (
        db.query(Listing)
        .filter(
            Listing.reid_id.like("REID_25_02%"),
            Listing.property_type.is_(None),
            Listing.source == "Bali Treasure Properties",
        )
        .all()
    )
    for listing in track(listings, description="Extracting balitreasureproperties"):
        rawdata = db.query(RawData).filter(RawData.url == listing.url).first()
        if rawdata:
            data = json.loads(rawdata.json)
            property_text = data.get("listingType")
            property_type = define_property_type(property_text)
            if property_text:
                listing.property_type = property_type
                db.commit()


if __name__ == "__main__":
    extract_balitreasureproperties()
