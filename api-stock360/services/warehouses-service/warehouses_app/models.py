from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserInToken(BaseModel):
    sub: str = Field(..., description="The user ID of the authenticated user.")
    role: str = Field(..., description="The role of the authenticated user.")


class Location(BaseModel):
    lat: Optional[float] = Field(
        None, description="Latitude coordinate (auto-filled from address when missing)."
    )
    lon: Optional[float] = Field(
        None, description="Longitude coordinate (auto-filled from address when missing)."
    )
    address: Optional[str] = Field(None, description="Physical street address.")


class Warehouse(BaseModel):
    """Base model for a Warehouse document."""

    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(
        ..., description="The name of the warehouse (e.g., 'Main Distribution Center')."
    )
    location: Location = Field(
        ..., description="Geographical location of the warehouse."
    )

    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class WarehouseCreate(BaseModel):
    """Model for creating a new Warehouse."""

    name: str
    location: Location


class WarehouseUpdate(BaseModel):
    """Model for partial updates to an existing Warehouse."""

    name: Optional[str] = None
    location: Optional[Location] = None


class WarehouseResponse(BaseModel):
    """Simplified response model for Warehouse data."""

    id: str
    name: str
    location: Location
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}
