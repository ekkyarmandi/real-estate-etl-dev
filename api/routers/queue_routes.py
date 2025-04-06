"""
Routes for queue management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from func import get_domain
from database import get_checker_db, get_db
from models import Queue, Listing
from schemas.queue import StatusUpdate, BulkStatusUpdate

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/")
async def get_queues(
    page: int = 1,
    status: str = "All",
    domain: str = "All",
    date: str = "All",
    db: Session = Depends(get_checker_db),
):
    """
    Get all queues
    """
    queues = db.query(Queue)
    queues = queues.order_by(Queue.created_at.desc())
    if status != "All":
        queues = queues.filter(Queue.status == status)
    if domain != "All":
        queues = queues.filter(Queue.url.like(f"%{domain}%"))
    if date != "All":
        queues = queues.filter(Queue.created_at >= date)
    total_count = queues.count()
    queues = queues.offset((page - 1) * 50).limit(50).all()
    return {
        "message": "success",
        "results": {
            "count": len(queues),
            "total": total_count,
            "items": [{"id": q.id, "url": q.url} for q in queues],
        },
    }


@router.get("/domains")
async def get_domains(db: Session = Depends(get_checker_db)):
    """
    Get all unique domains
    """
    queues = db.query(Queue).distinct().all()
    urls = [get_domain(q.url) for q in queues]
    urls = [url for url in urls if url is not None]
    domains = list(set(urls))
    domains.sort()
    return {"message": "success", "domains": domains}


@router.get("/sync")
async def sync_queue_to_listing(
    db: Session = Depends(get_checker_db), cloud_db: Session = Depends(get_db)
):
    """
    Sync queue from Checker DB to REID DB
    """
    # query all not available queues from checker db
    this_month = datetime.now().strftime("%Y-%m-01")
    statuses = ["Delisted", "Error"]
    count = 0
    for status in statuses:
        queues = (
            db.query(Queue)
            .filter(Queue.status == status, Queue.updated_at >= this_month)
            .all()
        )
        queue_urls = [q.url for q in queues]
        listings = (
            cloud_db.query(Listing)
            .filter(Listing.url.in_(queue_urls), Listing.is_available == False)
            .all()
        )
        for listing in listings:
            listing.status = status
            listing.updated_at = datetime.now()
            listing.is_available = status == "Available"
            count += 1
    # query all available queues from checker db
    queues = (
        db.query(Queue)
        .filter(Queue.status == "Available", Queue.updated_at >= this_month)
        .all()
    )
    queue_urls = [q.url for q in queues]
    listings = (
        cloud_db.query(Listing)
        .filter(Listing.url.in_(queue_urls), Listing.is_available == False)
        .all()
    )
    for listing in listings:
        listing.status = "Available"
        listing.updated_at = datetime.now()
        listing.is_available = True
        count += 1

    # commit all changes
    try:
        cloud_db.commit()
    except Exception as e:
        print(f"Error updating listing {listing.url}: {e}")
        cloud_db.rollback()

    return {
        "message": "success",
        "details": f"{count} queues have been synced",
    }


@router.get("/errors/count")
async def get_total_count(db: Session = Depends(get_checker_db)):
    """
    Get total count of errors
    """
    total_errors = db.query(Queue).filter(Queue.status == "Error").count()
    return {
        "message": "success",
        "results": {
            "count": total_errors,
        },
    }


@router.put("/errors/bulk")
async def bulk_status_update(
    updates: BulkStatusUpdate, db: Session = Depends(get_checker_db)
):
    """
    Update the status of multiple queue items at once
    """
    results = {"success": [], "failed": []}
    for item in updates.items:
        try:
            queue = db.query(Queue).filter(Queue.id == item.id).first()
            if queue:
                queue.status = item.status
                results["success"].append(item.id)
            else:
                results["failed"].append({"id": item.id, "reason": "Not found"})
        except Exception as e:
            results["failed"].append({"id": item.id, "reason": str(e)})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to commit changes: {str(e)}"
        )

    return {
        "status": "success",
        "message": f"Updated {len(results['success'])} items, {len(results['failed'])} failed",
        "results": results,
    }
