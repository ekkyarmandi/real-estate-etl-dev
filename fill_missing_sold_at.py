from reid.database import get_db
from models.listing import Listing
from tqdm import tqdm
from rich.progress import track


def main():
    db = next(get_db())
    listings = (
        db.query(Listing)
        .filter(
            Listing.is_available == False,
            Listing.sold_at == None,
        )
        .all()
    )
    for listing in track(listings, description="Filling missing sold_at"):
        if not listing.sold_at:
            sold_at = listing.updated_at
            new_month = sold_at.month - 1
            if new_month == 0:
                new_month = 12
                sold_at = sold_at.replace(year=sold_at.year - 1)
            sold_at = sold_at.replace(month=new_month)
            sold_at = sold_at.strftime("%Y-%m-01")
            listing.sold_at = sold_at
            db.commit()


if __name__ == "__main__":
    main()
