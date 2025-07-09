# app/schemas/user.py
from typing import Optional, List
from datetime import datetime
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
)
from beanie import PydanticObjectId
from app.models.user import UserRole, AuditLogEntry


# --- Base User Schemas ---
class UserBase(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    role: UserRole
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False
    profile_picture_url: Optional[str] = None
    associated_administrative_units: Optional[List[str]] = None
    associated_hierarchy_levels: Optional[List[str]] = None

    model_config = ConfigDict(
        extra="ignore"
    )  # Allow extra fields for safety during creation if needed


# --- User Schemas for API Operations ---


class UserCreate(UserBase):
    password: str  # Password required for creation


class UserUpdate(BaseModel):
    # Fields that can be updated. All are optional for updates.
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = (
        None  # Email updates might require separate verification flow
    )
    phone_number: Optional[str] = None
    password: Optional[str] = None  # For changing password directly by admin
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_picture_url: Optional[str] = None
    associated_administrative_units: Optional[List[str]] = None
    associated_hierarchy_levels: Optional[List[str]] = None

    model_config = ConfigDict(
        extra="ignore"
    )  # Allow extra fields for safety during updates


class UserPublic(UserBase):
    id: Optional[PydanticObjectId] = Field(
        alias="_id", default_factory=PydanticObjectId
    )
    created_at: datetime
    updated_at: datetime
    audit_log: List[AuditLogEntry] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={PydanticObjectId: str},
    )


# --- Authentication Schemas ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# --- User Profile Update Schema (for /me/profile) ---
class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture_url: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


# --- Password Change Schema (for /me/password) ---
class PasswordChange(BaseModel):
    old_password: str
    new_password: str
