# app/models/hierarchy.py
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import Field
from beanie import Document


# --- Administrative Unit Types (Customizable) ---
class AdministrativeUnitType(str, Enum):
    """Defines the types of administrative units, matching the hierarchy levels."""

    COUNTRY = "country"
    STATE = "state"
    DISTRICT = "district"
    CITY = "city"
    TALUKA = "taluka"
    MOHALLA = "mohalla"


# --- AdminUnit Model ---
class AdminUnit(Document):
    """
    Represents an administrative unit in the hierarchical structure.
    """

    name: str = Field(unique=True, index=True)
    type: AdministrativeUnitType
    parent_id: Optional[str] = Field(
        default=None, index=True
    )  # ID of the parent AdminUnit

    # Optional metadata, e.g., population, area, specific codes
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "admin_units"
