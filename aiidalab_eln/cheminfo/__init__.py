"""Module to define the Cheminfo ELN connector for AiiDAlab."""

import pathlib

import ipywidgets as ipw
import traitlets
from aiida.orm import Node
from cheminfopy import User, errors
from IPython.display import Javascript, display

from ..base_connector import ElnConnector
from .exporter import export_cif, export_isotherm
from .importer import import_cif, import_pdb


class CheminfoElnConnector(ElnConnector):
    """Cheminfo ELN connector to AiiDAlab."""

    node = traitlets.Instance(Node, allow_none=True)
    token = traitlets.Unicode()
    sample_uuid = traitlets.Unicode()
    file_name = traitlets.Unicode()
    data_type = traitlets.Unicode()

    def __init__(self, **kwargs):

        self.session = None

        eln_instance_widget = ipw.Text(
            description="ELN address:",
            value="https://mydb.cheminfo.org/",
            style={"description_width": "initial"},
        )
        traitlets.link((self, "eln_instance"), (eln_instance_widget, "value"))

        token_widget = ipw.Text(
            description="Token:",
            value="",
            placeholder='Press the "Request token" button below',
            style={"description_width": "initial"},
        )
        traitlets.link((self, "token"), (token_widget, "value"))

        request_token_button = ipw.Button(
            description="Request token", tooltip="Will open new tab/window."
        )
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

    def connect(self):
        """Connect to the cheminfo ELN."""
        try:
            self.session = User(instance=self.eln_instance, token=self.token)
            return ""
        except errors.InvalidInstanceUrlError:
            return "The ELN address seems to be wrong."

    def get_config(self):
        return {
            "eln_instance": self.eln_instance,
            "eln_type": self.eln_type,
            "token": self.token,
        }

    def request_token(self, _=None):
        """Request token from the selected Cheminfo ELN."""
        token_url = self.eln_instance + "/misc/token/"
        display(Javascript(f'window.open("{token_url}");'))

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
        for key, value in kwargs.items():
            if hasattr(self, key) and key in ("file_name", "sample_uuid"):
                setattr(self, key, value)

    def sample_config_editor(self):
        return ipw.VBox(
            [
                self.sample_uuid_widget,
                self.file_name_widget,
            ]
        )

    def export_data(self):
        """Export AiiDA object (node attribute of this class) to ELN."""

        sample = self.session.get_sample(self.sample_uuid)

        # Choose the data type.
        if self.node.node_type == "data.dict.Dict.":
            export_isotherm(
                sample,
                self.node,
                self.file_name,
                aiidalab_instance=self.aiidalab_instance,
            )
        elif self.node.node_type == "data.cif.CifData.":
            export_cif(
                sample,
                self.node,
                self.file_name,
                aiidalab_instance=self.aiidalab_instance,
            )

    def import_data(self):
        """Import data object from cheminfo ELN to AiiDAlab."""
        sample = self.session.get_sample(self.sample_uuid)
        fpath = pathlib.Path(self.file_name)

        # Choose the data type.
        if self.data_type == "xray":
            if fpath.suffix == ".cif":
                self.node = import_cif(
                    sample,
                    file_name=self.file_name,
                )
            elif fpath.suffix == ".pdb":
                self.node = import_pdb(
                    sample,
                    file_name=self.file_name,
                )
            else:
                raise NotImplementedError(
                    f'Importer for the data type "{self.data_type}" is not yet implemented.'
                )

        # Add extra information.
        eln_info = {
            "eln_instance": self.eln_instance,
            "eln_type": self.eln_type,
            "sample_uuid": self.sample_uuid,
            "data_type": self.data_type,
            "file_name": fpath.stem,
        }
        self.node.set_extra("eln", eln_info)
        self.node.store()
