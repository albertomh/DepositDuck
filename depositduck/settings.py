"""
Application configuration. Driven by environment variables.
Populate env vars by sourcing a .env file, which will be
picked up when the Settings object is instantiated.

Don't instantiate Settings directly from this module.
Use the `get_settings` dependable instead.

NB. `frozen=True` makes the Settings and nested objects hashable.
Making them hashable is needed so that dependables which require
a Settings object can be decorated with @lru_cache.

(c) 2024 Alberto Morón Hernández
"""

from pydantic import PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from depositduck.utils import is_valid_fernet_key


class Settings(BaseSettings):
    app_name: str = "DepositDuck"
    app_secret: str
    app_origin: str
    # controls FastAPI's debug mode and whether or not to show `/docs`.
    debug: bool = False
    # set during end-to-end tests to run as close to production (ie. debug=false)
    # but still modify some behaviours (eg. cookies are not secure when e2e=true).
    e2e: bool = False

    db_user: str
    db_password: str
    db_name: str
    db_host: str
    db_port: PositiveInt = 5432

    smtp_server: str
    smtp_port: PositiveInt = 465  # for SSL
    smtp_use_ssl: bool = True
    smtp_sender_address: str
    smtp_password: str

    drallam_origin: str = "http://0.0.0.0:11434"
    drallam_embeddings_model: str = "nomic-embed-text:v1.5"

    static_origin: str
    speculum_release: str

    @field_validator("app_secret")
    @classmethod
    def app_secret_is_valid_fernet_key(cls, value: str) -> str:
        try:
            is_valid_fernet_key(value)
        except (ValueError, TypeError) as e:
            raise e.__class__("setting APP_SECRET is not valid Fernet key") from e
        return value

    @field_validator("app_origin", "static_origin")
    @classmethod
    def remove_origins_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    model_config = SettingsConfigDict(env_nested_delimiter="__", frozen=True)
