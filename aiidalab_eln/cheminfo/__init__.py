import traitlets
import ipywidgets as ipw
from ..base_connector import ElnConnector
from cheminfopy import User
from IPython.display import clear_output

class CheminfoElnConnector(ElnConnector):
    access_token = traitlets.Unicode()
    token_url = traitlets.Unicode()
    
    def __init__(self, **kwargs):

        self.session = None

        eln_instance_widget = ipw.Text(
            description="ELN address:",
            value="",
            style={"description_width": "initial"},
        )
        traitlets.link((self, "eln_instance"), (eln_instance_widget, "value"))
        
        token_widget = ipw.Text(
            description="Token:",
            value="",
            placeholder="Press the \"Request token\" button below",
            style={"description_width": "initial"},
        )
        traitlets.link((self, "access_token"), (token_widget, "value"))
        
        token_url_widget = ipw.Text(
            description="Token URL:",
            value="",
            style={"description_width": "initial"},
        )
        traitlets.link((self, "token_url"), (token_url_widget, "value"))        
        
        self.button_clicked = True
        request_token_button = ipw.Button(description="Request token")
        request_token_button.on_click(self.request_token)
        self.output = ipw.Output() 
        super().__init__(children=[eln_instance_widget, token_widget, token_url_widget, request_token_button, self.output], **kwargs)
        
    def connect(self):
        """Connect to the cheminfo ELN."""
        self.session = User(instance=self.eln_instance, token=self.access_token)
    
    def get_config(self):
        return {
            "eln_instance": self.eln_instance,
            "eln_type": self.eln_type,
            "access_token": self.access_token,
            "token_url": self.token_url,
        }
    
    def request_token(self, _=None):
        with self.output:
            clear_output()
            if self.button_clicked:
                display(ipw.HTML(f"""
                Once it appears, copy the text from the frame below, and insert it to the "Token" field above.
                <br/>
                <iframe src="{self.token_url}" width="400" height="100"></iframe>
                """))
        self.button_clicked = not self.button_clicked
    
    @property
    def is_connected(self):
        if self.session and self.session.is_valid_token and self.session.has_rights(rights=["read", "write", "addAttachment"]):
            return True
        return False
    
    @traitlets.default("eln_type")
    def set_eln_type(self):
        return "cheminfo"
    
    
