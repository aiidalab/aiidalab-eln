"""Provide an ELN connector."""
from aiida_nanotech_empa.version import __version__

from .cheminfo import CheminfoElnConnector


def get_eln_connector(eln_type: str = "cheminfo"):
    """Provide ELN connector of a selected type."""
    if eln_type == "cheminfo":
        return CheminfoElnConnector
    raise NotImplementedError(
        f"""Unexpected error. The ELN connector of type '{eln_type}'
        is not implemented. Please report this to the
        <a href="https://github.com/aiidalab/aiidalab-eln/issues/new" target="_blank">
        issue tracker </a>."""
    )


__all__ = [
    "__version__",
]
