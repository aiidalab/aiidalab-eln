"""Export AiiDA objects to the cheminfo ELN."""

from aiida import orm
from aiida.plugins import WorkflowFactory
from pytojcamp import from_dict


def export_isotherm(
    sample,
    node,
    file_name: str = None,
    aiidalab_instance: str = "unknown",
):
    """Export Isotherm object."""
    source_info = {
        "uuid": node.uuid,
        "url": aiidalab_instance,
        "name": "Isotherm simulated using the isotherm app on AiiDAlab",
    }

    # Workaround till the Isotherm object is not ready.
    isotherm_wf = WorkflowFactory("lsmo.isotherm")
    query = (
        orm.QueryBuilder()
        .append(orm.Dict, filters={"uuid": node.uuid}, tag="isotherm_data")
        .append(isotherm_wf, with_outgoing="isotherm_data", tag="isotherm_wf")
        .append(orm.Str, with_outgoing="isotherm_wf", project="attributes.value")
    )
    adsorptive = query.all(flat=True)
    adsorptive = adsorptive[0] if adsorptive else None

    meta = {
        "adsorptive": adsorptive,
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
    aiidalab_instance: str = "unknown",
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
        file_content=node._prepare_cif()[0],  # pylint: disable=protected-access
        source_info=source_info,
    )
