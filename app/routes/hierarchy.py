# app/routes/hierarchy.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from beanie import PydanticObjectId

# Correct import for AdminUnit (from models)
from app.models.hierarchy import AdminUnit
from app.models.user import User, UserRole

# Correct imports for the Pydantic schemas (from schemas)
from app.schemas.hierarchy import AdminUnitCreate, AdminUnitUpdate, AdminUnitPublic

from app.services.admin_unit_service import AdminUnitService
from app.dependencies.auth import get_current_user

router = APIRouter()
admin_unit_service = AdminUnitService()


# --- Permissions Helper ---
def require_super_admin(current_user: User):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can manage administrative hierarchy.",
        )
    return current_user


# --- Administrative Unit Endpoints ---


@router.post("/", response_model=AdminUnitPublic, status_code=status.HTTP_201_CREATED)
async def create_admin_unit(
    unit_create: AdminUnitCreate, current_user: User = Depends(require_super_admin)
):
    """Creates a new administrative unit (Super Admin only)."""
    # Optional: Add logic to prevent creating a unit if its parent_id doesn't exist
    if unit_create.parent_id:
        parent_unit = await admin_unit_service.get_admin_unit_by_id(
            unit_create.parent_id
        )
        if not parent_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent unit with ID {unit_create.parent_id} not found.",
            )
        # Optional: Add logic to enforce strict hierarchy (e.g., State can only have Country parent)
        # if unit_create.type == AdministrativeUnitType.DISTRICT and parent_unit.type != AdministrativeUnitType.STATE:
        #     raise HTTPException(...)

    new_unit = await admin_unit_service.create_admin_unit(
        name=unit_create.name,
        unit_type=unit_create.type,
        parent_id=unit_create.parent_id,
        metadata=unit_create.metadata,
    )
    if not new_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrative unit creation failed.",
        )
    return new_unit


@router.get("/", response_model=List[AdminUnitPublic])
async def get_all_admin_units(current_user: User = Depends(get_current_user)):
    """
    Retrieves all administrative units.
    Super Admin can see all.
    Admins and Users can see units relevant to their `associated_administrative_units` and their descendants.
    General Read Only can see all.
    """
    if (
        current_user.role == UserRole.SUPER_ADMIN
        or current_user.role == UserRole.GENERAL_READ_ONLY
    ):
        units = await admin_unit_service.get_all_admin_units()
        return [AdminUnitPublic.model_validate(unit) for unit in units]

    if current_user.role in [UserRole.ADMIN, UserRole.USER]:
        if not current_user.associated_administrative_units:
            return []  # If no associated units, no units to show in scope

        # Get all units within the user's scope (their units + all descendants)
        allowed_unit_ids = await admin_unit_service.get_descendant_units_ids(
            current_user.associated_administrative_units
        )

        units = await AdminUnit.find(
            {"_id": {"$in": [PydanticObjectId(uid) for uid in allowed_unit_ids]}}
        ).to_list()
        return [AdminUnitPublic.model_validate(unit) for unit in units]

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to view administrative units.",
    )


@router.get("/{unit_id}", response_model=AdminUnitPublic)
async def get_admin_unit_by_id(
    unit_id: str, current_user: User = Depends(get_current_user)
):
    """Retrieves a single administrative unit by ID."""
    unit = await admin_unit_service.get_admin_unit_by_id(unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrative unit not found.",
        )

    # Check permission based on role and scope
    if (
        current_user.role == UserRole.SUPER_ADMIN
        or current_user.role == UserRole.GENERAL_READ_ONLY
    ):
        return unit

    if current_user.role in [UserRole.ADMIN, UserRole.USER]:
        if not current_user.associated_administrative_units:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this unit.",
            )

        # Check if the requested unit is within the user's scope
        allowed_unit_ids = await admin_unit_service.get_descendant_units_ids(
            current_user.associated_administrative_units
        )
        if unit_id not in allowed_unit_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this unit.",
            )
        return unit

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to view administrative units.",
    )


@router.put("/{unit_id}", response_model=AdminUnitPublic)
async def update_admin_unit(
    unit_id: str,
    unit_update: AdminUnitUpdate,
    current_user: User = Depends(require_super_admin),
):
    """Updates an existing administrative unit (Super Admin only)."""
    updated_unit = await admin_unit_service.update_admin_unit(
        unit_id,
        name=unit_update.name,
        parent_id=unit_update.parent_id,
        metadata=unit_update.metadata,
    )
    if not updated_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrative unit not found or update failed.",
        )
    return updated_unit


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_unit(
    unit_id: str, current_user: User = Depends(require_super_admin)
):
    """Deletes an administrative unit (Super Admin only)."""
    # Optional: Prevent deletion if unit has children or associated users/tasks
    children = await admin_unit_service.get_children_units(unit_id)
    if children:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete administrative unit with active children units.",
        )

    # Check for associated users (this would require querying the User collection)
    # users_in_unit = await User.find({"associated_administrative_units": unit_id}).count()
    # if users_in_unit > 0:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Cannot delete administrative unit with associated users."
    #     )

    success = await admin_unit_service.delete_admin_unit(unit_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrative unit not found.",
        )
    return
