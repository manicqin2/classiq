"""
Utility functions for API operations.
"""

from uuid import UUID

from fastapi import HTTPException, status


def validate_uuid(task_id: str) -> str:
    """
    Validate that a string is a valid UUID v4 format.

    Args:
        task_id: String to validate as UUID

    Returns:
        The validated task_id string

    Raises:
        HTTPException: 400 error if task_id is not a valid UUID
    """
    try:
        uuid_obj = UUID(task_id, version=4)
        return str(uuid_obj)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format. Expected UUID v4.",
        )
