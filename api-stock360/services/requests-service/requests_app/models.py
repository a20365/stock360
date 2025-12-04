from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserInToken(BaseModel):
    sub: str = Field(
        ..., description="The user ID of the authenticated user (subject)."
    )
    role: str = Field(
        ..., description="The role of the authenticated user (e.g., 'user', 'admin')."
    )


class RequestItem(BaseModel):
    """Model for a single construction material item being requested."""

    material_name: str = Field(
        ..., description="Name of the material (e.g., 'Cement Bag', 'Rebar 10mm')."
    )
    quantity: float = Field(
        ..., gt=0, description="The required quantity of the material."
    )
    unit: str = Field(
        ..., description="The unit of measure (e.g., 'bags', 'meters', 'sqft')."
    )
    notes: Optional[str] = Field(
        None, description="Any specific notes about the required item."
    )


class Request(BaseModel):
    """Base model for a Request document, including timestamps and items."""

    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(
        ..., description="The ID of the user who submitted the request."
    )
    request_type: str = Field(
        ..., description="The type of request (now fixed to 'Material')."
    )
    description: str = Field(
        ..., description="Detailed description or project name for the request."
    )
    items: List[RequestItem] = Field(
        ..., description="The list of construction materials requested."
    )
    status: str = Field(
        "pending",
        description="Current status of the request ('pending', 'approved', 'rejected').",
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class RequestCreate(BaseModel):
    """Model for creating a new Request, including the list of items."""

    description: str = Field(
        ..., description="Detailed description or project name for the request."
    )
    items: List[RequestItem] = Field(
        ...,
        min_items=1,
        description="The list of construction materials being requested.",
    )


class RequestUpdate(BaseModel):
    """Model for updating an existing Request."""

    description: Optional[str] = None
    items: Optional[List[RequestItem]] = None
    status: Optional[str] = None


class RequestResponse(BaseModel):
    """Simplified response model for Request data sent back to the client."""

    id: str
    user_id: str
    request_type: str
    items: List[RequestItem]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}
