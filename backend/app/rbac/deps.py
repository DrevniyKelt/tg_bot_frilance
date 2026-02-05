from __future__ import annotations

from fastapi import Depends, HTTPException, status


def require_permission(permission: str):
    async def _checker():
        # TODO: attach user to request context, check RBAC in DB
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": f"Missing permission: {permission}",
            },
        )

    return _checker
