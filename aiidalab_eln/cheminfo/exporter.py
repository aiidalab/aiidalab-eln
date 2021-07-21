# -*- coding: utf-8 -*-
"""Export AiiDA objects to the Cheminfo ELN."""

from pytojcamp import from_dict


def export_isotherm(
    sample,
    node,
    file_name: str = None,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):
    """Export Isotherm object."""
    source_info = {
        "uuid": node.uuid,
        "url": aiidalab_instance,
        "name": "Isotherm simulated using the isotherm app on AiiDAlab",
    }
    meta = {
        "adsorptive": "N2",
        "temperature": node["temperature"],
        "method": "GCMC",
    }
    jcamp = from_dict(
        {
            "x": {
                "data": node["isotherm"]["pressure"],
                "unit": node["isotherm"]["pressure_unit"],
                "type": "INDEPENDENT",
            },
            "y": {
                "data": node["isotherm"]["loading_absolute_average"],
                "unit": node["isotherm"]["loading_absolute_unit"],
                "type": "DEPENDENT",
            },
        },
        data_type="Adsorption Isotherm",
        meta=meta,
    )
    sample.put_data(
        data_type="isotherm",
        file_name=f"{node.uuid}.jcamp" if file_name is None else f"{file_name}.jcamp",
        file_content=jcamp,
        metadata=meta,
        source_info=source_info,
    )


def export_cif(
    sample,
    node,
    file_name: str = None,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):
    """Export CIF object."""

    source_info = {
        "uuid": node.uuid,
        "url": aiidalab_instance,
        "name": "Structure optimized on AiiDAlab",
    }

    sample.put_data(
        data_type="xray",
        file_name=f"{node.uuid}.cif" if file_name is None else f"{file_name}.cif",
        file_content=node._prepare_cif(),  # pylint: disable=protected-access
        source_info=source_info,
    )
