# -*- coding: utf-8 -*-
from aiida.plugins import DataFactory
from cheminfopy import Sample


def import_cif(eln_instance, sample_uuid, token):
    object_type = DataFactory("cif")
    sample = Sample(instance=eln_instance, sample_uuid=sample_uuid, token=token)
    content = sample.get_spectrum(spectrum_type=spectrum_type, name=file_name)
    file = io.BytesIO(bytes(content, "utf8"))
    node = object_type(file=file)

    eln_info = {
        "eln_instance": eln_instance,
        "sample_uuid": sample_uuid,
        "spectrum_type": spectrum_type,
        "file_name": file_name,
    }
    node.set_extra("eln", eln_info)
    node.store()
    return node
