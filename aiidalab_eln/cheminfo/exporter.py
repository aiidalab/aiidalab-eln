from pytojcamp import from_dict


def export_isotherm(
    sample_manager,
    isotherm,
    adsorptive: str,
    filename: str = None,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):
    source_info = {
        "uuid": isotherm.uuid,
        "url": aiidalab_instance,
        "name": "Isotherm simulated using the isotherm app on AiiDAlab",
    }
    meta = {
        "adsorptive": adsorptive,
        "temperature": isotherm["temperature"],
        "method": "GCMC",
    }
    jcamp = from_dict(
        {
            "x": {
                "data": isotherm["isotherm"]["pressure"],
                "unit": isotherm["isotherm"]["pressure_unit"],
                "type": "INDEPENDENT",
            },
            "y": {
                "data": isotherm["isotherm"]["loading_absolute_average"],
                "unit": isotherm["isotherm"]["loading_absolute_unit"],
                "type": "DEPENDENT",
            },
        },
        data_type="Adsorption Isotherm",
        meta=meta,
    )
    name = f"{isotherm.uuid}.jcamp" if filename is None else f"{filename}.jcamp"
    sample_manager.put_spectrum(
        spectrum_type="isotherm",
        name=name,
        filecontent=jcamp,
        metadata=meta,
        source_info=source_info,
    )

def export_cif(
    sample_manager,
    cifdata,
    filename: str = None,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):

    source_info = {
        "uuid": cifdata.uuid,
        "url": aiidalab_instance,
        "name": "Structure optimized using the XXX app on AiiDAlab",
    }

    sample_manager.put_spectrum(
        spectrum_type="xray",
        name=f"{cifdata.uuid}.cif" if filename is None else f"{filename}.cif",
        filecontent=cifdata._prepare_cif(),
        source_info=source_info,
    )


