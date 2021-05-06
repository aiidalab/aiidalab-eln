from pytojcamp import from_dict
from cheminfopy import Sample


def upload_isotherm(
    sample_manager,
    isotherm_dict: dict,
    adsorptive: str,
    filename: str = None,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):
    source_info = {
        "uuid": isotherm_dict.uuid,
        "url": aiidalab_instance,
        "name": "Isotherm simulated using the isotherm app on AiiDAlab",
    }
    meta = {
        "adsorptive": adsorptive,
        "temperature": isotherm_dict["temperature"],
        "method": "GCMC",
    }
    jcamp = from_dict(
        {
            "x": {
                "data": isotherm_dict["isotherm"]["pressure"],
                "unit": isotherm_dict["isotherm"]["pressure_unit"],
                "type": "INDEPENDENT",
            },
            "y": {
                "data": isotherm_dict["isotherm"]["loading_absolute_average"],
                "unit": isotherm_dict["isotherm"]["loading_absolute_unit"],
                "type": "DEPENDENT",
            },
        },
        data_type="Adsorption Isotherm",
        meta=meta,
    )
    name = f"{isotherm_dict.uuid}.jcamp" if filename is None else f"{filename}.jcamp"
    sample_manager.put_spectrum(
        spectrum_type="isotherm",
        name=name,
        filecontent=jcamp,
        metadata=meta,
        source_info=source_info,
    )

def upload_cif(
    sample_manager,
    cifdata,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):

    source_info = {
        "uuid": uuid,
        "url": aiidalab_instance,
        "name": "Structure optimized using the XXX app on AiiDAlab",
    }

    sample_manager.put_spectrum(
        spectrum_type="xray",
        name=f"{cifdata.uuid}.cif",
        filecontent=cifdata._prepare_cif(),
        source_info=source_info,
    )

def object_uploader(obj, eln_instance, sample_uuid, token):
    sample_manager = Sample(
        eln_instance,
        sample_uuid=sample_uuid,
        token=token,
    )
    if obj.node_type == "data.dict.Dict.":
        upload_isotherm(sample_manager, isotherm_dict=obj, adsorptive="N2")
    elif obj.node_type == "data.cif.CifData.":
        upload_cif(sample_manager, obj) 