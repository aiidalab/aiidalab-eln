from pytojcamp import from_dict


def upload_isotherm(
    sample_manager,
    isotherm_dict: dict,
    adsorptive: str,
    uuid: str,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):
    source_info = {
        "uuid": uuid,
        "url": aiidalab_instance,
        "name": "Isotherm simulated using the isotherm app on AiiDAlab",
    }

    jcamp = from_dict(
        {
            "p": {
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
        meta={"adsorptive": adsorptive},
    )

    sample_manager.put_spectrum(
        spectrum_type="isotherm",
        name=f"{uuid}.jdx",
        filecontent=jcamp,
        source_info=source_info,
    )

