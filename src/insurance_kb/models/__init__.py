"""Pydantic domain models used throughout the platform.

Every pipeline stage communicates using the domain models defined here
instead of raw dictionaries, so that data shape is validated at each
boundary and downstream code can rely on typed attribute access.
"""

from insurance_kb.models.canonical_product import CanonicalFieldValue, CanonicalProduct
from insurance_kb.models.chunk import Chunk, ChunkSource
from insurance_kb.models.company import Company
from insurance_kb.models.export_package import ExportPackage, ExportTarget
from insurance_kb.models.faq import FAQ, FAQAudience
from insurance_kb.models.knowledge_artifact import ArtifactType, KnowledgeArtifact, ReviewStatus
from insurance_kb.models.metadata import Metadata
from insurance_kb.models.pdf_analysis import PdfAnalysisResult
from insurance_kb.models.pdf_document_metadata import PdfDocumentMetadata
from insurance_kb.models.product import Product
from insurance_kb.models.product_version import ProductVersion
from insurance_kb.models.qa_report import QaReport

__all__ = [
    "Company",
    "Product",
    "ProductVersion",
    "CanonicalProduct",
    "CanonicalFieldValue",
    "Metadata",
    "PdfDocumentMetadata",
    "PdfAnalysisResult",
    "QaReport",
    "KnowledgeArtifact",
    "ArtifactType",
    "ReviewStatus",
    "FAQ",
    "FAQAudience",
    "Chunk",
    "ChunkSource",
    "ExportPackage",
    "ExportTarget",
]
