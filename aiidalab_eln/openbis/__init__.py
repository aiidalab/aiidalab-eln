from ..base_connector import ElnConnector
import traitlets as tl
from aiida import orm
import ipywidgets as ipw
import pybis as pb



import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from ase import Atoms
from sklearn.decomposition import PCA
from aiida import plugins


def make_ase(species, positions):
    """Create ase Atoms object."""
    # Get the principal axes and realign the molecule along z-axis.
    positions = PCA(n_components=3).fit_transform(positions)
    atoms = Atoms(species, positions=positions, pbc=True)
    atoms.cell = np.ptp(atoms.positions, axis=0) + 10
    atoms.center()

    return atoms

def _rdkit_opt(smiles, steps=1000):
    """Optimize a molecule using force field and rdkit (needed for complex SMILES)."""

    smiles = smiles.replace("[", "").replace("]", "")
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)

    AllChem.EmbedMolecule(mol, maxAttempts=20, randomSeed=42)
    AllChem.UFFOptimizeMolecule(mol, maxIters=steps)
    positions = mol.GetConformer().GetPositions()
    natoms = mol.GetNumAtoms()
    species = [mol.GetAtomWithIdx(j).GetSymbol() for j in range(natoms)]
    return make_ase(species, positions)

def import_smiles(sample):
    object_type = plugins.DataFactory("structure")
    node = object_type(ase=_rdkit_opt(sample.props.smiles))
    return node
    

class OpenbisElnConnector(ElnConnector):
    """OpenBIS ELN connector to AiiDAlab."""

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
    def connect(self):
        """Function to login to openBIS."""
        self.session = pb.Openbis(self.eln_instance, verify_certificates=False)
        self.session.set_token(self.token)
        return ""

    def get_config(self):
        return {
            "eln_instance": self.eln_instance,
            "eln_type": self.eln_type,
            "token": self.token,
        }

    def request_token(self, _=None):
        """Request a token."""
        raise NotImplementedError("The method 'request_token' is not implemented yet.")

    @property
    def is_connected(self):
        return self.session.is_token_valid()

    @tl.default("eln_type")
    def set_eln_type(self):  # pylint: disable=no-self-use
        return "openbis"
    
    
    def import_data(self):
        """Import data object from OpenBIS ELN to AiiDAlab."""
        
        sample = self.session.get_sample(self.sample_uuid)
        
        #print("Sample", sample)
        if self.data_type == "smiles":
            self.node = import_smiles(sample)
        eln_info = {
            "eln_instance": self.eln_instance,
            "eln_type": self.eln_type,
            "sample_uuid": self.sample_uuid,
            "data_type": self.data_type,
        }
        self.node.set_extra("eln", eln_info)
        self.node.store()
