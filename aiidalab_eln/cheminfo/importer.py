"""Module to define import tools from Cheminfo ELN to AiiDAlab."""

import io

from aiida.plugins import DataFactory
from ase.io import read


def import_cif(sample, **kwargs):
    """Import CIF object from Cheminfo ELN to AiiDAlab."""
    object_type = DataFactory("cif")
    content = sample.get_spectrum(spectrum_type="xray", name=kwargs["file_name"])
    file = io.BytesIO(bytes(content, "utf8"))
    node = object_type(file=file)
    return node


def import_pdb(sample, **kwargs):
    """Import PDB object from Cheminfo ELN to AiiDAlab."""
    object_type = DataFactory("structure")
    content = sample.get_spectrum(spectrum_type="xray", name=kwargs["file_name"])
    file = io.BytesIO(bytes(content, "utf8"))
    node = object_type(from_ase=read(file))
    return node
