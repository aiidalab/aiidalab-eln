"""Module that defines the base class for ELN connetors."""
import ipywidgets as ipw
import traitlets


class ElnConnector(ipw.VBox):
    """Base class for the ELN connectors."""

    aiidalab_instance = traitlets.Unicode()
    eln_instance = traitlets.Unicode()
    eln_type = traitlets.Unicode()

    def __init__(self, **kwargs):
        """Connect to an ELN

        Args:
            eln_instance (str): URL which points to the ELN instance.
            eln_type (str): ELN type, e.g. "cheminfo" or "openbis".
        """
        super().__init__(**kwargs)

    def connect(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'connect' method"
        )

    @property
    def is_connected(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'is_connected' method"
        )

    def export_data(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'export_data' method"
        )

    def import_data(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'import_data' method"
        )

    def get_config(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'get_config' method"
        )
