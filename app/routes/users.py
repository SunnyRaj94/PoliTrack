# app/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from beanie import PydanticObjectId

from app.models.user import User, UserRole, AuditLogEntry
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserPublic,
    # UserLogin,
    Token,
    PasswordChange,
    ProfileUpdate,
)
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.dependencies.auth import (
    get_current_user,
    authenticate_user_dependency,
    create_access_token_dependency,
)  # Added create_access_token_dependency
from app.schemas.misc import Message

router = APIRouter()
user_service = UserService()
auth_service = AuthService()


# Dependency to require Super Admin role
def require_super_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins are allowed to perform this action.",
        )
    return current_user


# Dependency to require Admin or Super Admin role
def require_admin_or_super_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins or Super Admins are allowed to perform this action.",
        )
    return current_user


# --- Authentication Endpoints ---


@router.post(
    "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_create: UserCreate,
    current_user: User = Depends(
        require_admin_or_super_admin
    ),  # Only admin/super admin can create users
):
    """
    Register a new user. Only Admins and Super Admins can register new users.
    Super Admins can assign any role. Admins can only assign 'USER' or 'GENERAL_READ_ONLY'.
    """
    if current_user.role == UserRole.ADMIN:
        if user_create.role not in [UserRole.USER, UserRole.GENERAL_READ_ONLY]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only register 'user' or 'general_read_only' roles.",
            )

    existing_user = await user_service.get_user_by_email(user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    new_user = await user_service.create_user(user_create)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )

    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    # CHANGE THIS LINE: Accept 'user' of type 'User'
    user: User = Depends(authenticate_user_dependency),
    create_access_token_func: callable = Depends(
        create_access_token_dependency
    ),  # Renamed to avoid clash if 'create_access_token' is a module-level variable
):
    """
    Authenticate user and return an access token.
    """
    # Use the 'user' object directly
    access_token = create_access_token_func({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's details.
    """
    return current_user


@router.put("/me/password", response_model=Message)
async def change_my_password(
    password_change: PasswordChange, current_user: User = Depends(get_current_user)
):
    """
    Allows a user to change their own password.
    """
    if not auth_service.verify_password(
        password_change.old_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid old password"
        )

    if password_change.old_password == password_change.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as old password",
        )

    hashed_new_password = auth_service.hash_password(password_change.new_password)
    await user_service.update_user(current_user.id, hashed_password=hashed_new_password)

    return {"message": "Password updated successfully"}


@router.put("/me/profile", response_model=UserPublic)
async def update_my_profile(
    profile_update: ProfileUpdate, current_user: User = Depends(get_current_user)
):
    """
    Allows a user to update their own profile information (first_name, last_name, phone_number, profile_picture_url).
    The email cannot be changed via this endpoint.
    """
    # Create an audit log entry before updating sensitive fields if changed
    audit_log_entries = []

    # Check for phone_number change
    if (
        profile_update.phone_number is not None
        and profile_update.phone_number != current_user.phone_number
    ):
        audit_log_entries.append(
            {
                "changed_by_user_id": current_user.id,
                "field_name": "phone_number",
                "old_value": current_user.phone_number,
                "new_value": profile_update.phone_number,
            }
        )

    # You can add more checks for other fields if needed, e.g., role or status changes
    # For now, assuming only phone number for audit log based on previous requirements.

    updated_user_data = profile_update.model_dump(exclude_unset=True)

    # Add audit log entries to the update data if any changes were recorded
    if audit_log_entries:
        # Append the new log entries to the existing audit_log
        # This requires fetching the current audit_log and extending it
        existing_audit_log = current_user.audit_log
        for entry_data in audit_log_entries:
            # Create an AuditLogEntry instance (Pydantic will handle timestamp if default_factory)
            entry = auth_service.AuditLogEntry(**entry_data)
            existing_audit_log.append(entry)

        # Ensure that updated_user_data reflects the full audit_log list
        # This will overwrite the entire audit_log field in the database
        updated_user_data["audit_log"] = existing_audit_log

    updated_user = await user_service.update_user(current_user.id, **updated_user_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )

    return updated_user


# --- Admin-only User Management Endpoints ---


@router.get("/", response_model=List[UserPublic])
async def get_all_users(current_user: User = Depends(require_admin_or_super_admin)):
    """
    Retrieve a list of all users (Admin/Super Admin only).
    Admins can only see 'user' and 'general_read_only' roles. Super Admins see all.
    """
    users = await user_service.get_all_users()

    if current_user.role == UserRole.ADMIN:
        # Admins only see 'user' and 'general_read_only' roles
        users = [
            user
            for user in users
            if user.role in [UserRole.USER, UserRole.GENERAL_READ_ONLY]
        ]

    # --- NEW CRITICAL CHANGE HERE ---
    public_users = []
    for user in users:
        # Use user.model_dump(by_alias=True) to get the dictionary with 'id' instead of '_id'
        # and then pass it to the constructor.
        # Ensure that `id` in UserPublic is aliased to `_id` and is `str`.
        # The json_encoders will handle PydanticObjectId to str for response serialization.
        # For direct instantiation, PydanticObjectId needs to be cast to str.
        user_data = user.model_dump(by_alias=True)
        public_users.append(UserPublic(**user_data))

    return public_users


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_by_id(
    user_id: PydanticObjectId,
    current_user: User = Depends(require_admin_or_super_admin),
):
    """
    Retrieve a single user by ID (Admin/Super Admin only).
    Admins can only see 'user' and 'general_read_only' roles. Super Admins see all.
    """
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if current_user.role == UserRole.ADMIN and user.role not in [
        UserRole.USER,
        UserRole.GENERAL_READ_ONLY,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are not authorized to view this user's details.",
        )

    return user


@router.put("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: PydanticObjectId,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin_or_super_admin),
):
    """
    Update an existing user's details (Admin/Super Admin only).
    Super Admins can update any user's fields, including role.
    Admins can update 'user' or 'general_read_only' roles only (excluding their own role to prevent self-escalation)
    and cannot change roles to ADMIN or SUPER_ADMIN.
    """
    # Fetch the user to be updated to check permissions and existing values
    target_user = await user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    # Permissions check for Admin
    if current_user.role == UserRole.ADMIN:
        # Admin cannot update Super Admin or other Admins
        if (
            target_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
            and target_user.id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins are not authorized to update users with 'admin' or 'super_admin' roles, or other admins.",
            )
        # Admin cannot change roles to ADMIN or SUPER_ADMIN
        if user_update.role and user_update.role in [
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot assign 'admin' or 'super_admin' roles.",
            )
        # Admin can only update users with 'user' or 'general_read_only' roles
        if (
            target_user.role not in [UserRole.USER, UserRole.GENERAL_READ_ONLY]
            and target_user.id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only update users with 'user' or 'general_read_only' roles.",
            )

    # Prepare data for update, excluding fields that should not be changed by certain roles or at all
    update_data = user_update.model_dump(exclude_unset=True)

    # Handle password hashing if provided
    if "password" in update_data:
        update_data["hashed_password"] = auth_service.hash_password(
            update_data.pop("password")
        )

    # Audit logging for sensitive changes (e.g., phone number, roles, activation status)
    audit_log_entries = []

    # Check for phone_number change (if it's allowed for admin to update others)
    if (
        "phone_number" in update_data
        and update_data["phone_number"] != target_user.phone_number
    ):
        audit_log_entries.append(
            {
                "changed_by_user_id": current_user.id,
                "field_name": "phone_number",
                "old_value": target_user.phone_number,
                "new_value": update_data["phone_number"],
            }
        )

    # Check for role change
    if "role" in update_data and update_data["role"] != target_user.role:
        audit_log_entries.append(
            {
                "changed_by_user_id": current_user.id,
                "field_name": "role",
                "old_value": target_user.role.value,  # Store enum value
                "new_value": update_data["role"].value,  # Store enum value
            }
        )

    # Check for is_active status change
    if "is_active" in update_data and update_data["is_active"] != target_user.is_active:
        audit_log_entries.append(
            {
                "changed_by_user_id": current_user.id,
                "field_name": "is_active",
                "old_value": target_user.is_active,
                "new_value": update_data["is_active"],
            }
        )

    # Add new audit log entries to the existing ones
    if audit_log_entries:
        existing_audit_log = target_user.audit_log
        for entry_data in audit_log_entries:
            entry = auth_service.AuditLogEntry(**entry_data)
            existing_audit_log.append(entry)
        update_data["audit_log"] = (
            existing_audit_log  # Ensure the full list is passed for update
        )

    updated_user = await user_service.update_user(user_id, **update_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )

    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: PydanticObjectId,
    current_user: User = Depends(
        require_super_admin
    ),  # Only Super Admin can delete users
):
    """
    Deletes a user by ID (Super Admin only).
    """
    # Prevent a Super Admin from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super Admin cannot delete their own account.",
        )

    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or deletion failed.",
        )
    return


@router.put("/{user_id}/status", response_model=UserPublic)
async def set_user_status(
    user_id: PydanticObjectId,
    is_active: bool,
    current_user: User = Depends(require_admin_or_super_admin),
):
    """
    Activates or deactivates a user (Admin/Super Admin only).
    Admins can only activate/deactivate 'user' or 'general_read_only' roles.
    """
    target_user = await user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    # Prevent a user from changing their own active status (they should use /me/profile or specific change password endpoint)
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own active status via this endpoint.",
        )

    # Admin role specific restrictions
    if current_user.role == UserRole.ADMIN:
        if target_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot change the status of 'admin' or 'super_admin' roles.",
            )
        if target_user.role not in [UserRole.USER, UserRole.GENERAL_READ_ONLY]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only change the status of 'user' or 'general_read_only' roles.",
            )

    # Audit log for status change
    audit_log_entry = {
        "changed_by_user_id": current_user.id,
        "field_name": "is_active",
        "old_value": target_user.is_active,
        "new_value": is_active,
    }

    # Append the new log entry
    existing_audit_log = target_user.audit_log
    entry = auth_service.AuditLogEntry(**audit_log_entry)
    existing_audit_log.append(entry)

    updated_user = await user_service.update_user(
        user_id,
        is_active=is_active,
        audit_log=existing_audit_log,  # Pass the full updated list
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user status.",
        )

    return updated_user


@router.put("/{user_id}/role", response_model=UserPublic)
async def set_user_role(
    user_id: PydanticObjectId,
    role: UserRole,  # Expect a UserRole enum
    current_user: User = Depends(
        require_super_admin
    ),  # Only Super Admin can change roles
):
    """
    Changes a user's role (Super Admin only).
    """
    target_user = await user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    # Prevent a Super Admin from changing their own role (self-demotion/escalation issues)
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super Admin cannot change their own role via this endpoint.",
        )

    # Prevent changing a Super Admin's role to non-Super Admin (unless specific policy dictates)
    # This is a common safety net
    if target_user.role == UserRole.SUPER_ADMIN and role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote a Super Admin directly. Consider a specific demotion process if needed.",
        )

    # Audit log for role change
    audit_log_entry = {
        "changed_by_user_id": current_user.id,
        "field_name": "role",
        "old_value": target_user.role.value,  # Store enum value
        "new_value": role.value,  # Store enum value
    }

    # Append the new log entry
    existing_audit_log = target_user.audit_log
    entry = auth_service.AuditLogEntry(**audit_log_entry)
    existing_audit_log.append(entry)

    updated_user = await user_service.update_user(
        user_id, role=role, audit_log=existing_audit_log  # Pass the full updated list
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role.",
        )

    return updated_user


@router.get("/{user_id}/audit-log", response_model=List[AuditLogEntry])
async def get_user_audit_log(
    user_id: PydanticObjectId,
    current_user: User = Depends(require_admin_or_super_admin),
):
    """
    Retrieves the audit log for a specific user (Admin/Super Admin only).
    Admins can only view audit logs for 'user' or 'general_read_only' roles.
    """
    target_user = await user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    if current_user.role == UserRole.ADMIN and target_user.role not in [
        UserRole.USER,
        UserRole.GENERAL_READ_ONLY,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are not authorized to view audit logs for this user's role.",
        )

    return target_user.audit_log
