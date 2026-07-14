"""Domain model for the per-PDF ``metadata.json`` sidecar file produced by
document downloaders (e.g. :class:`~insurance_kb.downloader.pdf_downloader.PdfDownloader`).

This is intentionally a *separate* model from
:class:`~insurance_kb.models.metadata.Metadata` (which represents a whole
pipeline *run's* summary/log, per design doc section 10 / Phase 1). This
model instead represents one downloaded file's own metadata, as specified
for the Samsung Fire pilot (Phase 2): company/product/category/dates plus
HTTP-transport-level facts (status, content-length, mime type, etag,
last-modified, download duration) and a crawler version tag for
traceability. Adding this as a new file keeps the Phase 1 Architecture
Freeze intact — no existing Phase 1 model is modified.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PdfDocumentMetadata(BaseModel):
    """Metadata describing a single downloaded PDF document.

    Serialized as ``metadata.json`` alongside the PDF, per the storage
    layout ``data/raw/{Company}/{category}/``.

    Attributes:
        company: Insurance company display name, e.g. ``"삼성화재"``.
        product: Product name as discovered by the crawler.
        category: Product category (folder-level granularity, may be a
            top-level category or a more specific sub-category if the
            source site exposes one — see design note in
            :mod:`insurance_kb.crawlers.samsung_fire_crawler`).
        publish_date: Sale/publish date as reported by the source site,
            if available.
        download_date: Timestamp the file was downloaded.
        source_url: The exact URL the PDF was downloaded from.
        sha256: SHA-256 hex digest of the downloaded file content.
        crawler_version: Version tag of the crawler implementation that
            produced this metadata, for traceability across crawler code
            changes over time.
        http_status: HTTP status code returned by the download request.
        content_length: Value of the ``Content-Length`` response header,
            in bytes, if present.
        mime_type: Value of the response ``Content-Type`` header.
        etag: Value of the response ``ETag`` header, if present. Useful as
            an additional, cheaper change-detection signal alongside sha256.
        last_modified: Value of the response ``Last-Modified`` header, if present.
        download_duration_seconds: Wall-clock time the download took.
        file_path: Path to the saved PDF file on local storage.
    """

    company: str = Field(..., description="Insurance company display name.")
    product: str = Field(..., description="Product name as discovered by the crawler.")
    category: str = Field(..., description="Product category (folder-level granularity).")
    publish_date: str | None = Field(default=None, description="Sale/publish date, if available.")
    download_date: datetime = Field(default_factory=datetime.utcnow)
    source_url: str = Field(..., description="Exact URL the PDF was downloaded from.")
    sha256: str = Field(..., description="SHA-256 hex digest of the downloaded file content.")

    crawler_version: str = Field(..., description="Version tag of the crawler implementation.")
    http_status: int = Field(..., description="HTTP status code returned by the download request.")
    content_length: int | None = Field(default=None, description="Content-Length header, in bytes.")
    mime_type: str | None = Field(default=None, description="Content-Type response header value.")
    etag: str | None = Field(default=None, description="ETag response header value, if present.")
    last_modified: str | None = Field(
        default=None, description="Last-Modified response header value, if present."
    )
    download_duration_seconds: float = Field(..., ge=0.0, description="Wall-clock download time.")
    file_path: str = Field(..., description="Path to the saved PDF file on local storage.")
