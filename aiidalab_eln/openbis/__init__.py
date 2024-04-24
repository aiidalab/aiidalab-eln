from ..base_connector import ElnConnector
import traitlets as tl
from aiida import orm
import ipywidgets as ipw


class OpenbisElnConnector(ElnConnector):
    """Cheminfo ELN connector to AiiDAlab."""

    node = tl.Instance(orm.Node, allow_none=True)
    token = tl.Unicode()
    sample_uuid = tl.Unicode()
    file_name = tl.Unicode()
    data_type = tl.Unicode()

    def __init__(self, **kwargs):
        self.session = None

        eln_instance_widget = ipw.Text(
            description="ELN address:",
            value="https://mydb.cheminfo.org/",
            style={"description_width": "initial"},
        )
        tl.link((self, "eln_instance"), (eln_instance_widget, "value"))

        token_widget = ipw.Text(
            description="Token:",
            value="",
            placeholder='Press the "Request token" button below',
            style={"description_width": "initial"},
        )
        tl.link((self, "token"), (token_widget, "value"))

        request_token_button = ipw.Button(
            description="Request token", tooltip="Will open new tab/window."
        )
        request_token_button.on_click(self.request_token)

        self.sample_uuid_widget = ipw.Text(
            description="Sample ID:",
            value="",
            style={"description_width": "initial"},
        )
        tl.link((self, "sample_uuid"), (self.sample_uuid_widget, "value"))

        self.file_name_widget = ipw.Text(
            description="File name:",
            value="",
            style={"description_width": "initial"},
        )
        tl.link((self, "file_name"), (self.file_name_widget, "value"))

        self.output = ipw.Output()

        super().__init__(
            children=[
                eln_instance_widget,
                token_widget,
                request_token_button,
                self.output,
                ipw.HTML(
                    value="You can find more information about the integration with the cheminfo ELN in \
                        <a href='https://docs.c6h6.org/docs/eln/uuid/07223c3391c6b0cde342518d240d3426#integration-with-molecular-and-atomistic-simulations'  target='_blank'>\
                        the documentation</a>."
                ),
            ],
            **kwargs,
        )
    
    def request_token(self, _=None):
        """Request a token."""
        raise NotImplementedError("The method 'request_token' is not implemented yet.")