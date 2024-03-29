"""
(c) 2024 Alberto Morón Hernández
"""

import logging

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture(scope="session", autouse=True)
def LOG():
    return logging.getLogger(__name__)


async def get_aclient(app: FastAPI, url: str):
    return AsyncClient(transport=ASGITransport(app=app), base_url=url)


@pytest_asyncio.fixture
async def api_client():
    from depositduck.main import apiapp

    api_client = await get_aclient(apiapp, "http://apitest")
    async with api_client as client:
        yield client


@pytest_asyncio.fixture
async def web_client():
    from depositduck.main import webapp

    web_client = await get_aclient(webapp, "http://webtest")
    async with web_client as client:
        yield client
