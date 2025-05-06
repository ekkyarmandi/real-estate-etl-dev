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
from datetime import datetime
from tqdm import tqdm
import tempfile
import re
import os

from database import get_local_db, get_cloud_db, get_checker_db, get_db
from func import get_domain, convert_dates_in_item
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
        item = convert_dates_in_item(item)

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

    date = dt.strptime(date, "%Y-%m-%d")
    date = date.replace(month=date.month - 1)
    prev_month = date.strftime("%b/%y")

    # count total new listings
    if date:
        reid_ids = [item["REID ID"] for item in data]
        reid_ids = [item for item in reid_ids if item]
        reid_ids = [i for i in reid_ids if i.startswith(date.strftime("REID_%y_%m"))]
        total_new_listings = len(reid_ids)
    else:
        total_new_listings = 0

    blacklist_source = [
        "Coco Developments",
        "Alex Villa",
        "Living Properties",
        "Mirah",
        "Loyo Development",
        "Anta Group",
        "Pertama",
        "Nexa",
        "Address Bali",
        "Body Factory Bali",
    ]

    # query bali home immo listings
    bhi = db.query(Listing).filter(Listing.source == "Bali Home Immo").all()
    bhi = {l.url: l.to_dict() for l in bhi}

    # cound sold listing by sold date
    sold_out_listings = {}
    total_sould_out = 0
    missing_sold_date = 0
    for item in data:
        sold_date = item["Sold Date"]
        status = item["Availability"]
        source = item["Source A"]
        url = item["Property Link"]
        if status != "Available" and source and source not in blacklist_source:
            if source == "Bali Home Immo":
                if url not in bhi:
                    continue
                bhi_month = bhi[url].get("Sold Date")
                if bhi_month and sold_date == bhi_month:
                    if source not in sold_out_listings:
                        sold_out_listings[source] = 1
                    else:
                        sold_out_listings[source] += 1
                    total_sould_out += 1
                elif not sold_date:
                    missing_sold_date += 1
            else:
                if sold_date == prev_month:
                    if source not in sold_out_listings:
                        sold_out_listings[source] = 1
                    else:
                        sold_out_listings[source] += 1
                    total_sould_out += 1
                elif not sold_date:
                    missing_sold_date += 1

    return {
        "month": prev_month,
        "total_listings": len(data),
        "total_new_listings": total_new_listings,
        "total_sold_listings": total_sould_out,
        "missing_sold_date": missing_sold_date,
        "sold_out_listing_by_source": sold_out_listings,
    }


@router.post("/count-json")
async def count_json_listings(
    file: Optional[UploadFile] = File(None),
    checker_db: Session = Depends(get_checker_db),
    cloud_db: Session = Depends(get_cloud_db),
):
    """
    Count JSON listing availability status based on URL and availability
    """
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )
    content = await file.read()
    data = json.loads(content)
    # Count listing availability by 'Availability' attr
    count = {
        "count": {
            "available": 0,
            "not_available": 0,
        },
        "count-not-available-in": {
            "reid_db": 0,
            "checker_db": 0,
        },
    }
    urls = []
    for listing in data:
        if listing["Availability"] == "Available":
            count["count"]["available"] += 1
        else:
            count["count"]["not_available"] += 1
        urls.append(listing["Property Link"])
    # Count total listing that not exist in reid_db
    existing_urls = set(
        url
        for (url,) in cloud_db.query(Listing.url).filter(Listing.url.in_(urls)).all()
    )
    urls_set = set(urls)
    missing_urls = urls_set - existing_urls
    count["count-not-available-in"]["reid_db"] = len(missing_urls)
    # Count total listing that not exist in checker db
    existing_urls = set(
        url for (url,) in checker_db.query(Queue.url).filter(Queue.url.in_(urls)).all()
    )
    urls_set = set(urls)
    missing_urls = urls_set - existing_urls
    count["count-not-available-in"]["checker_db"] = len(missing_urls)
    return count


