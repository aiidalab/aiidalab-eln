from pathlib import Path
from types import SimpleNamespace

import ase
import pytest
from aiida import orm
from aiida.tools.archive import create_archive
from aiida.tools.archive.implementations.sqlite_zip.main import ArchiveFormatSqlZip

from aiidalab_eln.openbis.structure_importer import (
    ELN_ORIGIN_EXTRA,
    OpenbisStructureImporterWidget,
    _chemical_counts,
    _parse_elements,
    extract_structure_archive,
    structure_fingerprint,
)


class FakeProps:
    def __init__(self, values):
        self._values = values

    def all(self):
        return dict(self._values)


class FakeDataset:
    def __init__(self, permid, files):
        self.permId = permid
        self.file_list = list(files)
        self._files = dict(files)

    def download(self, destination):
        root = Path(destination) / self.permId / "original"
        root.mkdir(parents=True)
        for filename, content in self._files.items():
            path = root / Path(filename).name
            path.write_bytes(content)


class FakeObject:
    def __init__(self, permid, type_code, properties=None, datasets=()):
        self.permId = permid
        self.type = SimpleNamespace(code=type_code)
        self.props = FakeProps(properties or {})
        self._datasets = list(datasets)
        self._parents = []
        self._children = []

    def get_datasets(self):
        return list(self._datasets)

    def get_parents(self):
        return list(self._parents)

    def get_children(self):
        return list(self._children)


class FakeSession:
    def __init__(self, objects):
        self.objects = {obj.permId: obj for obj in objects}

    def get_objects(self, type):
        return [obj for obj in self.objects.values() if obj.type.code == type]

    def get_object(self, identifier):
        return self.objects[identifier]


def test_formula_and_element_filters():
    assert _chemical_counts("Au4C2O") == {"Au": 4, "C": 2, "O": 1}
    assert _chemical_counts("not a formula") is None
    assert _parse_elements("au, C O;co") == {"Au", "C", "O", "Co"}
    with pytest.raises(ValueError, match="Unknown chemical element"):
        _parse_elements("Gold")


def test_atomistic_model_search_filters():
    objects = [
        FakeObject(
            "am-1",
            "ATOMISTIC_MODEL",
            {"name": "C2H6", "dimensionality": "0", "wfms_uuid": "uuid-1"},
        ),
        FakeObject(
            "am-2",
            "ATOMISTIC_MODEL",
            {"name": "Au4CO", "dimensionality": "2", "wfms_uuid": "uuid-2"},
        ),
    ]
    widget = OpenbisStructureImporterWidget(
        session=FakeSession(objects), eln_instance="https://openbis.example/"
    )
    widget.dimensionality_filter.value = 2
    widget.elements_filter.value = "Au C"
    widget.max_atoms_filter.value = 6
    widget._search()

    assert tuple(widget.results.options) == (("Au4CO - 2D - 6 atoms - am-2", "am-2"),)
    assert widget.source.value == "__aiida_node__"


def test_molecule_offers_only_available_representations():
    dataset = FakeDataset(
        "ds-1",
        {
            "1001.cdxml": b"<CDXML/>",
            "1001.xyz": b"1\ncomment\nC 0 0 0\n",
            "notes.txt": b"not structural",
        },
    )
    molecule = FakeObject(
        "mol-1",
        "MOLECULE",
        {"empa_number": "1001", "name": "methane", "sum_formula": "CH4", "smiles": "C"},
        [dataset],
    )
    widget = OpenbisStructureImporterWidget(
        session=FakeSession([molecule]), eln_instance="https://openbis.example/"
    )
    widget.mode.value = "MOLECULE"
    widget.name_filter.value = "1001 methane"
    widget._search()

    labels = [label for label, _ in widget.source.options]
    assert labels == [
        "Planar CDXML - 1001.cdxml",
        "Stored geometry - 1001.xyz",
        "3D geometry generated from SMILES",
    ]


@pytest.mark.usefixtures("aiida_profile_clean")
def test_smiles_import_records_openbis_origin():
    molecule = FakeObject(
        "mol-1",
        "MOLECULE",
        {"empa_number": "1001", "name": "methane", "sum_formula": "CH4", "smiles": "C"},
    )
    widget = OpenbisStructureImporterWidget(
        session=FakeSession([molecule]), eln_instance="https://openbis.example/"
    )
    widget.mode.value = "MOLECULE"
    widget._search()
    widget.source.value = "__smiles__"
    widget._load()

    assert isinstance(widget.structure, orm.StructureData)
    assert not widget.structure.is_stored
    origin = widget.structure.base.extras.get(ELN_ORIGIN_EXTRA)
    assert origin["eln_instance"] == "https://openbis.example"
    assert origin["sample_uuid"] == "mol-1"
    assert origin["data_type"] == "MOLECULE"
    assert origin["representation"] == "smiles"
    assert origin["structure_fingerprint"] == structure_fingerprint(
        widget.structure.get_ase()
    )


@pytest.mark.usefixtures("aiida_profile_clean")
def test_atomistic_model_reuses_local_structure():
    node = orm.StructureData(ase=ase.Atoms("CH4")).store()
    model = FakeObject(
        "am-1",
        "ATOMISTIC_MODEL",
        {"name": "CH4", "dimensionality": "0", "wfms_uuid": str(node.uuid)},
    )
    widget = OpenbisStructureImporterWidget(
        session=FakeSession([model]), eln_instance="https://openbis.example/"
    )
    widget._search()
    widget._load()

    assert widget.structure.uuid == node.uuid
    assert widget.structure.pk == node.pk
    assert f"PK {node.pk}" in widget.status.value
    assert "reusing it" in widget.status.value


@pytest.mark.usefixtures("aiida_profile_clean")
def test_extract_structure_archive_keeps_only_requested_node(tmp_path):
    selected = orm.StructureData(
        ase=ase.Atoms("CH4", cell=[10, 10, 10], pbc=False)
    ).store()
    unrelated = orm.Dict({"unrelated": True}).store()
    source = tmp_path / "source.aiida"
    create_archive(
        [selected, unrelated],
        source,
        create_backward=False,
        call_calc_backward=False,
        call_work_backward=False,
    )

    destination = tmp_path / "selected.aiida"
    extract_structure_archive(source, str(selected.uuid), destination)

    archive_format = ArchiveFormatSqlZip()
    with archive_format.open(destination, "r") as reader:
        nodes = (
            reader.querybuilder().append(orm.Node, project=["uuid", "node_type"]).all()
        )
    assert nodes == [[str(selected.uuid), selected.node_type]]


def test_openbis_connection_is_lazy(monkeypatch):
    calls = []
    session = FakeSession([])
    connector = SimpleNamespace(
        session=session,
        eln_instance="https://openbis.example/",
        eln_type="openbis",
    )

    def connect_to_eln(**kwargs):
        calls.append(kwargs)
        return connector, None

    monkeypatch.setattr(
        "aiidalab_eln.openbis.structure_importer.connect_to_eln",
        connect_to_eln,
    )

    widget = OpenbisStructureImporterWidget(eln_instance="https://openbis.example/")
    assert calls == []
    assert widget.session is None

    widget._search()

    assert calls == [{"eln_instance": "https://openbis.example/"}]
    assert widget.session is session
