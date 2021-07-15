# -*- coding: utf-8 -*-
"""Module to define the Cheminfo ELN connector for AiiDAlab."""
import ipywidgets as ipw
import traitlets
from cheminfopy import User
from IPython.display import clear_output, display

from ..base_connector import ElnConnector
from .exporter import export_cif, export_isotherm


class CheminfoElnConnector(ElnConnector):
    """Cheminfo ELN connector to AiiDAlab."""

    access_token = traitlets.Unicode()
    token_url = traitlets.Unicode()
    sample_uuid = traitlets.Unicode()
    file_name = traitlets.Unicode()
    spectrum_type = traitlets.Unicode()

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
            placeholder='Press the "Request token" button below',
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

        self.sample_uuid_widget = ipw.Text(
            description="Sample ID:",
            value="",
            style={"description_width": "initial"},
        )
        traitlets.link((self, "sample_uuid"), (self.sample_uuid_widget, "value"))

        self.file_name_widget = ipw.Text(
            description="File name:",
            value="",
            style={"description_width": "initial"},
        )
        traitlets.link((self, "file_name"), (self.file_name_widget, "value"))

        self.spectrum_type_widget = ipw.Text(
            description="Spectrum type:",
            value="",
            style={"description_width": "initial"},
        )
        traitlets.link((self, "spectrum_type"), (self.spectrum_type_widget, "value"))

        self.output = ipw.Output()

        super().__init__(
            children=[
                eln_instance_widget,
                token_widget,
                token_url_widget,
                request_token_button,
                self.output,
            ],
            **kwargs,
        )

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
        """Request token from the selected Cheminfo ELN."""
        with self.output:
            clear_output()
            if self.button_clicked:
                display(
                    ipw.HTML(
                        f"""
                Once it appears, copy the text from the frame below, and insert it to the "Token" field above.
                <br/>
                <iframe src="{self.token_url}" width="400" height="100"></iframe>
                """
                    )
                )
        self.button_clicked = not self.button_clicked

    @property
    def is_connected(self):
        if (
            self.session
            and self.session.is_valid_token
            and self.session.has_rights(rights=["read", "write", "addAttachment"])
        ):
            return True
        return False

    @traitlets.default("eln_type")
    def set_eln_type(self):  # pylint: disable=no-self-use
        return "cheminfo"

    def set_sample_config(self, **kwargs):
        """Set sample-related variables from a config."""
        if "sample_uuid" in kwargs:
            self.sample_uuid = kwargs["sample_uuid"]
        if "file_name" in kwargs:
            self.file_name = kwargs["file_name"]
        if "spectrum_type" in kwargs:
            self.spectrum_type = kwargs["spectrum_type"]

    def sample_config_editor(self):
        return ipw.VBox(
            [
                self.sample_uuid_widget,
                self.file_name_widget,
                self.spectrum_type_widget,
            ]
        )

    def send_data_object(self, data_object):
        sample_manager = self.session.get_sample(self.sample_uuid)

        if data_object.node_type == "data.dict.Dict.":
            export_isotherm(
                sample_manager,
                isotherm=data_object,
                adsorptive="N2",
                filename=self.file_name,
            )
        elif data_object.node_type == "data.cif.CifData.":
            export_cif(sample_manager, data_object, filename=self.file_name)