@router.post("/before-after")
async def availability_comparison(
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

    # convert date into B/y format and subtract 1 month
    date = dt.strptime(date, "%Y-%m-%d")
    date = date.replace(month=date.month - 1)
    month = date.strftime("%b/%y")

    # compare listings availability before and after
    before_after = []
    for item in data:
        url = item["Property Link"]
        if url in listings:
            before = item["Availability"]
            before_sold_date = item["Sold Date"]
            after = listings[url]["Availability"]
            if after == "Available" and before != "Available":
                before_after.append(
                    {
                        "url": url,
                        "sold_date": before_sold_date,
                        "status_before": before,
                        "current_month": month,
                        "status_after": after,
                    }
                )

    return {
        "count": len(before_after),
        "data": before_after,
    }


@router.post("/check")
async def availability_comparison(
    file: Optional[UploadFile] = File(None),
    date: Optional[str] = Form(default="2025-03-01"),
    db: Session = Depends(get_db),
):
    """
    Availability check and comparison
    """
    # load data
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )
    content = await file.read()
    data = json.loads(content)

    # load listings
    listings = (
        db.query(Listing)
        .filter((Listing.sold_at == None) & (Listing.is_available == False))
        .all()
    )
    # listings = [l.to_dict() for l in listings]
    listings = {l.url: l for l in listings}

    raja_villa = (
        db.query(Listing)
        .filter((Listing.source == "Bali Home Immo") & (Listing.is_available == False))
        .all()
    )
    # raja_villa = [l.to_dict() for l in raja_villa]
    raja_villa = {l.url: l for l in raja_villa}

    # GOALS
    # i want to fill any missing sold date in the listing
    # with sold date in the previous dataset for the same url

    # Is there any listings in data that missings sold date? Few, and the source don't even exist in the project
    # output = {}
    # for item in data:
    #     url = item["Property Link"]
    #     sold_date = item["Sold Date"]
    #     status = item["Availability"]
    #     source = item["Source A"]
    #     if status != "Available" and not sold_date:
    #         if source in output:
    #             output[source] += 1
    #         else:
    #             output.update({source: 1})
    # return {"results": {"data": output}}

    # How many listings in db that missing sold date while it actually not missing in data table: 120
    # len_exist = 0
    # for item in data:
    #     url = item["Property Link"]
    #     sold_date = item["Sold Date"]
    #     status = item["Availability"]
    #     if url in listings and sold_date and status != "Available":
    #         len_exist += 1
    # count = {
    #     "listings": len(listings),
    #     "exist": len_exist,
    # }

    # Sync listings missing sold date with main database data
    result = []
    # for item in data:
    #     url = item["Property Link"]
    #     sold_date = item["Sold Date"]
    #     status = item["Availability"]
    #     if status != "Available" and sold_date:
    #         if url in listings:
    #             listing = listings[url]
    #         else:
    #             listing = None
    #         # elif url in raja_villa:
    #         #     listing = raja_villa[url]
    #         if listing:
    #             new_listing = {
    #                 "url": url,
    #                 "before": {
    #                     "sold_status": listing.sold_at,
    #                     "status": listing.availability,
    #                 },
    #                 "after": {
    #                     "sold_status": item["Sold Date"],
    #                     "status": item["Availability"],
    #                 },
    #             }
    #             result.append(new_listing)

    # result = []
    for item in tqdm(data):
        url = item["Property Link"]
        sold_date = item["Sold Date"]
        status = item["Availability"]
        if status != "Available" and sold_date:
            if url in raja_villa:
                listing = raja_villa[url]
            elif url in listings:
                listing = listings[url]
            else:
                listing = None
            # convert sold_date to str
            sold_date = datetime.fromtimestamp(sold_date / 1000)
            if listing:
                delisted = item["Site Status"]
                # update listing
                listing.sold_at = sold_date.strftime("%Y-%m-%d")
                listing.is_available = False
                listing.availability = delisted if delisted else status
                db.commit()
                db.refresh(listing)
                # after refresh
                new_listing = {
                    "url": url,
                    "before": {
                        "sold_date": listing.sold_at,
                        "status": listing.availability,
                    },
                    "after": {
                        "sold_date": sold_date.strftime("%Y-%m-%d"),
                        "status": status,
                    },
                }
                result.append(new_listing)

    return {"results": {"count": len(result), "data": result}}


