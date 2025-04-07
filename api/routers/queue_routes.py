"""
Routes for queue management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from func import get_domain
from database import get_checker_db, get_db
from models import Queue, Listing
from schemas.queue import StatusUpdate, BulkStatusUpdate
from typing import List

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
    # Create base query with filters
    base_query = db.query(Queue)

    if status != "All":
        base_query = base_query.filter(Queue.status == status)
    if domain != "All":
        base_query = base_query.filter(Queue.url.like(f"%{domain}%"))
    if date != "All":
        base_query = base_query.filter(Queue.created_at >= date)

    # Get total count with the filter but without ordering or pagination
    total_count = base_query.count()

    # Apply ordering and pagination for the data query
    queues = (
        base_query.order_by(Queue.created_at.desc())
        .offset((page - 1) * 50)
        .limit(50)
        .all()
    )

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
    # Use a more efficient query that extracts domains directly
    domains_query = db.query(
        func.distinct(func.substring(Queue.url, "(?:https?://)?(?:www\.)?([^/]+)"))
    ).all()

    # Filter None values and convert to list
    domains = [domain[0] for domain in domains_query if domain[0]]
    domains.sort()

    return {"message": "success", "domains": domains}


@router.get("/sync")
async def sync_queue_to_listing(
    db: Session = Depends(get_checker_db), cloud_db: Session = Depends(get_db)
):
    """
    Sync queue from Checker DB to REID DB with optimized batch processing
    """
    this_month = datetime.now().strftime("%Y-%m-01")
    batch_size = 500  # Process in batches to reduce memory usage
    status_updates = {"Delisted": 0, "Error": 0, "Available": 0}

    # Process multiple statuses with the same pattern
    for status in ["Delisted", "Error", "Available"]:
        offset = 0
        while True:
            # Get URLs in batches
            queue_batch = (
                db.query(Queue.url)
                .filter(Queue.status == status, Queue.updated_at >= this_month)
                .offset(offset)
                .limit(batch_size)
                .all()
            )

            # Break if no more records
            if not queue_batch:
                break

            # Extract URLs from query results
            urls = [q[0] for q in queue_batch]

            # Only query listings that need updating (is_available doesn't match expected state)
            expected_availability = status == "Available"
            listings_to_update = (
                cloud_db.query(Listing)
                .filter(
                    Listing.url.in_(urls), Listing.is_available != expected_availability
                )
                .all()
            )

            # Apply updates
            for listing in listings_to_update:
                listing.status = status
                listing.updated_at = datetime.now()
                listing.is_available = expected_availability
                status_updates[status] += 1

            # Commit batch
            try:
                if listings_to_update:
                    cloud_db.commit()
            except Exception as e:
                cloud_db.rollback()
                raise HTTPException(
                    status_code=500, detail=f"Error updating listings: {str(e)}"
                )

            # Move to next batch
            offset += batch_size

    # Calculate total updated records
    total_updated = sum(status_updates.values())

    return {
        "message": "success",
        "details": f"{total_updated} queues have been synced",
        "breakdown": status_updates,
    }


@router.get("/errors/count")
async def get_total_count(db: Session = Depends(get_checker_db)):
    """
    Get total count of errors
    """
    total_errors = (
        db.query(func.count(Queue.id)).filter(Queue.status == "Error").scalar()
    )
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
    Update the status of multiple queue items at once with optimized batch processing
    """
    results = {"success": [], "failed": []}

    # Group updates by status for more efficient processing
    status_groups = {}
    for item in updates.items:
        if item.status not in status_groups:
            status_groups[item.status] = []
        status_groups[item.status].append(item.id)

    # Process each status group
    for status, ids in status_groups.items():
        batch_size = 500
        # Process in batches
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]

            try:
                # Fetch queue items to update
                queues = db.query(Queue).filter(Queue.id.in_(batch_ids)).all()
                queue_map = {q.id: q for q in queues}

                # Update status
                for queue_id in batch_ids:
                    if queue_id in queue_map:
                        queue_map[queue_id].status = status
                        results["success"].append(queue_id)
                    else:
                        results["failed"].append(
                            {"id": queue_id, "reason": "Not found"}
                        )

                # Commit batch
                db.commit()
            except Exception as e:
                db.rollback()
                # Record all failed IDs from this batch
                for queue_id in batch_ids:
                    if queue_id not in results["success"]:
                        results["failed"].append({"id": queue_id, "reason": str(e)})

    return {
        "status": "success",
        "message": f"Updated {len(results['success'])} items, {len(results['failed'])} failed",
        "results": results,
    }
