# app/schemas/hierarchy.py
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from app.models.hierarchy import AdministrativeUnitType


class AdminUnitBase(BaseModel):
    name: str
    type: AdministrativeUnitType
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdminUnitCreate(AdminUnitBase):
    pass


class AdminUnitUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None  # Allow changing parent_id or setting to None
    metadata: Optional[Dict[str, Any]] = None


class AdminUnitPublic(AdminUnitBase):
    id: PydanticObjectId = Field(..., alias="_id")

    class Config:
        populate_by_name = True
        json_encoders = {PydanticObjectId: str}
