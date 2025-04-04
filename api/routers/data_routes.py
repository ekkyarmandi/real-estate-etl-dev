"""
File upload and download routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Body
import json
from sqlalchemy.orm import Session
from fastapi.params import Depends
from sqlalchemy import func
from typing import Optional

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
        # Get counts by status
        status_counts = (
            db.query(Queue.status, func.count(Queue.id)).group_by(Queue.status).all()
        )

        stats = {item[0]: item[1] for item in status_counts}
        total = sum(stats.values())

        stats = {
            "total": total,
            "available": stats.get("Available", 0),
            "errors": stats.get("Error", 0),
            "delisted": stats.get("Delisted", 0),
            "sold": stats.get("Sold", 0),
        }

        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch queue statistics: {str(e)}"
        )


@router.post("/upload")
async def upload_file(
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_checker_db),
):
    """
    Receives data from the frontend and prints it to the terminal.
    Can accept either:
    - A file upload that contains JSON data

    Returns the parsed data or appropriate error messages.
    """
    result = {}

    # Process file if present
    if file:
        content = await file.read()
        try:
            # Try to parse content as JSON
            data = json.loads(content)
            urls = [
                item["Property Link"]
                for item in data
                if item["Availability"] == "Available"
            ]

            # query urls that are already exist in queue
            queues = db.query(Queue).all()
            queue_urls = [queue.url for queue in queues]

            # filter urls to check
            urls = [url for url in urls if get_domain(url) not in BLACKLIST_DOMAINS]
            urls = [url for url in urls if url is not None]
            urls = [url for url in urls if url.startswith("http")]

            # filter urls that are already exist in queue
            if queue_urls:
                urls = [url for url in urls if url not in queue_urls]

            # filter duplicate urls
            urls = list(set(urls))

            # create queue object
            batch_size = 10
            for i in range(0, len(urls), batch_size):
                batch_urls = urls[i : i + batch_size]
                queues = []
                for url in batch_urls:
                    queue = Queue(
                        url=url,
                        listing_id=None,
                        status="Available",
                    )
                    queues.append(queue)
                try:
                    db.add_all(queues)
                    db.commit()
                except Exception as err:
                    db.rollback()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid JSON data in the uploaded file"
            )

    return {"status": "success", "data": {"count": len(urls)}}
