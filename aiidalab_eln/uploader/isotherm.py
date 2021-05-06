from pytojcamp import from_dict


def upload_isotherm(
    sample_manager,
    isotherm_dict: dict,
    adsorptive: str,
    uuid: str,
    filename: str = None,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):
    source_info = {
        "uuid": uuid,
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
    name = f"{uuid}.jcamp" if filename is None else f"{filename}.jcamp"
    sample_manager.put_spectrum(
        spectrum_type="isotherm",
        name=name,
        filecontent=jcamp,
        metadata=meta,
        source_info=source_info,
    )

