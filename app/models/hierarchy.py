from beanie import Document, Link
from pydantic import Field
from typing import Optional


class HierarchyLevel(Document):
    name: str = Field(..., description="e.g., 'Country', 'State', 'District'")
    level_order: int = Field(
        ...,
        description="Numerical order of the level (e.g., 0 for Country, 1 for State)",
    )
    is_active: bool = True

    class Settings:
        name = "hierarchy_levels"


class AdministrativeUnit(Document):
    name: str = Field(..., description="e.g., 'India', 'Jharkhand', 'Madhupur'")
    level: Link[HierarchyLevel]  # Link to the HierarchyLevel document
    parent_unit: Optional[Link["AdministrativeUnit"]] = (
        None  # Self-referencing link for hierarchy
    )
    description: Optional[str] = None
    is_active: bool = True

    class Settings:
        name = "administrative_units"
