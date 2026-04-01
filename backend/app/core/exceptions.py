class PatentPulseError(Exception):
    """Base exception for Patent Pulse."""

    pass


class IngestionError(PatentPulseError):
    """Error during patent data ingestion."""

    pass


class TransientIngestionError(IngestionError):
    """Transient error that should trigger retry."""

    pass


class NormalizationError(PatentPulseError):
    """Error normalizing patent data to internal schema."""

    pass


class SummarizationError(PatentPulseError):
    """Error generating AI summary."""

    pass


class ScoringError(PatentPulseError):
    """Error computing patent interest score."""

    pass
