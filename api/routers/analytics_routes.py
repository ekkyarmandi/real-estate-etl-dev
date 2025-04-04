"""
API endpoints for analytics.
"""

import re
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func, desc

from models.listing import CheckerListing
from models.report import Report
from schemas.report import ReportList

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


@router.get("/listings-count")
def get_monthly_new_listings_count(db: Session = Depends(get_db)):
    """
    Retrieve the total count of new listings scraped.
    """
    try:
        listings = db.query(CheckerListing).all()
        total = {}
        for listing in listings:
            reid_id = listing.reid_id
            # REID_24_10_KIBR_12
            match = re.search(r"REID_(\d{2})_(\d{2})", reid_id)
            if match:
                year = match.group(1)
                month = match.group(2)
                date = f"20{year}-{month}-01"
                if date not in total:
                    total[date] = 0
                total[date] += 1
        # sort by date and return as dictionary
        total = sorted(total.items(), key=lambda x: x[0])
        return {date: count for date, count in total}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Internal server error during data retrieval."
        )


@router.get("/report", response_model=ReportList)
def get_report_count(date: str, db: Session = Depends(get_db)):
    """
    Retrieve the data scraping reports.
    """
    try:
        date_obj = datetime.strptime(date, "%Y-%m-01")
        current_date = date_obj + timedelta(days=31)
        current_month = current_date.strftime("%Y-%m-01")
        next_month = (current_date + timedelta(days=31)).strftime("%Y-%m-01")

        # First identify the most recent report id for each source
        subquery = (
            db.query(Report.source, func.max(Report.created_at).label("max_created_at"))
            .filter(Report.created_at >= current_month, Report.created_at < next_month)
            .group_by(Report.source)
            .subquery()
        )

        # Use the subquery to get the complete reports with the most recent created_at
        reports = (
            db.query(
                Report.id,
                Report.source,
                Report.created_at,
                func.sum(Report.item_scraped_count).label("total_listings"),
                func.sum(Report.item_scraped_count).label("success_count"),
                Report.response_error_count.label("error_count"),
                Report.elapsed_time_seconds.label("duration"),
            )
            .join(
                subquery,
                (Report.source == subquery.c.source)
                & (Report.created_at == subquery.c.max_created_at),
            )
            .filter(Report.created_at >= current_month, Report.created_at < next_month)
            .group_by(
                Report.id,
                Report.source,
                Report.created_at,
                Report.response_error_count,
                Report.elapsed_time_seconds,
            )
            .order_by(desc(Report.created_at))
            .all()
        )

        return {"reports": reports}
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        )
