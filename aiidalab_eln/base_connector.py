# -*- coding: utf-8 -*-
import ipywidgets as ipw
import traitlets


class ElnConnector(ipw.VBox):

    eln_instance = traitlets.Unicode()
    eln_type = traitlets.Unicode()

    def __init__(self, **kwargs):
        """Connect to an ELN

        Args:
            eln_instance (str): URL which points to the eln instance.
            user (str): ELN user.
            token (str): ELN access token (or user password).
            eln_type (str): ELN type, e.g. "cheminfo".
        """
        super().__init__(**kwargs)

    def connect(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'connect' method"
        )

    def is_connected(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'is_connected' method"
        )

    def send_data_object(self, data_object):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'send_data_object' method"
        )

    def get_config(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement the 'get_config' method"
        )
