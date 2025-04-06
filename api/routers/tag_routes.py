"""
Routes for tag or listing issue management
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime

from reid.database import get_db
from models import Tag, Property, Listing
from schemas.tag import TagCount, TagList, BulkMarkAsSolvedOrIgnored

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/")
async def get_tags(date: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get unique tags and total count
    """
    query = db.query(Tag.name, func.count(Tag.id).label("count")).join(
        Property, Property.id == Tag.property_id
    )

    # filter the tags if it's solved or ignored
    query = query.filter(or_(Tag.is_solved == False, Tag.is_ignored == False))

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
    Get details for a specific tag
    """
    # query properties with tag name and order it by source name
    properties = (
        db.query(Property)
        .filter(
            Property.tags.any(
                Tag.name == tag_name
                and or_(Tag.is_solved == False, Tag.is_ignored == False),
            )
        )
        .order_by(Property.source)
    )
    if date:
        properties = properties.filter(Property.created_at >= date)

    # get total count
    total = properties.count()

    # paginate
    properties = properties.offset((page - 1) * size).limit(size)

    # properties as output data
    data = []
    urls = []
    for property in properties:
        if property.url not in urls:
            urls.append(property.url)
            listing = db.query(Listing).filter(Listing.url == property.url).first()
            if listing:
                listing_data = {
                    "region": listing.region,
                    "sold_at": listing.sold_at,
                    "is_excluded": listing.is_excluded,
                    "excluded_by": listing.excluded_by,
                    "tab": listing.tab,
                }
            else:
                listing_data = {}
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
    p = (
        db.query(Property)
        .filter(Property.id == property_id, Property.tags.any(name=tag))
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Property not found")

    # remove the tag from the property
    tag_found = False
    for tag_item in p.tags:
        if tag_item.name == tag:  # Compare with the parameter 'tag'
            if mode == "solved":
                tag_item.is_solved = True
            elif mode == "ignored":
                tag_item.is_ignored = True
            db.commit()
            tag_found = True
            break

    if not tag_found:
        raise HTTPException(
            status_code=404, detail=f"Tag '{tag}' not found for this property"
        )

    return {"message": "success"}


@router.patch("/bulk-marked/{tag_name}")
async def bulk_mark_as_solved_or_ignored(
    form: BulkMarkAsSolvedOrIgnored,
    tag_name: str,
    db: Session = Depends(get_db),
):
    """
    Bulk mark as solved or ignored
    """

    # query tags related to the property ids
    tags = (
        db.query(Tag)
        .filter(Tag.property_id.in_(form.property_ids), Tag.name == tag_name)
        .all()
    )

    # mark the properties as solved or ignored
    for tag in tags:
        tag.is_solved = form.mode == "solved"
        tag.is_ignored = form.mode == "ignored"

    db.commit()

    return {"message": "success"}
