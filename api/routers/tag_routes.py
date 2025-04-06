"""
Routes for tag or listing issue management
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from reid.database import get_db
from models import Tag, Property, Listing
from schemas.tag import TagCount, TagList

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
    query = query.filter(Tag.is_solved == False, Tag.is_ignored == False)

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
        .filter(Property.tags.any(Tag.name == tag_name))
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
            data.append(
                {
                    "id": property.id,
                    "url": property.url,
                    "source": property.source,
                    "created_at": property.created_at,
                    "tags": [tag.name for tag in property.tags],
                    "title": property.title,
                    "description": property.description,
                    "region": getattr(property, "region", None),
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
                    "sold_at": getattr(property, "sold_at", None),
                    "is_excluded": getattr(property, "is_excluded", False),
                    "excluded_by": getattr(property, "excluded_by", None),
                    "tab": getattr(property, "tab", None),
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

    # update the property
    p.description = data.get("description", p.description)
    db.commit()
    db.refresh(p)

    # update the listing
    l = db.query(Listing).filter(Listing.url == p.url).first()
    if l:
        l.description = data.get("description", l.description)
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
