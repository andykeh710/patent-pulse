from enum import StrEnum


class PatentOffice(StrEnum):
    USPTO = "USPTO"
    EPO = "EPO"
    WIPO = "WIPO"
    JPO = "JPO"
    KIPO = "KIPO"
    CNIPA = "CNIPA"


class LegalStatus(StrEnum):
    PUBLISHED = "PUBLISHED"
    GRANTED = "GRANTED"
    LAPSED = "LAPSED"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"
    PENDING = "PENDING"


class MaintenanceStatus(StrEnum):
    CURRENT = "CURRENT"
    GRACE_PERIOD = "GRACE_PERIOD"
    LAPSED = "LAPSED"
    UNKNOWN = "UNKNOWN"
