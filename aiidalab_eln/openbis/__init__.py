import json
import os
import shutil

import ipywidgets as ipw
import numpy as np
import pybis as pb
import rdkit
import traitlets as tl
from aiida import orm, plugins
from ase import Atoms
from rdkit import Chem
from rdkit.Chem import AllChem
from sklearn.decomposition import PCA
from surfaces_tools.widgets import cdxml

from ..base_connector import ElnConnector


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


def read_file(filename):
    return open(filename, "rb").read()


def import_smiles(smiles):
    object_type = plugins.DataFactory("structure")
    node = object_type(ase=_rdkit_opt(smiles))
    return node


def get_molecule_cdxml(session, molecule_permid):
    molecule_obis = session.get_object(molecule_permid)
    molecule_obis_datasets = molecule_obis.get_datasets()
    for dataset in molecule_obis_datasets:
        dataset_files = dataset.file_list
        for file in dataset_files:
            _, file_extension = os.path.splitext(file)
            if file_extension == ".cdxml":
                dataset.download(destination="cdxml_files")
                structure_filepath = f"cdxml_files/{dataset.permId}/{file}"
                structure_cdxml = read_file(structure_filepath)
                shutil.rmtree(f"cdxml_files/{dataset.permId}/")
                return structure_cdxml


class OpenbisElnConnector(ElnConnector):
    """OpenBIS ELN connector to AiiDAlab."""

    node = tl.Instance(orm.Node, allow_none=True)
    token = tl.Unicode()
    sample_uuid = tl.Unicode()
    molecule_info = tl.Unicode()
    molecule_uuid = tl.Unicode()
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

        self.output = ipw.VBox()

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

    def set_sample_config(self, **kwargs):
        """Set sample-related variables from a config."""
        for key, value in kwargs.items():
            if hasattr(self, key) and key in ("file_name", "sample_uuid"):
                setattr(self, key, value)

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

    def sample_config_editor(self):
        return ipw.VBox(
            [
                self.sample_uuid_widget,
            ]
        )

    def get_all_structures_and_geoopts(self, node):
        """Get all atomistic models that led to the one used in the simulation"""
        current_node = node
        all_structures = []
        all_geoopts = []

        while current_node is not None:
            if isinstance(current_node, orm.StructureData):
                all_structures.append(current_node)
                current_node = current_node.creator

            elif isinstance(current_node, orm.CalcJobNode):
                current_node = current_node.caller

            elif isinstance(current_node, orm.CalcFunctionNode):
                current_node = current_node.inputs.source_structure

            elif isinstance(current_node, orm.WorkChainNode):
                if "GeoOpt" in current_node.label:
                    all_geoopts.append(current_node)
                    current_node = current_node.inputs.structure
                elif "ORBITALS" in current_node.label or "STM" in current_node.label:
                    current_node = current_node.inputs.structure
                else:
                    current_node = current_node.caller

        return all_structures, all_geoopts

    def import_data(self):
        """Import data object from OpenBIS ELN to AiiDAlab."""

        # sample = self.extract_sample_id()
        molecule_info_dict = json.loads(self.molecule_info)

        if self.data_type == "smiles":
            self.node = import_smiles(molecule_info_dict["smiles"])

        elif self.data_type == "cdxml":
            self.cdxml_import_widget = cdxml.CdxmlUpload2GnrWidget()
            tl.dlink(
                (self.cdxml_import_widget, "structure"),
                (self, "node"),
                transform=lambda struct: orm.StructureData(ase=struct),
            )

            self.output.children = [self.cdxml_import_widget]

            cdxml_content = get_molecule_cdxml(self.session, self.sample_uuid)
            cdxml_content = cdxml_content.decode("ascii")  # To test
            (
                self.cdxml_import_widget.crossing_points,
                self.cdxml_import_widget.cdxml_atoms,
                self.cdxml_import_widget.nunits.disabled,
            ) = self.cdxml_import_widget.extract_crossing_and_atom_positions(
                cdxml_content
            )

            # Convert CDXML content to RDKit molecules and ASE Atoms objects
            options = [
                self.cdxml_import_widget.rdkit2ase(mol)
                for mol in rdkit.Chem.MolsFromCDXML(cdxml_content)
            ]
            self.cdxml_import_widget.atoms = options[0]
            self.cdxml_import_widget._on_button_click()

        # eln_info = {
        #     "eln_instance": self.eln_instance,
        #     "eln_type": self.eln_type,
        #     "sample_uuid": self.sample_uuid,
        #     "data_type": self.data_type,
        # }
        # self.node.set_extra("eln", eln_info)
        # self.node.store()

    def create_new_collection_openbis(
        self, project_code, collection_code, collection_type, collection_name
    ):
        collection = self.session.new_collection(
            project=project_code, code=collection_code, type=collection_type
        )
        collection.props["$name"] = collection_name
        collection.save()
        return collection

    def get_collection_openbis(self, collection_identifier):
        return self.session.get_collection(code=collection_identifier)

    def check_if_collection_exists(self, project_code, collection_code):
        return (
            self.session.get_collections(
                project=project_code, code=collection_code
            ).df.empty
            is False
        )

    def create_collection_openbis(
        self,
        project_code,
        collection_name,
        collection_code,
        collection_type,
        collection_exists,
    ):
        if collection_exists is False:
            collection = self.create_new_collection_openbis(
                project_code, collection_code, collection_type, collection_name
            )
        else:
            collection_identifier = f"{project_code}/{collection_code}"
            collection = self.get_collection_openbis(collection_identifier)

        return collection

    def get_objects_list_openbis(self, object_type):
        return self.session.get_objects(type=object_type)

    def check_aiida_objects_in_openbis(self, aiida_objects, openbis_objects):
        aiida_objects_inside_openbis = []
        # Verify which AiiDA objects are already in openBIS
        for _, aiida_object in enumerate(aiida_objects):
            aiida_object_inside_openbis_exists = False
            for openbis_object in openbis_objects:
                if openbis_object.props.get("wfms_uuid") == aiida_object.uuid:
                    aiida_objects_inside_openbis.append([openbis_object, True])
                    aiida_object_inside_openbis_exists = True
                    print(
                        f"Object {openbis_object.props.get('wfms_uuid')} already exists."
                    )

            if aiida_object_inside_openbis_exists is False:
                aiida_objects_inside_openbis.append([None, False])

        # Reverse the lists because in openBIS, one should start by building the parents.
        aiida_objects.reverse()
        aiida_objects_inside_openbis.reverse()

        return aiida_objects, aiida_objects_inside_openbis

    def create_new_object_openbis(
        self, collection_identifier, object_type, parents=None
    ):
        if parents is None:
            return self.session.new_sample(
                collection=collection_identifier, type=object_type
            )
        else:
            return self.session.new_sample(
                collection=collection_identifier, type=object_type, parents=parents
            )

    def set_atomistic_model_props(
        self,
        aiida_object_index,
        aiida_object,
        number_aiida_objects,
        openbis_object_type,
    ):

        if openbis_object_type == "ATOMISTIC_MODEL":
            # Get Structure details from AiiDA
            structure_ase = aiida_object.get_ase()
            # structure_ase.positions # Atoms positions
            # structure_ase.symbols # Atoms Symbols
            # structure.cell # Cell vectors

            pbc = json.dumps(
                {
                    "x": int(structure_ase.pbc[0]),
                    "y": int(structure_ase.pbc[1]),
                    "z": int(structure_ase.pbc[2]),
                }
            )

            object_props = {
                "$name": f"Atomistic Model {aiida_object_index}",
                "wfms_uuid": aiida_object.uuid,
                "periodic_boundary_conditions": pbc,
            }

            if (
                number_aiida_objects > 1
                and aiida_object_index == number_aiida_objects - 1
            ):  # If it is the last of more than one structures, it is optimised.
                object_props["optimised"] = True
            else:
                object_props["optimised"] = False

        return object_props

    def create_atomistic_models(
        self, structures_nodes, structures_inside_openbis, collection_identifier
    ):
        atomistic_models = []
        selected_molecule = None

        for structure_index, structure in enumerate(structures_nodes):

            # If the structure contains a molecule, save it as a parent of the previous atomistic model because it is the molecule that started all the simulation
            if "eln" in structure.base.extras.all:
                selected_molecule = self.session.get_sample(
                    structure.base.extras.all["eln"]["molecule_uuid"]
                )
            else:
                structure_inside_openbis = structures_inside_openbis[structure_index]

                if structure_inside_openbis[1] is False:
                    # Create Atomistic Model in openBIS
                    number_aiida_objects = len(structures_nodes)
                    atomistic_model = self.create_new_object_openbis(
                        collection_identifier, "ATOMISTIC_MODEL"
                    )
                    atomistic_model.props = self.set_atomistic_model_props(
                        structure_index,
                        structure,
                        number_aiida_objects,
                        "ATOMISTIC_MODEL",
                    )
                    atomistic_model.save()
                    atomistic_models.append(atomistic_model)
                else:
                    atomistic_models.append(structure_inside_openbis[0])

        # If the simulation started from openBIS, we make the connection between the molecule and the first atomistic model
        # If the atomistic model (second structure, right after the molecule) is already there, there is no need to make the connection, because in principle it already contains it
        if selected_molecule is not None and structures_inside_openbis[1][1] is False:
            atomistic_models[0].add_parents(selected_molecule)
            atomistic_models[0].save()

        return atomistic_models

    def create_geoopts_simulations(
        self,
        geoopts_nodes,
        geoopts_inside_openbis,
        collection_identifier,
        atomistic_models,
    ):
        geoopts_simulations = []

        for geoopt_index, geoopt in enumerate(geoopts_nodes):
            geoopt_inside_openbis = geoopts_inside_openbis[geoopt_index]

            if geoopt_inside_openbis[1] is False:
                parent_atomistic_model = atomistic_models[geoopt_index]

                geoopt_model = self.create_new_object_openbis(
                    collection_identifier,
                    "GEOMETRY_OPTIMISATION",
                    [parent_atomistic_model],
                )
                geoopt_model.props = {
                    "$name": f"GeoOpt Simulation {geoopt_index}",
                    "wfms_uuid": geoopt.uuid,
                }
                geoopt_model.save()

                # Its plus one because there are N+1 geometries for N GeoOpts
                atomistic_models[geoopt_index + 1].add_parents(geoopt_model)
                atomistic_models[geoopt_index + 1].save()

                geoopts_simulations.append(geoopt_model)
            else:
                geoopts_simulations.append(geoopt_inside_openbis[0])

        return geoopts_simulations, atomistic_models

    def create_stm_simulations(
        self, stms_nodes, stms_inside_openbis, collection_identifier, atomistic_models
    ):
        stms_simulations = []

        for stm_index, stm in enumerate(stms_nodes):
            stm_inside_openbis = stms_inside_openbis[stm_index]

            if stms_inside_openbis[0][1] is False:

                optimised_atomistic_model = atomistic_models[-1]

                # Simulated STM
                stm_model = self.create_new_object_openbis(
                    collection_identifier, "2D_MEASUREMENT", [optimised_atomistic_model]
                )

                stm_model.props = {
                    "$name": f"STM Simulation {stm_index}",
                    "wfms_uuid": stm.uuid,
                }
                # dft_params = dict(self.node.inputs.dft_params)

                # TODO: Remove this is the future. Orbitals do not have stm_params
                try:
                    stm_params = dict(stm.inputs.spm_params)
                    stm_model.props = {
                        "e_min": json.dumps(
                            {
                                "value": float(stm_params["--energy_range"][0]),
                                "unit": "http://qudt.org/vocab/unit/EV",
                            }
                        ),
                        "e_max": json.dumps(
                            {
                                "value": float(stm_params["--energy_range"][1]),
                                "unit": "http://qudt.org/vocab/unit/EV",
                            }
                        ),
                        "de": json.dumps(
                            {
                                "value": float(stm_params["--energy_range"][2]),
                                "unit": "http://qudt.org/vocab/unit/EV",
                            }
                        ),
                    }
                except Exception:
                    pass

                stm_model.save()

                # stm_simulation_images_zip_filename = series_plotter_inst.create_zip_link_for_openbis()

                # stm_simulation_images_dataset = self.session.new_dataset(
                #     type = "RAW_DATA",
                #     files = [stm_simulation_images_zip_filename],
                #     sample = stm_simulation_model
                # )
                # stm_simulation_images_dataset.save()

                # TODO: How to do this using Python commands?
                stm_simulation_dataset_filename = "stm_simulation.aiida"
                os.system(
                    f"verdi archive create {stm_simulation_dataset_filename} --no-call-calc-backward --no-call-work-backward --no-create-backward -N {stm.pk}"
                )

                stm_simulation_dataset = self.session.new_dataset(
                    type="RAW_DATA",
                    files=[stm_simulation_dataset_filename],
                    sample=stm_model,
                )
                stm_simulation_dataset.save()

                # Delete the file after uploading
                os.remove(stm_simulation_dataset_filename)

                stms_simulations.append(stm_model)
            else:
                stms_simulations.append(stm_inside_openbis[0])

        return stms_simulations

    def export_data(self):
        """Export AiiDA object (node attribute of this class) to ELN."""

        # Get experiment from openBIS
        selected_experiment = self.session.get_experiment(self.sample_uuid)

        # Create a collection for storing atomistic models in openBIS if it is not already there
        inventory_project_code = "/MATERIALS/ATOMISTIC_MODELS"
        atomistic_models_collection_name = "Atomistic Models"
        atomistic_models_collection_type = "COLLECTION"
        atomistic_models_collection_code = "ATOMISTIC_MODEL_COLLECTION"
        atomistic_models_collection_identifier = (
            f"{inventory_project_code}/{atomistic_models_collection_code}"
        )

        atomistic_models_collection_exists = self.check_if_collection_exists(
            inventory_project_code, atomistic_models_collection_code
        )
        _ = self.create_collection_openbis(
            inventory_project_code,
            atomistic_models_collection_name,
            atomistic_models_collection_code,
            atomistic_models_collection_type,
            atomistic_models_collection_exists,
        )

        # Get all geoopts and atomistic models from openbis
        geoopts_openbis = self.get_objects_list_openbis("GEOMETRY_OPTIMISATION")
        atomistic_models_openbis = self.get_objects_list_openbis("ATOMISTIC_MODEL")

        # Get Geometry Optimisation Workchain from AiiDA
        all_structures, all_aiida_geoopts = self.get_all_structures_and_geoopts(
            self.node
        )

        # Verify which GeoOpts are already in openBIS
        all_aiida_geoopts, all_geoopts_inside_openbis = (
            self.check_aiida_objects_in_openbis(all_aiida_geoopts, geoopts_openbis)
        )

        # Verify which structures (atomistic models) are already in openBIS
        all_structures, all_structures_inside_openbis = (
            self.check_aiida_objects_in_openbis(
                all_structures, atomistic_models_openbis
            )
        )

        # Get the project identifier of the selected experiment
        # project_identifier = selected_experiment.project.identifier

        # Create a new simulation experiment in openBIS
        # now = datetime.now()
        # simulation_number = now.strftime("%d%m%Y%H%M%S")
        # simulation_experiment_code = f"SIMULATION_EXPERIMENT_{simulation_number}"
        # simulation_experiment_name = "Simulation of Methane on Au"
        # simulation_experiment = self.get_collection_openbis(self.sample_uuid)

        # TODO: Do we need to create a simulation experiment or do we put the simulations inside the selected experiment?
        simulation_experiment_identifier = selected_experiment.identifier

        # Build atomistic models (structures in AiiDA) in openBIS
        all_atomistic_models = self.create_atomistic_models(
            all_structures,
            all_structures_inside_openbis,
            atomistic_models_collection_identifier,
        )

        # Build GeoOpts in openBIS
        all_geoopts_simulations, all_atomistic_models = self.create_geoopts_simulations(
            all_aiida_geoopts,
            all_geoopts_inside_openbis,
            simulation_experiment_identifier,
            all_atomistic_models,
        )

        if isinstance(self.node, orm.WorkChainNode):

            # Get structure used in the Workchain
            all_aiida_stms = [self.node]

            # Get all STMs inside openBIS
            stms_openbis = self.get_objects_list_openbis("STM")

            # Verify which structures (atomistic models) are already in openBIS
            all_aiida_stms, all_stms_inside_openbis = (
                self.check_aiida_objects_in_openbis(all_aiida_stms, stms_openbis)
            )

            # Build STM Simulations in openBIS
            _ = self.create_stm_simulations(
                all_aiida_stms,
                all_stms_inside_openbis,
                simulation_experiment_identifier,
                all_atomistic_models,
            )

    # def extract_sample_id(self):

    #     experiment = self.session.get_experiment(self.sample_uuid)
    #     samples = experiment.get_samples()

    #     for sample in samples:
    #         if sample.type.code == "DEPOSITION":
    #             deposition_sample = self.session.get_sample(sample.permId)
    #             break

    #     for parent in deposition_sample.parents:
    #         parent_sample = self.session.get_sample(parent)

    #         if parent_sample.type.code == "MOLECULE":
    #             molecule_sample = self.session.get_sample(parent_sample.permId)
    #             break

    #     return molecule_sample
