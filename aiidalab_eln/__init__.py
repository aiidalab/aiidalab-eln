# -*- coding: utf-8 -*-
"""Provide an ELN connector."""
from .cheminfo import CheminfoElnConnector


def get_eln_connector(eln_type: str = "cheminfo"):
    """Provide ELN connector of a selected type."""
    if eln_type == "cheminfo":
        return CheminfoElnConnector
    raise Exception(f"The selected ELN connector type ({eln_type}) is not known.")
