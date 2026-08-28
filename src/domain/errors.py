"""Domain validation errors.

All domain validation failures raise :class:`DomainValidationError` (or a
subclass) so that catalog loaders can translate them into explicit,
non-silent configuration errors.
"""


class DomainValidationError(ValueError):
    """A multistore domain configuration value is invalid."""


class CatalogError(DomainValidationError):
    """A store catalog could not be built from the supplied configuration."""


class CredentialResolutionError(CatalogError):
    """A referenced credential could not be resolved safely."""