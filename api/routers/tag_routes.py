"""
Routes for tag or listing issue management
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, update
from datetime import datetime

from database import get_db
from models import Tag, Property, Listing
from schemas.tag import BuildUpdatePayload, TagCount, TagList, BulkMarkAsSolvedOrIgnored

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/")
async def get_tags(date: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get unique tags and total count
    """
    # Create a CTE query for better performance with large datasets
    query = db.query(Tag.name, func.count(Tag.id).label("count")).join(
        Property, Property.id == Tag.property_id
    )

    # filter the tags if it's solved or ignored
    query = query.filter((Tag.is_solved == False) & (Tag.is_ignored == False))

    if date:
        query = query.filter(Property.created_at >= date)

    tag_counts = query.group_by(Tag.name).all()
    # construct tag items
    tag_items = [
        TagCount(id=name, name=name.replace("_", " ").title(), count=count)
        for name, count in tag_counts
    ]
    return TagList(tags=tag_items)


@router.get("/{tag_name}")
async def get_tag_details(
    tag_name: str,
    date: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get details for a specific tag with optimized query performance
    """
    # Use a join instead of any() to improve query performance
    properties_query = (
        db.query(Property)
        .join(Tag, Property.id == Tag.property_id)
        .filter(Tag.name == tag_name, Tag.is_solved == False, Tag.is_ignored == False)
        .order_by(Property.source)
        .distinct()
    )

    if date:
        properties_query = properties_query.filter(Property.created_at >= date)

    # Get total count efficiently with a separate, simpler count query
    total = properties_query.count()

    # Apply pagination
    properties = properties_query.offset((page - 1) * size).limit(size).all()

    # Get all URLs at once
    property_urls = [p.url for p in properties]

    # Preload all needed listings in a single query instead of N+1 query pattern
    listings_dict = {}
    if property_urls:
        listings = db.query(Listing).filter(Listing.url.in_(property_urls)).all()
        listings_dict = {listing.url: listing for listing in listings}

    # Build the result data
    data = []
    urls = []  # Track unique URLs

    for property in properties:
        if property.url not in urls:
            urls.append(property.url)
            listing = listings_dict.get(property.url)

            listing_data = {}
            if listing:
                listing_data = {
                    "region": listing.region,
                    "sold_at": listing.sold_at,
                    "is_excluded": listing.is_excluded,
                    "excluded_by": listing.excluded_by,
                    "tab": listing.tab,
                }

            data.append(
                {
                    "id": property.id,
                    "url": property.url,
                    "source": property.source,
                    "created_at": property.created_at,
                    "tags": [tag.name for tag in property.tags],
                    "title": property.title,
                    "description": property.description,
                    "region": listing_data.get("region", None),
                    "location": property.location,
                    "leasehold_years": property.leasehold_years,
                    "contract_type": property.contract_type,
                    "property_type": property.property_type,
                    "bedrooms": property.bedrooms,
                    "bathrooms": property.bathrooms,
                    "build_size": property.build_size,
                    "land_size": property.land_size,
                    "land_zoning": property.land_zoning,
                    "price": property.price,
                    "currency": property.currency,
                    "is_available": property.is_available,
                    "availability": property.availability,
                    "is_off_plan": property.is_off_plan,
                    "sold_at": listing_data.get("sold_at", None),
                    "is_excluded": listing_data.get("is_excluded", False),
                    "excluded_by": listing_data.get("excluded_by", None),
                    "tab": listing_data.get("tab", None),
                }
            )

    return {
        "message": "success",
        "data": data,
        "total": total,
        "page": page,
        "size": size,
    }


@router.put("/{property_id}")
async def update_listing(
    property_id: str,
    data: dict,
    db: Session = Depends(get_db),
):
    """
    Update a listing
    """
    # query the property
    p = db.query(Property).filter(Property.id == property_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found")

    # update the property with all editable fields
    p.title = data.get("title", p.title)
    p.description = data.get("description", p.description)
    p.location = data.get("location", p.location)
    p.leasehold_years = data.get("leasehold_years", p.leasehold_years)
    p.contract_type = data.get("contract_type", p.contract_type)
    p.property_type = data.get("property_type", p.property_type)
    p.bedrooms = data.get("bedrooms", p.bedrooms)
    p.bathrooms = data.get("bathrooms", p.bathrooms)
    p.build_size = data.get("build_size", p.build_size)
    p.price = data.get("price", p.price)
    p.currency = data.get("currency", p.currency)

    # Handle availability and sold_at together for consistency
    if "availability" in data:
        availability = data.get("availability", "")
        p.availability = availability
        p.is_available = availability == "Available"

        # If marked as Sold, ensure sold_at date exists
        if availability == "Sold" and not p.sold_at and "sold_at" not in data:
            p.sold_at = datetime.now()
        # If marked as Available, clear sold_at date
        elif availability == "Available":
            p.sold_at = None

    # Handle sold_at field explicitly if provided
    if "sold_at" in data:
        p.sold_at = data.get("sold_at")
        # If sold_at is set, make sure availability reflects this
        if p.sold_at:
            p.availability = "Sold"
            p.is_available = False
        elif p.availability == "Sold":
            # If sold_at was cleared but availability was "Sold", reset to Available
            p.availability = "Available"
            p.is_available = True

    # Handle excluded_by field
    if "excluded_by" in data:
        p.excluded_by = data.get("excluded_by", "").strip()
        # Set is_excluded based on excluded_by value - true if value exists, false otherwise
        p.is_excluded = bool(p.excluded_by)

    db.commit()
    db.refresh(p)

    # update the listing if it exists
    l = db.query(Listing).filter(Listing.url == p.url).first()
    if l:
        # Update the updated_at timestamp
        l.updated_at = datetime.now()

        l.title = data.get("title", l.title)
        l.description = data.get("description", l.description)
        l.region = data.get("region", l.region) if hasattr(l, "region") else None
        l.location = data.get("location", l.location)
        l.leasehold_years = data.get("leasehold_years", l.leasehold_years)
        l.contract_type = data.get("contract_type", l.contract_type)
        l.property_type = data.get("property_type", l.property_type)
        l.bedrooms = data.get("bedrooms", l.bedrooms)
        l.bathrooms = data.get("bathrooms", l.bathrooms)
        l.build_size = data.get("build_size", l.build_size)
        l.price = data.get("price", l.price)
        l.currency = data.get("currency", l.currency)

        # Apply the same availability and sold_at logic to listing
        if "availability" in data:
            availability = data.get("availability", "")
            l.availability = availability
            l.is_available = availability == "Available"

            if availability == "Sold" and not l.sold_at and "sold_at" not in data:
                l.sold_at = datetime.now()
            elif availability == "Available":
                l.sold_at = None

        if "sold_at" in data:
            l.sold_at = data.get("sold_at")
            if l.sold_at:
                l.availability = "Sold"
                l.is_available = False
            elif l.availability == "Sold":
                l.availability = "Available"
                l.is_available = True

        # Handle excluded_by field for listing
        if "excluded_by" in data:
            l.excluded_by = data.get("excluded_by", "").strip()
            # Set is_excluded based on excluded_by value - true if value exists, false otherwise
            l.is_excluded = bool(l.excluded_by)

        # Reclassify tab based on updated values
        if hasattr(l, "classify_tab") and callable(l.classify_tab):
            l.classify_tab()
        else:
            # Manual tab classification if method not available
            if l.price >= 78656000000 and l.currency == "IDR":
                l.tab = "LUXURY LISTINGS"
            elif l.price >= 5000000 and l.currency == "USD":
                l.tab = "LUXURY LISTINGS"
            elif l.property_type == "Land":
                l.tab = "ALL LAND"
            else:
                l.tab = "DATA"

        db.commit()
        db.refresh(l)

    return {"message": "success"}


@router.put("/{property_id}/mark-as-solved")
def mark_as_solved_or_ignored(
    property_id: str, tag: str, mode: str = "solved", db: Session = Depends(get_db)
):
    """
    Mark a property as solved or ignored
    """
    # More efficient query using explicit join
    tag_item = (
        db.query(Tag)
        .join(Property, Property.id == Tag.property_id)
        .filter(Property.id == property_id, Tag.name == tag)
        .first()
    )

    if not tag_item:
        raise HTTPException(
            status_code=404,
            detail=f"Property with ID {property_id} and tag '{tag}' not found",
        )

    # Update directly without loop
    if mode == "solved":
        tag_item.is_solved = True
    elif mode == "ignored":
        tag_item.is_ignored = True

    db.commit()
    return {"message": "success"}


@router.patch("/bulk-marked/{tag_name}")
async def bulk_mark_as_solved_or_ignored(
    form: BulkMarkAsSolvedOrIgnored,
    tag_name: str,
    db: Session = Depends(get_db),
):
    """
    Bulk mark as solved or ignored using efficient bulk updates
    """
    if not form.property_ids:
        return {"message": "success", "count": 0}

    # Use bulk update instead of fetching all tags and updating individually
    is_solved = form.mode == "solved"
    is_ignored = form.mode == "ignored"

    # Using SQLAlchemy's Update object for bulk updates
    try:
        # Execute a bulk update operation
        result = db.execute(
            update(Tag)
            .where(Tag.property_id.in_(form.property_ids), Tag.name == tag_name)
            .values(is_solved=is_solved, is_ignored=is_ignored)
        )
        db.commit()
        return {"message": "success", "count": result.rowcount}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/bulk-update")
async def bulk_update(form: BuildUpdatePayload, db: Session = Depends(get_db)):
    """
    Bulk update properties with optimized database operations
    """
    if not form.items:
        return {"message": "success"}

    # Extract all property IDs
    property_ids = [item["id"] for item in form.items]

    # Get all properties in a single query
    properties = db.query(Property).filter(Property.id.in_(property_ids)).all()
    property_map = {p.id: p for p in properties}

    # Get all property URLs from the fetched properties
    property_urls = [p.url for p in properties if p.id in property_map]

    # Get all related listings in a single query
    listings = db.query(Listing).filter(Listing.url.in_(property_urls)).all()
    listing_map = {l.url: l for l in listings}

    # Process updates - first collect all changes
    property_updates = []
    listing_updates = []

    for item in form.items:
        property_id = item["id"]
        if property_id in property_map:
            property = property_map[property_id]

            # Update property attributes
            for key, value in item.items():
                if key != "id" and hasattr(property, key):
                    setattr(property, key, value)
            property_updates.append(property)

            # Update related listing if exists
            if property.url in listing_map:
                listing = listing_map[property.url]
                # Update the updated_at timestamp
                listing.updated_at = datetime.now()

                for key, value in item.items():
                    if key != "id" and hasattr(listing, key):
                        setattr(listing, key, value)

                # Tab classification logic
                if hasattr(listing, "classify_tab") and callable(listing.classify_tab):
                    listing.classify_tab()
                else:
                    # Manual tab classification
                    if listing.price >= 78656000000 and listing.currency == "IDR":
                        listing.tab = "LUXURY LISTINGS"
                    elif listing.price >= 5000000 and listing.currency == "USD":
                        listing.tab = "LUXURY LISTINGS"
                    elif listing.property_type == "Land":
                        listing.tab = "ALL LAND"
                    else:
                        listing.tab = "DATA"

                listing_updates.append(listing)

    # Commit all changes in a single transaction
    try:
        db.commit()
        return {
            "message": "success",
            "updated_properties": len(property_updates),
            "updated_listings": len(listing_updates),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
