"""Common, dependency-light utility functions shared across pipeline stages.

Each submodule here should remain free of business logic and free of
dependencies on other ``insurance_kb`` packages (models, core, etc.) so
that utilities stay easily testable and reusable. Future PDF-specific
utilities (e.g. page counting, table extraction helpers) should be added
as a new ``pdf_util.py`` module in this package.
"""
