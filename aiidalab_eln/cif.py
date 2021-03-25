def upload_cif(
    sample_manager,
    cifdata,
    uuid: str,
    aiidalab_instance: str = "https://aiidalab-demo.materialscloud.org",
):

    source_info = {
        "uuid": uuid,
        "url": aiidalab_instance,
        "name": "Structure optimized using the XXX app on AiiDAlab",
    }

    sample_manager.put_spectrum(
        spectrum_type="xray",
        name=f"{uuid}.cif",
        filecontent=cifdata._prepare_cif(),
        source_info=source_info,
    )
