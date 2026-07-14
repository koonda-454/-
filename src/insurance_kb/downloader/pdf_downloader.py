"""httpx-based PDF downloader.

Implements :class:`~insurance_kb.downloader.base_downloader.BaseDownloader`.
Deliberately decoupled from any specific crawler: it only needs a
:class:`~insurance_kb.models.product.Product` with a populated
``source_url`` pointing at a PDF, plus a target company/category naming
scheme. This keeps collection (finding *what* to download) and download
(actually fetching bytes) as two independently testable concerns, per the
Phase 2 pilot requirement to separate Crawler and Downloader.

Change detection strategy (cheapest-first):
1. If a previous ``metadata.json`` exists for this exact target file and
   has an ``etag``/``last_modified``, issue a conditional GET
   (``If-None-Match`` / ``If-Modified-Since``). A ``304 Not Modified``
   response means "skip" without transferring the PDF body at all.
2. Otherwise (no conditional headers available, or the server ignores
   them), download the full body and compare its SHA-256 against the
   previous metadata's ``sha256``. Identical hashes also mean "skip" —
   the freshly downloaded bytes are discarded rather than rewritten.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import httpx

from insurance_kb.core.exceptions import DownloadException, StorageException, ValidationException
from insurance_kb.core.logger import get_logger
from insurance_kb.downloader.base_downloader import BaseDownloader
from insurance_kb.models.pdf_document_metadata import PdfDocumentMetadata
from insurance_kb.models.product import Product
from insurance_kb.models.product_version import ProductVersion
from insurance_kb.utils import robots_util
from insurance_kb.utils.date_util import to_date_string
from insurance_kb.utils.file_util import ensure_dir, read_json, safe_filename, write_json
from insurance_kb.utils.hash_util import compute_bytes_hash

logger = get_logger(__name__)

DEFAULT_USER_AGENT = "InsuranceKB-Bot/0.1 (+contact: tbd@example.com)"
CRAWLER_VERSION = "1.0.0"


class PdfDownloader(BaseDownloader):
    """Downloads a single product's PDF over HTTP(S) using ``httpx``.

    Args:
        raw_root: Root directory PDFs are stored under
            (``data/raw/{company_folder}/{category}/...``).
        company_folder: Folder name for the owning company, e.g. ``"SamsungFire"``.
        company_display_name: Human-readable company name for metadata/filenames,
            e.g. ``"삼성화재"``.
        document_label: Document type label used in filenames, per the
            required naming convention (``"상품요약서"``).
        user_agent: User agent string sent with every request, and used
            for robots.txt permission checks.
        crawler_version: Version tag recorded in every metadata.json for traceability.
        http_client: Optional pre-configured ``httpx.Client`` (primarily
            for dependency injection in tests). A default client is
            created if not provided.
        timeout_seconds: Per-request HTTP timeout.
    """

    def __init__(
        self,
        raw_root: str | Path = "data/raw",
        company_folder: str = "SamsungFire",
        company_display_name: str = "삼성화재",
        document_label: str = "상품요약서",
        user_agent: str = DEFAULT_USER_AGENT,
        crawler_version: str = CRAWLER_VERSION,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._raw_root = Path(raw_root)
        self._company_folder = company_folder
        self._company_display_name = company_display_name
        self._document_label = document_label
        self._user_agent = user_agent
        self._crawler_version = crawler_version
        self._client = http_client or httpx.Client(
            headers={"User-Agent": user_agent}, follow_redirects=True
        )
        self._timeout_seconds = timeout_seconds

    def _target_paths(self, product: Product) -> tuple[Path, Path]:
        """Compute the PDF and metadata.json paths for a product.

        Filename convention: ``삼성화재_{상품명}_상품요약서_{YYYYMMDD}.pdf``.
        The date component uses ``product.publish_date`` when available,
        otherwise falls back to today's date (download date).
        """
        date_str = to_date_string(product.publish_date or datetime.utcnow())
        base_name = safe_filename(
            f"{self._company_display_name}_{product.product_name}_{self._document_label}_{date_str}"
        )
        category_dir = self._raw_root / self._company_folder / safe_filename(product.category)
        pdf_path = category_dir / f"{base_name}.pdf"
        metadata_path = category_dir / f"{base_name}.metadata.json"
        return pdf_path, metadata_path

    def _load_previous_metadata(self, metadata_path: Path) -> PdfDocumentMetadata | None:
        if not metadata_path.exists():
            return None
        try:
            raw = read_json(metadata_path)
            return PdfDocumentMetadata(**raw)
        except Exception as exc:  # noqa: BLE001 - corrupt/legacy metadata should not crash the run
            logger.warning(
                f"Could not parse previous metadata, ignoring it: {metadata_path} ({exc})"
            )
            return None

    def download(self, product: Product) -> ProductVersion:
        """See :meth:`BaseDownloader.download`."""
        if not product.source_url:
            raise DownloadException("PDF 없음: product.source_url이 비어 있습니다", context={
                "product_id": product.product_id
            })

        source_url = str(product.source_url)

        if not robots_util.is_allowed(source_url, self._user_agent):
            raise DownloadException(
                "robots.txt 정책에 의해 다운로드가 차단되었습니다",
                context={"product_id": product.product_id, "source_url": source_url},
            )

        pdf_path, metadata_path = self._target_paths(product)
        previous = self._load_previous_metadata(metadata_path)

        logger.info(f"다운로드 시작: {product.product_name} ({source_url})")

        conditional_headers: dict[str, str] = {}
        if previous is not None:
            if previous.etag:
                conditional_headers["If-None-Match"] = previous.etag
            if previous.last_modified:
                conditional_headers["If-Modified-Since"] = previous.last_modified

        start_time = time.monotonic()
        try:
            response = self._client.get(
                source_url, headers=conditional_headers, timeout=self._timeout_seconds
            )
        except httpx.HTTPError as exc:
            raise DownloadException(
                "PDF 다운로드 중 네트워크 오류가 발생했습니다",
                context={
                    "product_id": product.product_id,
                    "source_url": source_url,
                    "error": str(exc),
                },
            ) from exc
        duration = time.monotonic() - start_time

        if response.status_code == 304 and previous is not None:
            logger.info(f"Skip (변경 없음, 304 Not Modified): {product.product_name}")
            return self._version_from_metadata(product, previous, pdf_path, metadata_path)

        if response.status_code != 200:
            raise DownloadException(
                "PDF 다운로드에 실패했습니다 (예상치 못한 HTTP 상태)",
                context={
                    "product_id": product.product_id,
                    "source_url": source_url,
                    "http_status": response.status_code,
                },
            )

        content = response.content
        sha256 = compute_bytes_hash(content)

        if previous is not None and previous.sha256 == sha256:
            logger.info(f"Skip (동일 SHA256, 내용 변경 없음): {product.product_name}")
            return self._version_from_metadata(product, previous, pdf_path, metadata_path)

        try:
            ensure_dir(pdf_path.parent)
            pdf_path.write_bytes(content)
        except OSError as exc:
            raise DownloadException(
                "다운로드한 PDF 파일 저장에 실패했습니다",
                context={
                    "product_id": product.product_id,
                    "pdf_path": str(pdf_path),
                    "error": str(exc),
                },
            ) from exc

        try:
            metadata = PdfDocumentMetadata(
                company=self._company_display_name,
                product=product.product_name,
                category=product.category,
                publish_date=to_date_string(product.publish_date) if product.publish_date else None,
                source_url=source_url,
                sha256=sha256,
                crawler_version=self._crawler_version,
                http_status=response.status_code,
                content_length=(
                    int(response.headers["content-length"])
                    if "content-length" in response.headers
                    else len(content)
                ),
                mime_type=response.headers.get("content-type"),
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
                download_duration_seconds=duration,
                file_path=str(pdf_path),
            )
        except Exception as exc:  # noqa: BLE001 - pydantic ValidationError or similar
            raise ValidationException(
                "Metadata 생성에 실패했습니다", context={"product_id": product.product_id, "error": str(exc)}
            ) from exc

        try:
            write_json(metadata_path, metadata.model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001
            raise StorageException(
                "metadata.json 저장에 실패했습니다",
                context={"product_id": product.product_id, "metadata_path": str(metadata_path)},
            ) from exc

        logger.info(f"다운로드 완료: {product.product_name} -> {pdf_path}")

        return ProductVersion(
            version_id=f"{product.product_id}_v{product.version}",
            product_id=product.product_id,
            version_no=product.version,
            file_hash=sha256,
            publish_date=product.publish_date,
            pdf_path=str(pdf_path),
            json_path=str(metadata_path),
            is_latest=True,
        )

    def _version_from_metadata(
        self,
        product: Product,
        metadata: PdfDocumentMetadata,
        pdf_path: Path,
        metadata_path: Path,
    ) -> ProductVersion:
        """Build a ProductVersion from a previously-saved metadata.json,
        used when a download is skipped because nothing changed."""
        return ProductVersion(
            version_id=f"{product.product_id}_v{product.version}",
            product_id=product.product_id,
            version_no=product.version,
            file_hash=metadata.sha256,
            publish_date=product.publish_date,
            pdf_path=str(pdf_path),
            json_path=str(metadata_path),
            is_latest=True,
        )
