"""
Main FastAPI application entry point.
"""

import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the parent directory (DataScraper) to the Python path
# This allows importing modules from the 'models' directory when running from 'api/'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Now import the routers - they will handle their own model imports
# from api.routers import tags_routes
from routers import (
    analytics_routes,
    data_routes,
    queue_routes,
)

app = FastAPI(
    title="DataScraper API",
    description="API for accessing scraped property data and analytics.",
    version="0.1.0",
)

# Include routers
app.include_router(analytics_routes.router)
# app.include_router(tags_routes.router)
app.include_router(data_routes.router)
app.include_router(queue_routes.router)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to the DataScraper API"}
