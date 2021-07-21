"""Module to define import tools from Cheminfo ELN to AiiDAlab."""

import io

from aiida.plugins import DataFactory
from ase.io import read


def import_cif(sample, **kwargs):
    """Import CIF object from sample in cheminfo ELN to AiiDA node."""
    object_type = DataFactory("cif")
    file_content = sample.get_data(data_type="xray", file_name=kwargs["file_name"])
    file_object = io.BytesIO(bytes(file_content, "utf8"))
    node = object_type(file=file_object)
    return node


def import_pdb(sample, **kwargs):
    """Import PDB object from sample in cheminfo ELN to AiiDA node."""
    object_type = DataFactory("structure")
    file_content = sample.get_data(data_type="xray", file_name=kwargs["file_name"])
    file_object = io.BytesIO(bytes(file_content, "utf8"))
    node = object_type(from_ase=read(file_object))
    return node
