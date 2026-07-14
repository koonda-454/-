"""Domain model representing an insurance company."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Company(BaseModel):
    """A single insurance company that this platform collects data from.

    Attributes:
        company_id: Stable internal identifier (e.g. ``"samsung_fire"``).
        name: Official display name (e.g. ``"삼성화재"``).
        name_en: English name, if available.
        homepage_url: Official homepage URL.
        disclosure_url: URL of the product disclosure (공시자료실) section.
        is_active: Whether this company is currently being collected.
    """

    model_config = ConfigDict(frozen=True)

    company_id: str = Field(..., description="Stable internal identifier, e.g. 'samsung_fire'.")
    name: str = Field(..., description="Official Korean display name.")
    name_en: str | None = Field(default=None, description="English display name, if available.")
    homepage_url: HttpUrl | None = Field(default=None, description="Official homepage URL.")
    disclosure_url: HttpUrl | None = Field(
        default=None, description="URL of the product disclosure section."
    )
    is_active: bool = Field(default=True, description="Whether collection is currently enabled.")
