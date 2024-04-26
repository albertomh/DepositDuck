"""
(c) 2024 Alberto Morón Hernández
"""

from unittest.mock import Mock

import pytest
from fastapi import status

from depositduck.middleware import FRONTEND_MUST_BE_LOGGED_OUT_PATHS, current_active_user
from depositduck.models.sql.auth import User


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    FRONTEND_MUST_BE_LOGGED_OUT_PATHS,
)
async def test_unprotected_routes_accept_logged_out_user(web_client_factory, path):
    dependency_overrides = {current_active_user: lambda: None}
    web_client = await web_client_factory(
        settings=None, dependency_overrides=dependency_overrides
    )

    async with web_client as client:
        response = await client.get(path)

    assert response.status_code == status.HTTP_200_OK
    assert response.next_request is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    FRONTEND_MUST_BE_LOGGED_OUT_PATHS,
)
async def test_unprotected_routes_redirect_logged_in_user(web_client_factory, path):
    dependency_overrides = {current_active_user: lambda: Mock(spec=User)}
    web_client = await web_client_factory(
        settings=None, dependency_overrides=dependency_overrides
    )

    async with web_client as client:
        response = await client.get(path)

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.next_request.url.path == "/"


@pytest.mark.asyncio
async def test_protected_routes_accept_logged_out_user(web_client_factory):
    dependency_overrides = {current_active_user: lambda: Mock(spec=User)}
    web_client = await web_client_factory(
        settings=None, dependency_overrides=dependency_overrides
    )

    async with web_client as client:
        response = await client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.next_request is None


@pytest.mark.asyncio
async def test_protected_routes_redirect_logged_out_user(web_client_factory):
    dependency_overrides = {current_active_user: lambda: None}
    web_client = await web_client_factory(
        settings=None, dependency_overrides=dependency_overrides
    )

    async with web_client as client:
        response = await client.get("/")

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.next_request.url.path == "/login/"
