from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, confloat


class UserInToken(BaseModel):
    sub: str = Field(..., description="The user ID of the authenticated user (subject).")
    role: str = Field(..., description="The role of the authenticated user (e.g., 'user', 'admin').")


class Item(BaseModel):
    """Base model for an Item document in inventory."""
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., description="Descriptive name of the material (e.g., 'Cement Bag - Type II').")
    description: Optional[str] = Field(None, description="Detailed description of the item.")
    unit: str = Field(..., description="The unit of measure (e.g., 'bags', 'meters', 'pieces').")
    
    quantity_on_hand: confloat(ge=0) = Field(..., description="Current stock quantity.")
    min_quantity: confloat(ge=0) = Field(0, description="Minimum reorder quantity.")
    
    category_id: Optional[str] = Field(None, description="ID linking to a material category.")
    warehouse_id: Optional[str] = Field(None, description="ID linking to the storage warehouse location.")
    
    is_active: bool = Field(True, description="Whether the item is currently active in the inventory.")
    
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class ItemCreate(BaseModel):
    """Model for creating a new Item."""
    name: str
    description: Optional[str] = None
    unit: str
    quantity_on_hand: confloat(ge=0)
    min_quantity: confloat(ge=0) = 0
    category_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    is_active: bool = True


class ItemUpdate(BaseModel):
    """Model for partial updates to an existing Item."""
    name: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    quantity_on_hand: Optional[confloat(ge=0)] = None
    min_quantity: Optional[confloat(ge=0)] = None
    category_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    is_active: Optional[bool] = None


class ItemResponse(BaseModel):
    """Simplified response model for Item data sent back to the client."""
    id: str
    name: str
    unit: str
    quantity_on_hand: float
    min_quantity: float
    is_active: bool
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}