"""
File upload and download routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Body
import json
from sqlalchemy.orm import Session
from fastapi.params import Depends
from sqlalchemy import func, text
from typing import Optional, List, Dict, Any

from database import get_checker_db
from func import get_domain
from models import Queue
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
    url_field: Optional[str] = Form(default="Property Link"),
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
                and url_field in item
                and item[url_field]
                and isinstance(item[url_field], str)
                and item[url_field].startswith("http")
            ):

                url = item[url_field]
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
