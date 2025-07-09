# app/models/user.py
from enum import Enum
from typing import List, Optional, Any
from datetime import datetime
from pydantic import Field, EmailStr, ConfigDict, BaseModel  # Import BaseModel
from beanie import Document, PydanticObjectId


# --- UserRole Enum (Simplified) ---
class UserRole(str, Enum):
    """Defines the core roles a user can have within the system based on capabilities."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    GENERAL_READ_ONLY = "general_read_only"


# --- Audit Log Entry Model ---
class AuditLogEntry(BaseModel):  # <--- CHANGE THIS LINE: Inherit from BaseModel
    """
    Represents an entry in a user's audit log for profile changes.
    """

    changed_by_user_id: PydanticObjectId
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    field_name: str
    old_value: Any
    new_value: Any

    class Config:  # <--- Optional: Add Pydantic v1 Config for JSON encoding, if needed for this specific model
        json_encoders = {PydanticObjectId: str}
        # If you were on Pydantic v2 exclusively, this would be model_config
        # model_config = ConfigDict(json_encoders={PydanticObjectId: str})
        # But for simple PydanticObjectId to str, it usually handles it automatically on BaseModel.
        # It's safer to include for PydanticObjectId if you want explicit string conversion.
        arbitrary_types_allowed = True  # Keep this if 'Any' type causes issues, but often not needed for BaseModel


# --- User Model ---
class User(Document):
    # id: Optional[PydanticObjectId] = Field(
    #     alias="_id", default_factory=PydanticObjectId
    # )
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr = Field(unique=True)
    phone_number: Optional[str] = None  # Contact info for audit log concern
    hashed_password: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    profile_picture_url: Optional[str] = None
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )  # Make sure this is present and works
    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )  # Make sure this is present and works

    # This field defines the administrative scope for ADMINs and the location for USERs
    # A Super Admin typically wouldn't have this, or it would be []
    # An Admin would have the IDs of the units they manage (e.g., a state ID, or a district ID)
    # A User would have the ID of their specific unit (e.g., a Mohalla ID, or a District ID if their task is district-wide)
    associated_administrative_units: List[str] = Field(default_factory=list)

    # Stores the hierarchy levels this user is associated with (e.g., ["Country", "State", "District"])
    # This is descriptive and can be derived from associated_administrative_units
    associated_hierarchy_levels: List[str] = Field(default_factory=list)

    # Audit log for profile changes (specifically contact info)
    audit_log: List[AuditLogEntry] = Field(default_factory=list)

    # We can likely remove arbitrary_types_allowed=True from User model's ConfigDict
    # because AuditLogEntry is now a BaseModel, which Pydantic knows how to handle.
    # However, it doesn't hurt to keep it if you have other arbitrary types.
    # For now, let's keep it just in case, or you can try removing it after this fix.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Settings:
        name = "users"  # MongoDB collection name
