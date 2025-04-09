"""
File upload and download routes
1. sold listings = True
2. sold listings = False
3. geolocation = True
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import json
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from fastapi.params import Depends
from sqlalchemy import text
from typing import Optional
from datetime import datetime as dt
from bs4 import BeautifulSoup
import tempfile
import re
import os

from database import get_checker_db, get_db
from func import get_domain
from models import Queue, Listing
from schemas.report import QueueStatsResponse

router = APIRouter(prefix="/data", tags=["data"])

BLACKLIST_DOMAINS = [
    "mirahdevelopments.com",
    "balicoconutliving.com",
    "bodyfactoryproperty.com",
    "propertia.com",
    "century21.co.id",
    "balirealty.com",
    "bali-home-immo.com",
    "addressbali.com",
    "antagroup.info",
    "cangguproperti.com",
    "geonet.properties",
    "parqdevelopment.com",
]


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(db: Session = Depends(get_checker_db)):
    """
    Returns statistics about the items in the queue:
    - Total listings
    - Available listings
    - Errors
    - Delisted
    - Sold
    """

    try:
        # More efficient query using direct aggregation with GROUP BY
        # Avoids multiple COUNT queries
        query = text(
            """
            SELECT 
                status, 
                COUNT(*) as count
            FROM 
                queue
            GROUP BY 
                status
        """
        )

        status_counts = db.execute(query).fetchall()
        stats_dict = {item[0]: item[1] for item in status_counts}

        total = sum(stats_dict.values())

        stats = {
            "total": total,
            "available": stats_dict.get("Available", 0),
            "errors": stats_dict.get("Error", 0),
            "delisted": stats_dict.get("Delisted", 0),
            "sold": stats_dict.get("Sold", 0),
        }

        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch queue statistics: {str(e)}"
        )


@router.post("/upload")
async def upload_file(
    file: Optional[UploadFile] = File(None),
    link_field: Optional[str] = Form(default="Property Link"),
    db: Session = Depends(get_checker_db),
):
    """
    Receives data from the frontend and processes URLs for the queue.
    """
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )

    try:
        # Parse file content
        content = await file.read()
        data = json.loads(content)

        # Filter the valid URLs in a single pass
        valid_urls = []
        for item in data:
            # Check if URL is available and valid
            if (
                item.get("Availability") == "Available"
                and link_field in item
                and item[link_field]
                and isinstance(item[link_field], str)
                and item[link_field].startswith("http")
            ):

                url = item[link_field]
                domain = get_domain(url)

                # Skip blacklisted domains
                if domain and domain not in BLACKLIST_DOMAINS:
                    valid_urls.append(url)

        # Remove duplicates
        valid_urls = list(set(valid_urls))

        if not valid_urls:
            return {"status": "success", "data": {"urls": [], "count": 0}}

        # Query existing URLs efficiently to filter them out
        # Use batching for large number of URLs
        batch_size = 1000  # Adjust based on DB capabilities
        existing_urls = set()

        for i in range(0, len(valid_urls), batch_size):
            batch = valid_urls[i : i + batch_size]
            existing_batch = db.query(Queue.url).filter(Queue.url.in_(batch)).all()
            existing_urls.update([item[0] for item in existing_batch])

        # Filter out existing URLs
        new_urls = [url for url in valid_urls if url not in existing_urls]

        if not new_urls:
            return {"status": "success", "data": {"urls": [], "count": 0}}

        # Insert new URLs in larger batches
        insert_batch_size = 100  # Increased from 10 to 100
        inserted_count = 0

        for i in range(0, len(new_urls), insert_batch_size):
            batch_urls = new_urls[i : i + insert_batch_size]

            # Create queue objects for the batch
            queue_objects = [
                Queue(url=url, listing_id=None, status="Available")
                for url in batch_urls
            ]

            try:
                # Bulk insert
                db.bulk_save_objects(queue_objects)
                db.commit()
                inserted_count += len(batch_urls)
            except Exception as err:
                db.rollback()
                print(f"Error inserting batch {i//insert_batch_size}: {err}")

        return {
            "status": "success",
            "data": {
                "urls": new_urls,
                "count": inserted_count,
                "total_valid": len(valid_urls),
                "already_existed": len(valid_urls) - len(new_urls),
            },
        }
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid JSON data in the uploaded file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing upload: {str(e)}"
        )


@router.post("/export")
async def export_file(
    file: Optional[UploadFile] = File(None),
    link_field: Optional[str] = Form(default="Property Link"),
    include_geolocation: Optional[bool] = Form(default=False),
    only_sold_listings: Optional[bool] = Form(default=True),
    file_version: Optional[str] = Form(default="_v1"),
    db: Session = Depends(get_db),
):
    """
    :param file: The JSON file to upload
    :param link_field: The field name for the Listing URL
    """
    # Check if file is provided
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )
    elif not link_field:
        raise HTTPException(
            status_code=400,
            detail="No link field provided. Please provide a link field.",
        )
    elif not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a JSON file."
        )

    # Parse file content
    content = await file.read()
    data = json.loads(content)

    default_file_name = file.filename.split(".")[0]
    filename = f"{default_file_name}{file_version}.json"

    # Count new listing
    today = dt.now()
    today = today.replace(month=today.month - 1)
    current_reid_id = today.strftime("REID_%y_%m%")
    listings = db.query(Listing).filter(
        (Listing.reid_id.like(current_reid_id)) & Listing.is_available
    )
    # total_new_listings = listings.count()
    listings = listings.all()

    # Query existing listings
    urls = [item[link_field] for item in data]
    urls = [url for url in urls if url]
    urls = [url for url in urls if url.startswith("http")]
    urls = list(set(urls))
    urls.sort()
    existing_listings = db.query(Listing).filter(Listing.url.in_(urls)).all()
    existing_listings = [listing.to_dict() for listing in existing_listings]
    existing_listings = {listing[link_field]: listing for listing in existing_listings}
    # Compare changes between data in the existing listings and the new listings
    columns = [
        "Region",
        "Years",
        "Location",
        "Description",
        "Image",
        "Source A",
        "Title",
        "Bedrooms",
        "Bathrooms",
        "Build Size (SQM)",
        "Land Size (SQM)",
        "Property Type",
        "Contract Type",
        "Availability",
    ]
    replace_columns = [
        "Image",
        "Bedrooms",
        "Bathrooms",
        "Build Size (SQM)",
        "Land Size (SQM)",
        "Contract Type",
        "Years",
        "Availability",
    ]
    comparison = {}
    changes = {}
    count = 0
    for l in data:
        url = l[link_field]
        if url in existing_listings:
            r = existing_listings[url]
            is_change = False
            old_listing = {
                "title": l.get("Title"),
                "url": l.get(link_field),
                "source": l.get("Source A"),
            }
            new_listing = {
                "title": r.get("Title"),
                "url": r.get(link_field),
                "source": r.get("Source A"),
            }
            same_listing = all(
                [
                    old_listing.get(key) == new_listing.get(key)
                    for key in old_listing.keys()
                ]
            )
            if url not in comparison:
                comparison[url] = {}
            for key in columns:
                v1 = l.get(key)
                v2 = r.get(key)
                if key in ["Build Size (SQM)", "Land Size (SQM)"] and v2:
                    # skip new value if it is float
                    t = str(v2)
                    x = t.split(".")[-1]
                    if int(x) == 0:
                        t = t.split(".")[0]
                    else:
                        continue
                    # skip if new value is end with 2
                    if not re.search(r"2$", t):
                        v2 = float(t)
                    else:
                        continue
                # skip if listing availability is not sold
                if only_sold_listings and key == "Availability" and v2 != "Sold":
                    continue
                # fix title
                if v2 and re.search(r"^<", str(v2)) and key == "Title":
                    soup = BeautifulSoup(v2, "html.parser")
                    v2 = soup.get_text()
                elif v2 and key == "Title":
                    v2 = re.sub(r"\n", "", v2)
                # compare changes
                if not v1 and v2 and key not in changes:
                    changes.update({key: 1})
                    comparison[url].update({key: {"before": v1, "after": v2}})
                    is_change = True
                elif not v1 and v2:
                    changes[key] += 1
                    comparison[url].update({key: {"before": v1, "after": v2}})
                    is_change = True
                elif (
                    v2
                    and v1 != v2
                    and key not in changes
                    and key in replace_columns
                    and same_listing
                ):
                    changes.update({key: 1})
                    comparison[url].update({key: {"before": v1, "after": v2}})
                    is_change = True
                elif v2 and v1 != v2 and key in replace_columns and same_listing:
                    changes[key] += 1
                    comparison[url].update({key: {"before": v1, "after": v2}})
                    is_change = True
            if is_change:
                count += 1
            else:
                comparison.pop(url)

    # return {
    #     "status": "success",
    #     "total_new_listings": total_new_listings,  # ✅
    #     "total_uploaded_listings": len(data),
    #     "total_existing_listings": len(existing_listings),
    #     "reid_id": current_reid_id,
    #     "changes_compare": changes,
    #     "changes_count": count,
    #     # "example_uploaded_listing": data[0],
    #     # "example_new_listing": listings.first().to_dict(),
    # }

    # query listings with geolocation
    geolocation_listings = db.query(Listing).filter(Listing.longitude != None).all()
    geolocation_listings = [listing.to_dict() for listing in geolocation_listings]
    geolocation_listings = {
        listing[link_field]: listing for listing in geolocation_listings
    }

    # 1. update the main data
    new_data = []
    for item in data:
        url = item[link_field]
        if url in comparison:
            new_value = {k: v["after"] for k, v in comparison[url].items()}
            item.update(new_value)
            new_data.append(item)
        else:
            new_data.append(item)

    # 2. add new listings
    for l in listings:
        if l.url not in comparison:
            new_data.append(l.to_dict())

    # 3. listings with geolocation
    if include_geolocation:
        for item in new_data:
            if item[link_field] in geolocation_listings:
                g = geolocation_listings[item[link_field]]
                item.update(
                    {
                        "Longitude": g["Longitude"],
                        "Latitude": g["Latitude"],
                    }
                )
        new_data_urls = [item[link_field] for item in new_data]
        for url, g in geolocation_listings.items():
            if url not in new_data_urls:
                new_data.append(g)

    # convert all timestamp into %B/%y format
    for item in new_data:
        date_keys = [
            "Sold Date",
            "List Date",
            "Scrape Date",
        ]
        for key in date_keys:
            date_value = item.get(key)
            if date_value:
                if isinstance(date_value, int):
                    try:
                        new_date = dt.fromtimestamp(date_value)
                        item[key] = new_date.strftime("%b/%y")
                    except ValueError:
                        new_date = dt.fromtimestamp(date_value / 1000)
                        item[key] = new_date.strftime("%b/%y")
                elif isinstance(date_value, dt):
                    item[key] = date_value.strftime("%b/%y")

    # Site status rule
    for item in new_data:
        sold_at = item.get("Sold Date")
        availability = item.get("Availability")
        if availability in ["Sold", "Delisted"]:
            if availability == "Delisted":
                item["Availability"] = "Sold"
                item["Site Status"] = "Delisted"
            elif availability == "Sold":
                item["Site Status"] = None
            if not sold_at:
                today = dt.now()
                today = today.replace(month=today.month - 1)
                item["Sold Date"] = today.strftime("%b/%y")
        else:
            item["Site Status"] = None
            item["Sold Date"] = None

    # Remove listing with no Longitude
    if include_geolocation:
        new_data = [item for item in new_data if "Longitude" in item]
        new_data = [item for item in new_data if item["Longitude"] is not None]

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w+") as tmp:
        json.dump(new_data, tmp, indent=2)
        tmp_path = tmp.name

    # Return the file and ensure it gets deleted after sending
    return FileResponse(
        path=tmp_path,
        filename=filename,
        media_type="application/json",
        background=lambda: os.unlink(
            tmp_path
        ),  # Delete the temp file after it's been sent
    )


@router.post("/count")
async def count_listings(
    file: Optional[UploadFile] = File(None),
    date: Optional[str] = Form(default="2025-03-01"),
    db: Session = Depends(get_db),
):
    """
    Count the number of listings in the file
    """
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )
    content = await file.read()
    data = json.loads(content)

    # count total listings
    total_listings = len(data)

    # count total new listings
    if date:
        reid_date = dt.strptime(date, "%Y-%m-%d")
        reid_date = reid_date.replace(month=reid_date.month - 1)
        reid_ids = [item["REID ID"] for item in data]
        reid_ids = [item for item in reid_ids if item]
        reid_ids = [
            item
            for item in reid_ids
            if item.startswith(reid_date.strftime("REID_%y_%m"))
        ]
        total_new_listings = len(reid_ids)
    else:
        total_new_listings = 0

    # get all sold dates
    if date:
        sold_date = dt.strptime(date, "%Y-%m-%d")
        sold_date = sold_date.replace(month=sold_date.month - 1)
        sold_dates = [item["Sold Date"] for item in data]
        sold_dates = [item for item in sold_dates if item]
        sold_dates = [
            item for item in sold_dates if item == sold_date.strftime("%b/%y")
        ]
    else:
        sold_dates = []

    listings = (
        db.query(Listing)
        .filter(
            Listing.is_available == False,
            Listing.updated_at >= date,
        )
        .all()
    )
    listing_urls = [item.url for item in listings]

    # cound sold listing by sold date
    sold_date_by_source = {}
    for item in data:
        status = item["Availability"]
        source = item["Source A"]
        listing_url = item["Property Link"]
        if status == "Sold" and source and listing_url in listing_urls:
            if source not in sold_date_by_source:
                sold_date_by_source[source] = 1
            else:
                sold_date_by_source[source] += 1

    return {
        "month": sold_date.strftime("%b/%y"),
        "total_listings": len(data),
        "total_new_listings": total_new_listings,
        "total_sold_listings": len(sold_dates),
        "sold_date_by_source": sold_date_by_source,
    }


@router.post("/before-after")
async def count_listings(
    file: Optional[UploadFile] = File(None),
    date: Optional[str] = Form(default="2025-03-01"),
    db: Session = Depends(get_db),
):
    """
    Compare availability before and after a certain date
    """
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )
    content = await file.read()
    data = json.loads(content)

    listings = db.query(Listing).filter(Listing.updated_at >= date).all()
    listings = [listing.to_dict() for listing in listings]
    listings = {listing["Property Link"]: listing for listing in listings}

    # compare listings availability before and after
    before_after = {}
    for item in data:
        url = item["Property Link"]
        if url in listings:
            before = item["Availability"]
            after = listings[url]["Availability"]
            if after == "Available" and before != "Available":
                before_after.update({url: {"before": before, "after": after}})

    return {
        "data": before_after,
    }
