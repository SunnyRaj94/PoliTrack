# app/services/admin_unit_service.py
from typing import List, Dict, Optional, Any
from beanie import PydanticObjectId
from app.models.hierarchy import AdminUnit, AdministrativeUnitType

# from app.models.user import (
#     User,
# )  # To check for users in a unit (optional, can be done in route)


class AdminUnitService:
    def __init__(self):
        pass

    async def get_all_admin_units(self) -> List[AdminUnit]:
        """Fetches all administrative units."""
        return await AdminUnit.find_all().to_list()

    async def get_admin_unit_by_id(self, unit_id: str) -> Optional[AdminUnit]:
        """Fetches a single administrative unit by its ID."""
        try:
            return await AdminUnit.get(PydanticObjectId(unit_id))
        except Exception:  # Catch invalid ObjectId format
            return None

    async def get_admin_unit_by_name_and_type(
        self, name: str, unit_type: AdministrativeUnitType
    ) -> Optional[AdminUnit]:
        """Fetches an administrative unit by its name and type."""
        return await AdminUnit.find_one({"name": name, "type": unit_type})

    async def create_admin_unit(
        self,
        name: str,
        unit_type: AdministrativeUnitType,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AdminUnit:
        """Creates a new administrative unit."""
        new_unit = AdminUnit(
            name=name, type=unit_type, parent_id=parent_id, metadata=metadata or {}
        )
        await new_unit.insert()
        return new_unit

    async def update_admin_unit(
        self,
        unit_id: str,
        name: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AdminUnit]:
        """Updates an existing administrative unit."""
        unit = await self.get_admin_unit_by_id(unit_id)
        if not unit:
            return None

        update_data = {}
        if name:
            update_data["name"] = name
        # Only update parent_id if explicitly provided, allowing None to clear it
        if parent_id is not None:
            update_data["parent_id"] = parent_id
        elif (
            "parent_id" in unit.model_fields_set and parent_id is None
        ):  # If explicit None is passed
            update_data["parent_id"] = None

        if metadata is not None:  # Allow clearing metadata
            update_data["metadata"] = metadata

        await unit.set(update_data)
        return unit

    async def delete_admin_unit(self, unit_id: str) -> bool:
        """Deletes an administrative unit."""
        unit = await self.get_admin_unit_by_id(unit_id)
        if not unit:
            return False
        await unit.delete()
        return True

    async def get_children_units(self, parent_id: str) -> List[AdminUnit]:
        """Fetches immediate children units of a given parent ID."""
        return await AdminUnit.find({"parent_id": parent_id}).to_list()

    async def get_descendant_units_ids(self, unit_ids: List[str]) -> List[str]:
        """
        Recursively fetches all descendant unit IDs (including the starting units themselves)
        for a given list of unit IDs. This is crucial for defining the scope of an Admin.
        """
        if not unit_ids:
            return []

        all_descendants = set(unit_ids)  # Include the starting units themselves
        queue = list(unit_ids)

        while queue:
            current_unit_id = queue.pop(0)
            children = await AdminUnit.find({"parent_id": current_unit_id}).to_list()
            for child in children:
                child_id_str = str(child.id)
                if child_id_str not in all_descendants:
                    all_descendants.add(child_id_str)
                    queue.append(child_id_str)

        return list(all_descendants)

    async def get_ancestor_units_ids(self, unit_id: str) -> List[str]:
        """
        Recursively fetches all ancestor unit IDs for a given unit ID, up to the root.
        """
        ancestors = []
        current_unit = await self.get_admin_unit_by_id(unit_id)
        while current_unit and current_unit.parent_id:
            ancestors.append(str(current_unit.parent_id))
            current_unit = await self.get_admin_unit_by_id(str(current_unit.parent_id))
        return ancestors[
            ::-1
        ]  # Return in order from highest ancestor to immediate parent
