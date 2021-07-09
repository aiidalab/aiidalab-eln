# -*- coding: utf-8 -*-
import ipywidgets as ipw

from ..base_connector import ElnConnector


class OpenbisElnConnector(ElnConnector):
    def __init__(self, **kwargs):

        output = ipw.HTML("I am the OpenBIS connector.")
        super().__init__(children=[output], **kwargs)