@router.post("/check-sold-date")
async def check_sold_date(
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Check how many listings are new and have been sold
    based on data provided
    """
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )
    content = await file.read()
    data = json.loads(content)
    data_urls = [item["Property Link"] for item in data]

    # load listings
    listings = db.query(Listing).filter(Listing.url.in_(data_urls)).all()
    listings = {l.url: l.to_dict() for l in listings}

    # load new listings
    new_listings = db.query(Listing).filter(Listing.scraped_at == "2025-03-01").all()
    new_listings = {l.url: l.to_dict() for l in new_listings}

    # how many new listings?
    count_new_listings = 0
    for l in new_listings:
        if l not in data_urls:
            count_new_listings += 1

    # define whitelist column
    columns = [
        "Source A",
        "Contract Type",
        "Property Type",
        "Years",
        "Bedrooms",
        "Bathrooms",
        "Land Size (SQM)",
        "Build Size (SQM)",
        "Price",
        "Price ($)",
        "Image",
        "Title",
        "Description",
        "Off plan",
    ]

    # how many listings updated as not available?
    count_soldout_listings = 0
    detail_change = []
    for item in data:
        url = item["Property Link"]
        status = item["Availability"]
        if url in listings:
            l = listings[url]
            listing_status = l["Availability"]
            is_status_change = status == "Available" and status != listing_status
            if is_status_change:
                count_soldout_listings += 1
            changes = {"url": url}
            for key in l.keys():
                if key in columns and item[key] != l[key]:
                    old_value = item[key]
                    new_value = l[key]
                    # skip it , if new value is the build size or land size and end with 2
                    if key == "Build Size (SQM)" or key == "Land Size (SQM)":
                        # turn new value into string
                        new_value_str = str(new_value)
                        # split the decimal point
                        new_value_str = new_value_str.split(".")[0]
                        # check if the last digit is 2
                        if new_value_str.endswith("2"):
                            continue
                    # skip it if new value is empty
                    if not new_value:
                        continue
                    changes.update({key: {"before": old_value, "after": new_value}})
            # only append changes if it has more than 1 key
            # it indicates that the listing has been updated
            # one attribute only means there are only url value inside
            if len(changes) > 1:
                detail_change.append(changes)

    # how many listings being updated
    output = {
        "report": {
            "count_new_listings": count_new_listings,
            "count_soldout_listings": count_soldout_listings,
            "total_changes": len(detail_change),
            "changes": detail_change,
        }
    }

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"result_{now}.json"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w+") as tmp:
        json.dump(output, tmp, indent=2)
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


@router.post("/insert-and-update-json")
async def insert_and_update_json(
    file: UploadFile = File(...),
    local_db: Session = Depends(get_local_db),
    cloud_db: Session = Depends(get_cloud_db),
    checker_db: Session = Depends(get_checker_db),
):
    """
    Receive a JSON file for new listtings insertion and
    update existing listings availability status
    """
    if not file:
        raise HTTPException(
            status_code=400, detail="No data provided. Please upload a file."
        )
    content = await file.read()
    data = json.loads(content)
    listings = list(filter(lambda x: x["Availability"] == "Available", data))
    data_urls = list(set([x["Property Link"] for x in listings if x["Property Link"]]))

    # convert data into listings data
    listings_data = {l["Property Link"]: l for l in data}

    # load listing from checker db
    current_month = dt.now().strftime("%Y-%m-01")
    listings = (
        checker_db.query(Queue)
        .filter(
            Queue.updated_at >= current_month,
            Queue.status != "Available",
            Queue.url.in_(data_urls),
        )
        .all()
    )
    listings = {l.url: l.status for l in listings}
    print("Total updated listings in checker db:", len(listings))

    count = {
        "total_sold": 0,
        "total_delisted": 0,
        "total_new": 0,
    }

    ## Update listings availability
    for url, new_status in listings.items():

        if not url or not url.strip():
            continue

        if url in listings_data:
            item = listings_data[url]

            # Use listings to update the item availability
            sold_date = item.get("Sold Date")

            # update availability
            if not sold_date:
                if new_status in ["Sold", "Delisted"]:
                    now = dt.now()
                    now = now.replace(month=now.month - 1)
                    item["Sold Date"] = now.strftime("%b/%y")
                    item["Availability"] = "Sold"
                    if new_status == "Delisted":
                        item["Site Status"] = "Delisted"
                        count["total_delisted"] += 1
                    elif new_status == "Sold":
                        item["Site Status"] = None
                        count["total_sold"] += 1

    ## Insert new listings
    ### Query listings from Cloud DB
    new_listings = []
    cloud_listings = (
        cloud_db.query(Listing).filter(Listing.created_at >= current_month).all()
    )
    print("Total Cloud Listings:", len(cloud_listings))
    new_listings.extend(cloud_listings)
    ### Query listings from Local DB
    local_listings = (
        local_db.query(Listing).filter(Listing.created_at >= current_month).all()
    )
    print("Total Local Listings:", len(local_listings))
    new_listings.extend(local_listings)
    for item in new_listings:
        if item.url not in listings_data:
            data.append(item.to_dict())
            count["total_new"] += 1

    ## Fix listings date attributes
    for item in data:
        item = convert_dates_in_item(item)

    ## Output listings as new JSON file
    default_file_name = file.filename.split(".")[0]
    filename = f"{default_file_name}_new.json"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w+") as tmp:
        json.dump(data, tmp, indent=2)
        tmp_path = tmp.name

    # return count
    return FileResponse(
        path=tmp_path,
        filename=filename,
        media_type="application/json",
        background=lambda: os.unlink(tmp_path),
    )
