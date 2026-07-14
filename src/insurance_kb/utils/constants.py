"""Project-wide constants.

Centralizing constants here avoids magic strings/numbers scattered across
modules and gives a single place to update shared values such as the
canonical field names introduced in the v0.2 design (design doc section 9-2).
"""

from __future__ import annotations

# Canonical schema field keys (design doc section 9-2 / ③ canonical_schema.yaml).
CANONICAL_FIELD_AGE_ELIGIBILITY = "가입연령"
CANONICAL_FIELD_POLICY_TERM = "보험기간"
CANONICAL_FIELD_PAYMENT_TERM = "납입기간"
CANONICAL_FIELD_RENEWAL = "갱신여부"
CANONICAL_FIELD_COVERAGE = "보장내용"
CANONICAL_FIELD_EXCLUSIONS = "면책사항"
CANONICAL_FIELD_REDUCTION = "감액지급"
CANONICAL_FIELD_WAIVER = "납입면제"

CANONICAL_FIELDS: tuple[str, ...] = (
    CANONICAL_FIELD_AGE_ELIGIBILITY,
    CANONICAL_FIELD_POLICY_TERM,
    CANONICAL_FIELD_PAYMENT_TERM,
    CANONICAL_FIELD_RENEWAL,
    CANONICAL_FIELD_COVERAGE,
    CANONICAL_FIELD_EXCLUSIONS,
    CANONICAL_FIELD_REDUCTION,
    CANONICAL_FIELD_WAIVER,
)

# Extraction method labels.
EXTRACTION_METHOD_TEXT = "text"
EXTRACTION_METHOD_OCR = "ocr"

# Default file/directory names.
DEFAULT_CONFIG_ROOT = "config"
DEFAULT_RESOURCES_ROOT = "resources"
DEFAULT_LOG_DIR = "logs"
DEFAULT_DATA_ROOT = "data"

# Hashing.
DEFAULT_HASH_ALGORITHM = "sha256"
DEFAULT_HASH_CHUNK_SIZE_BYTES = 65536

# Retry defaults.
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_MIN_WAIT_SECONDS = 1.0
DEFAULT_RETRY_MAX_WAIT_SECONDS = 10.0
