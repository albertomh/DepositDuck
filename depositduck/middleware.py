"""
important! Strictly speaking these are FastAPI dependables, but they behave and are used
closer to how middleware behaves and is used. Hence they are referred to as 'middleware'.

(c) 2024 Alberto Morón Hernández
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from depositduck.auth.users import current_active_user
from depositduck.models.sql.auth import User

FRONTEND_MUST_BE_LOGGED_OUT_PATHS = [
    "/login/",
    "/signup/",
]

OPERATIONS_MUST_BE_LOGGED_OUT_PATHS = [
    "/auth/filterProspect/",
    "/auth/unsuitableProspectFunnel/",
    "/auth/request-verification/",
    "/auth/verify/",
    "/auth/authenticate/",
]


async def frontend_auth_middleware(
    request: Request,
    user: Annotated[User, Depends(current_active_user)],
):
    """
    Protect routes based on the authentication status of the user associated
    with the request (if any). Define an allowlist of which routes may be
    accessed without auth. Assume all others require a logged-in user.
    """
    base = str(request.base_url).rstrip("/")
    url = str(request.url)
    path = url[len(base) :]

    if user is None and path not in FRONTEND_MUST_BE_LOGGED_OUT_PATHS:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login/"},
        )
    if user is not None and path in FRONTEND_MUST_BE_LOGGED_OUT_PATHS:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/"}
        )


async def operations_auth_middleware(
    request: Request,
    user: Annotated[User, Depends(current_active_user)],
):
    """
    Protect routes based on the authentication status of the user associated
    with the request (if any). Define an allowlist of which routes may be
    accessed without auth. Assume all others require a logged-in user.
    """
    base = str(request.base_url).rstrip("/")
    url = str(request.url)
    path = url[len(base) :]

    if user is not None and path in OPERATIONS_MUST_BE_LOGGED_OUT_PATHS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if user is not None and path in OPERATIONS_MUST_BE_LOGGED_OUT_PATHS:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/"}
        )