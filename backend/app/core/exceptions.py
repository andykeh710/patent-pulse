class InventionIndex8Error(Exception):
    """Base exception for Invention Index 8."""

    pass


class IngestionError(InventionIndex8Error):
    """Error during patent data ingestion."""

    pass


class TransientIngestionError(IngestionError):
    """Transient error that should trigger retry."""

    pass


class NormalizationError(InventionIndex8Error):
    """Error normalizing patent data to internal schema."""

    pass


class SummarizationError(InventionIndex8Error):
    """Error generating AI summary."""

    pass


class ScoringError(InventionIndex8Error):
    """Error computing patent interest score."""

    pass
