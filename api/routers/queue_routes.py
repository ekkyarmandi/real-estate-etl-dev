"""
Routes for queue management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_checker_db
from models import Queue, CheckerListing
from schemas.queue import StatusUpdate, BulkStatusUpdate

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/sync")
async def sync_queue_to_listing(db: Session = Depends(get_checker_db)):
    """
    Sync queue result to listing table
    """
    # count all available queue that exist in listing table
    listing_urls = (
        db.query(CheckerListing.url).filter(CheckerListing.is_available).all()
    )
    listing_urls = [url[0] for url in listing_urls]
    queues = db.query(Queue).filter(
        Queue.status.not_in(["Available", "Excluded", "Error"]),
        Queue.url.in_(listing_urls),
    )
    # update listing table with queue result
    count = 0
    errors = 0
    not_available = 0
    for q in queues:
        listing = db.query(CheckerListing).filter(CheckerListing.url == q.url).first()
        if listing:
            listing.is_available = False
            listing.available_text = q.status
            try:
                db.commit()
                count += 1
            except Exception as e:
                print(f"Error updating listing {q.url}: {e}")
                db.rollback()
                errors += 1
        else:
            not_available += 1
    return {
        "message": "success",
        "count": count,
        "errors": errors,
        "not_available": not_available,
        "details": f"{count} listings have been updated",
    }


@router.get("/errors")
async def get_errors(page: int = 1, db: Session = Depends(get_checker_db)):
    """
    Get all errors from queue
    """
    total_errors = db.query(Queue).filter(Queue.status == "Error").count()
    queues = (
        db.query(Queue)
        .filter(Queue.status == "Error", Queue.url.not_like("%bali-home-immo.com%"))
        .order_by(Queue.url)
        .limit(50)
        .offset((page - 1) * 50)
        .all()
    )
    return {
        "message": "success",
        "results": {
            "count": len(queues),
            "total": total_errors,
            "queues": [{"id": q.id, "url": q.url} for q in queues],
        },
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
