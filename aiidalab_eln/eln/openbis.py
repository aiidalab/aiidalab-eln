import ipywidgets as ipw
from . import ElnConnector
from cheminfopy import User

class OpenbisElnConnector(ElnConnector):
    def __init__(self, **kwargs):
        
        output = ipw.HTML("I am the OpenBIS connector.") 
        super().__init__(children=[output], **kwargs)
        
    def connect(self, instance, user, token):
        """Connect to the cheminfo ELN."""
        self.session = User(instance=instance, token=token)