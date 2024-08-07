"""
UserManager and related dependables using fastapi-users.
https://fastapi-users.github.io/fastapi-users/13.0/configuration/user-manager/

(c) 2024 Alberto Morón Hernández
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Optional

from fastapi import Depends, Request, Response
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.authentication.strategy.db import AccessTokenDatabase, DatabaseStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import InvalidPasswordException
from fastapi_users_db_sqlmodel.access_token import SQLModelAccessTokenDatabaseAsync
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from depositduck.auth import send_verification_email
from depositduck.dependables import (
    AYieldFixture,
    db_engine,
    get_logger,
    get_settings,
)
from depositduck.models.auth import UserCreate
from depositduck.models.sql.auth import AccessToken, User

settings = get_settings()
LOG = get_logger()
ACCESS_TOKEN_LIFETIME_IN_SECONDS = 3600


class InvalidPasswordReason(str, Enum):
    PASSWORD_TOO_SHORT = "PASSWORD_TOO_SHORT"  # nosec B105
    CONFIRM_PASSWORD_DOES_NOT_MATCH = "CONFIRM_PASSWORD_DOES_NOT_MATCH"  # nosec B105


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    # reset & verification token lifetimes default to 3600 seconds
    reset_password_token_secret = settings.app_secret
    verification_token_secret = settings.app_secret

    async def validate_password(  # type: ignore
        self,
        password: str,
        user: Optional[User] = None,
    ) -> None:
        # TODO: stub - validate length & check isn't common password
        if len(password) < 8:
            raise InvalidPasswordException(
                reason=InvalidPasswordReason.PASSWORD_TOO_SHORT
            )
        # TODO: if user is None, treat as check for new password.
        # TODO: if user is not None, check the password is that of the user:
        # if self.password_helper.hash(password) == user.hashed_password: ...

    async def create(self, user_create: UserCreate, **kwargs: Any) -> User:  # type: ignore
        if (
            user_create.password is not None
            and user_create.password != user_create.confirm_password
        ):
            raise InvalidPasswordException(
                reason=InvalidPasswordReason.CONFIRM_PASSWORD_DOES_NOT_MATCH
            )

        return await super().create(user_create, **kwargs)

    async def on_after_register(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        # TODO: stub - save event for analytics
        LOG.debug(f"{user} registered")

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ):
        # TODO: stub - save event for analytics
        LOG.debug(f"{user} logged in")

    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ):
        await send_verification_email(user, token)

    async def on_after_verify(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        now = datetime.now(timezone.utc)
        await self.user_db.update(user, {"verified_at": now})

    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ):
        # TODO: stub - rate limit & enqueue reset email
        LOG.debug(f"{user} requested a password reset - token: {token}")

    async def on_after_reset_password(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        LOG.info(f"{user} has reset their password")


async def _get_auth_db_session() -> AYieldFixture[AsyncSession]:
    """
    A SQLAlchemy sessionmaker to be used only with fastapi-users related dependables.
    This is necessary because fastapi-users' internal methods call session.commit(),
    which is incompatible with using a session context manager (session.begin()).
    See https://github.com/sqlalchemy/sqlalchemy/discussions/9114
    """
    # `expire_on_commit=False` allows accessing object attributes
    # even after a call to `AsyncSession.commit()`.
    db_session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with db_session_factory() as session:
        yield session


async def get_user_db(db_session: Annotated[AsyncSession, Depends(_get_auth_db_session)]):
    yield SQLAlchemyUserDatabase(db_session, User)


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)],
):
    yield UserManager(user_db)


async def get_access_token_db(
    db_session: Annotated[AsyncSession, Depends(_get_auth_db_session)],
):
    yield SQLModelAccessTokenDatabaseAsync(db_session, AccessToken)


def get_database_strategy(
    access_token_db: Annotated[
        AccessTokenDatabase[AccessToken], Depends(get_access_token_db)
    ],
) -> DatabaseStrategy:
    return DatabaseStrategy(
        access_token_db, lifetime_seconds=ACCESS_TOKEN_LIFETIME_IN_SECONDS
    )
