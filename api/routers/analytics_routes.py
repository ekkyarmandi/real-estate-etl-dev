"""
API endpoints for analytics.
"""

import re
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func, desc, text, extract

from models.listing import Listing
from models.report import Report
from schemas.report import ReportList

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


@router.get("/listings-count")
def get_monthly_new_listings_count(db: Session = Depends(get_db)):
    """
    Retrieve the total count of new listings scraped using efficient database aggregation.
    """
    try:
        # Use direct database aggregation instead of Python processing
        # This version uses regex extraction at the database level
        query = text(
            """
            SELECT 
                CONCAT('20', SUBSTRING(reid_id, 6, 2), '-', SUBSTRING(reid_id, 9, 2), '-01') AS date_key,
                COUNT(*) AS listing_count
            FROM 
                listing
            WHERE 
                reid_id REGEXP 'REID_[0-9]{2}_[0-9]{2}'
            GROUP BY 
                date_key
            ORDER BY 
                date_key
        """
        )

        result = db.execute(query).fetchall()

        # Convert to dictionary with proper date keys
        monthly_counts = {row[0]: row[1] for row in result}

        return monthly_counts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/report", response_model=ReportList)
def get_report_count(date: str, db: Session = Depends(get_db)):
    """
    Retrieve the data scraping reports with optimized query performance.
    """
    try:
        date_obj = datetime.strptime(date, "%Y-%m-01")
        current_month = date_obj.strftime("%Y-%m-01")
        next_month = (date_obj + timedelta(days=31)).strftime("%Y-%m-01")

        # Use a more efficient CTE approach with window functions to get the most recent reports
        # This is more efficient than the subquery approach
        query = text(
            """
            WITH ranked_reports AS (
                SELECT 
                    id,
                    source,
                    created_at,
                    item_scraped_count,
                    response_error_count,
                    elapsed_time_seconds,
                    ROW_NUMBER() OVER (PARTITION BY source ORDER BY created_at DESC) as rn
                FROM 
                    report
                WHERE 
                    created_at >= :current_month AND created_at < :next_month
            )
            SELECT 
                id,
                source,
                created_at,
                item_scraped_count AS total_listings,
                item_scraped_count AS success_count,
                response_error_count AS error_count,
                elapsed_time_seconds AS duration
            FROM 
                ranked_reports
            WHERE 
                rn = 1
            ORDER BY 
                created_at DESC
        """
        )

        reports = db.execute(
            query, {"current_month": current_month, "next_month": next_month}
        ).fetchall()

        # Convert to expected format - maintain SQLAlchemy's row result structure
        formatted_reports = []
        for report in reports:
            formatted_reports.append(
                {
                    "id": report[0],
                    "source": report[1],
                    "created_at": report[2],
                    "total_listings": report[3],
                    "success_count": report[4],
                    "error_count": report[5],
                    "duration": report[6],
                }
            )

        return {"reports": formatted_reports}
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        )
