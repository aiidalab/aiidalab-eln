import ipywidgets as ipw
from . import ElnConnector

class OpenbisElnConnector(ElnConnector):
    def __init__(self, **kwargs):
        
        output = ipw.HTML("I am the OpenBIS connector.") 
        super().__init__(children=[output], **kwargs)
        
  
