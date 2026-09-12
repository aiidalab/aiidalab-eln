"""Search and import structures from an openBIS ELN."""

from __future__ import annotations

import hashlib
import html
import json
import re
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path

import ase
import ase.data
import ase.formula
import ase.io
import ipywidgets as ipw
import numpy as np
import traitlets as tl
from aiida import orm
from aiida.common.exceptions import NotExistent
from aiida.tools.archive import create_archive, import_archive
from aiida.tools.archive.implementations.sqlite_zip.main import ArchiveFormatSqlZip
from aiidalab_widgets_empa import CdxmlUploadWidget

from ..elns import connect_to_eln

ELN_ORIGIN_EXTRA = "eln"
_ATOMISTIC_MODEL = "ATOMISTIC_MODEL"
_MOLECULE = "MOLECULE"
_AIIDA_NODE = "AIIDA_NODE"
_AIIDA_SOURCE = "__aiida_node__"
_SUPPORTED_STRUCTURE_SUFFIXES = {
    ".cif",
    ".extxyz",
    ".json",
    ".mol",
    ".pdb",
    ".poscar",
    ".sdf",
    ".vasp",
    ".xyz",
}


def _props(openbis_object) -> dict:
    values = openbis_object.props.all()
    return {str(key).lower(): value for key, value in values.items()}


def _type_code(openbis_object) -> str:
    object_type = getattr(openbis_object, "type", "")
    return str(getattr(object_type, "code", object_type))


def _permid(openbis_object) -> str:
    return str(getattr(openbis_object, "permId", ""))


def _normalise_references(value) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        value = (
            value.get("permId")
            or value.get("perm_id")
            or value.get("identifier")
            or value.get("code")
        )
        return (str(value),) if value else ()
    if isinstance(value, Iterable):
        references = []
        for item in value:
            references.extend(_normalise_references(item))
        return tuple(references)
    reference = (
        getattr(value, "permId", None)
        or getattr(value, "identifier", None)
        or getattr(value, "code", None)
    )
    return (str(reference),) if reference else ()


def _chemical_counts(formula: str) -> dict[str, int] | None:
    try:
        counts = ase.formula.Formula(str(formula), strict=True).count()
    except (ValueError, TypeError):
        return None
    return {str(symbol): int(count) for symbol, count in counts.items()}


def _parse_elements(value: str) -> set[str]:
    elements = set()
    for token in re.split(r"[\s,;]+", value.strip()):
        if not token:
            continue
        symbol = token[0].upper() + token[1:].lower()
        if symbol not in ase.data.atomic_numbers:
            raise ValueError(f"Unknown chemical element: {token}")
        elements.add(symbol)
    return elements


def structure_fingerprint(atoms: ase.Atoms) -> str:
    """Return a stable digest for identity checks, not structural similarity."""
    payload = {
        "symbols": atoms.get_chemical_symbols(),
        "positions": atoms.get_positions().round(12).tolist(),
        "cell": atoms.cell.array.round(12).tolist(),
        "pbc": [bool(value) for value in atoms.pbc],
    }
    serialised = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _ensure_auxiliary_cell(atoms: ase.Atoms, vacuum: float = 10.0) -> ase.Atoms:
    atoms = atoms.copy()
    if any(float(length) < 0.1 for length in atoms.cell.lengths()):
        atoms.cell = np.ptp(atoms.get_positions(), axis=0) + vacuum
        atoms.center()
    return atoms


def _read_structure_file(filename: str, content: bytes) -> ase.Atoms:
    suffix = Path(filename).suffix.lower()
    if suffix == ".json":
        try:
            from ase.io.jsonio import decode

            decoded = decode(content.decode("utf-8"))
            if isinstance(decoded, ase.Atoms):
                return decoded
        except (UnicodeDecodeError, ValueError, TypeError):
            pass

    with tempfile.NamedTemporaryFile(suffix=suffix) as handle:
        handle.write(content)
        handle.flush()
        structure = ase.io.read(handle.name)

    if isinstance(structure, list):
        if len(structure) != 1:
            raise ValueError(
                f"{filename} contains {len(structure)} structures; expected exactly one."
            )
        structure = structure[0]
    if not isinstance(structure, ase.Atoms):
        raise ValueError(f"{filename} does not contain an atomistic structure.")
    return _ensure_auxiliary_cell(structure)


def _read_cdxml(content: bytes) -> ase.Atoms:
    atoms = CdxmlUploadWidget.cdxml_to_ase_from_string(content.decode("utf-8"))
    _, atoms = CdxmlUploadWidget.add_hydrogen_atoms(atoms)
    atoms.pbc = False
    return _ensure_auxiliary_cell(atoms, vacuum=15.0)


def _dataset_files(openbis_object) -> tuple[tuple[object, str], ...]:
    files = []
    for dataset in list(openbis_object.get_datasets() or []):
        for filename in getattr(dataset, "file_list", ()) or ():
            files.append((dataset, str(filename)))
    return tuple(files)


def _download_dataset_file(dataset, filename: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="aiidalab-openbis-file-") as dirname:
        dataset.download(destination=dirname)
        candidates = [
            path
            for path in Path(dirname).rglob(Path(filename).name)
            if path.is_file()
            and (path.as_posix().endswith(filename) or path.name == Path(filename).name)
        ]
        if len(candidates) != 1:
            raise FileNotFoundError(
                f"Could not identify {filename!r} in dataset {_permid(dataset)}."
            )
        return candidates[0].read_bytes()


def _related_aiida_nodes(session, atomistic_model) -> tuple[object, ...]:
    """Return AIIDA_NODE objects referenced by direct simulation neighbours."""
    references = []
    neighbours = []
    for getter_name in ("get_parents", "get_children"):
        getter = getattr(atomistic_model, getter_name, None)
        if getter is not None:
            neighbours.extend(list(getter() or []))

    for neighbour in neighbours:
        if _type_code(neighbour) == _AIIDA_NODE:
            references.append(_permid(neighbour))
        references.extend(_normalise_references(_props(neighbour).get("aiida_node")))

    objects = []
    for reference in dict.fromkeys(references):
        try:
            candidate = session.get_object(reference)
        except (ValueError, KeyError):
            continue
        if _type_code(candidate) == _AIIDA_NODE:
            objects.append(candidate)
    return tuple(objects)


def _prepare_archive_version(source: Path, destination: Path) -> Path:
    archive_format = ArchiveFormatSqlZip()
    if archive_format.read_version(source) == archive_format.latest_version:
        return source
    migrated = destination / "migrated.aiida"
    archive_format.migrate(source, migrated, archive_format.latest_version, force=True)
    return migrated


def extract_structure_archive(
    source: str | Path,
    structure_uuid: str,
    destination: str | Path,
) -> Path:
    """Extract exactly one StructureData, preserving its UUID and repository."""
    source = Path(source)
    destination = Path(destination)
    archive_format = ArchiveFormatSqlZip()
    archive_source = _prepare_archive_version(source, destination.parent)

    with archive_format.open(archive_source, "r") as reader:
        try:
            node = reader.get(orm.Node, uuid=str(structure_uuid))
        except Exception as error:
            raise LookupError(
                f"The archive does not contain node {structure_uuid}."
            ) from error
        if not isinstance(node, orm.StructureData):
            raise TypeError(f"Node {structure_uuid} is not a StructureData.")
        create_archive(
            [node],
            destination,
            backend=reader.get_backend(),
            create_backward=False,
            call_calc_backward=False,
            call_work_backward=False,
            include_comments=False,
            include_logs=False,
        )

    with archive_format.open(destination, "r") as reader:
        nodes = (
            reader.querybuilder().append(orm.Node, project=["uuid", "node_type"]).all()
        )
    if len(nodes) != 1 or str(nodes[0][0]) != str(structure_uuid):
        raise RuntimeError(
            "Selective archive extraction did not produce exactly the requested node."
        )
    return destination


def _local_structure(structure_uuid: str) -> orm.StructureData | None:
    try:
        node = orm.load_node(structure_uuid)
    except (NotExistent, ValueError):
        return None
    if not isinstance(node, orm.StructureData):
        raise TypeError(f"AiiDA node {structure_uuid} is not a StructureData.")
    return node


def _restore_structure_from_openbis(
    session,
    atomistic_model,
    structure_uuid: str,
) -> orm.StructureData:
    local = _local_structure(structure_uuid)
    if local is not None:
        return local

    aiida_nodes = _related_aiida_nodes(session, atomistic_model)
    if not aiida_nodes:
        raise FileNotFoundError(
            "No directly linked AIIDA_NODE can provide the requested structure."
        )

    failures = []
    with tempfile.TemporaryDirectory(prefix="aiidalab-openbis-structure-") as dirname:
        directory = Path(dirname)
        for aiida_node in aiida_nodes:
            for dataset, filename in _dataset_files(aiida_node):
                if Path(filename).suffix.lower() != ".aiida":
                    continue
                try:
                    source = directory / (
                        f"{_permid(dataset).replace('/', '_')}-{Path(filename).name}"
                    )
                    source.write_bytes(_download_dataset_file(dataset, filename))
                    selected = directory / "selected.aiida"
                    if selected.exists():
                        selected.unlink()
                    extract_structure_archive(source, structure_uuid, selected)
                    import_archive(selected, create_group=False)
                    restored = _local_structure(structure_uuid)
                    if restored is None:
                        raise RuntimeError(
                            "AiiDA completed the import but the requested node is absent."
                        )
                    return restored
                except Exception as error:
                    failures.append(str(error))

    details = f" Checked archives: {'; '.join(failures)}" if failures else ""
    raise FileNotFoundError(
        f"No linked AiiDA archive contains StructureData {structure_uuid}.{details}"
    )


class OpenbisStructureImporterWidget(ipw.VBox):
    """A lazy, searchable structure importer for configured openBIS instances."""

    structure = tl.Union(
        [tl.Instance(ase.Atoms), tl.Instance(orm.Data)], allow_none=True
    )

    def __init__(
        self,
        title: str = "From openBIS",
        session=None,
        eln_instance: str | None = None,
        path_to_root: str = "../",
        **kwargs,
    ):
        self.title = title
        self.session = session
        self.eln_instance = (eln_instance or "").rstrip("/")
        self._requested_eln_instance = eln_instance
        self._path_to_root = path_to_root
        self._objects = {}
        self._sources = {}

        self.mode = ipw.ToggleButtons(
            options=[
                ("Atomistic model", _ATOMISTIC_MODEL),
                ("Molecular concept", _MOLECULE),
            ],
            value=_ATOMISTIC_MODEL,
            description="Import:",
            style={"description_width": "initial"},
        )
        self.name_filter = ipw.Text(
            description="Name or formula:",
            placeholder="Optional text filter",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="520px"),
        )
        self.dimensionality_filter = ipw.Dropdown(
            description="Dimensionality:",
            options=[("Any", None), ("0D", 0), ("1D", 1), ("2D", 2), ("3D", 3)],
            value=None,
            style={"description_width": "initial"},
        )
        self.elements_filter = ipw.Text(
            description="Contains elements:",
            placeholder="e.g. Au C O Co",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="520px"),
        )
        self.max_atoms_filter = ipw.BoundedIntText(
            description="Maximum atoms:",
            value=0,
            min=0,
            max=1_000_000,
            tooltip="Use 0 for no limit.",
            style={"description_width": "initial"},
        )
        self.filters = ipw.VBox()
        self.search_button = ipw.Button(
            description="Search", icon="search", button_style="primary"
        )
        self.results = ipw.Select(
            description="Results:",
            options=(),
            rows=8,
            style={"description_width": "initial"},
            layout=ipw.Layout(width="95%"),
        )
        self.source = ipw.Dropdown(
            description="Representation:",
            options=(),
            style={"description_width": "initial"},
            layout=ipw.Layout(width="95%"),
        )
        self.load_button = ipw.Button(
            description="Load structure", icon="download", disabled=True
        )
        self.status = ipw.HTML()

        self.mode.observe(self._mode_changed, names="value")
        self.results.observe(self._selection_changed, names="value")
        self.source.observe(self._source_changed, names="value")
        self.search_button.on_click(self._search)
        self.load_button.on_click(self._load)
        self._mode_changed()

        super().__init__(
            children=[
                self.mode,
                self.filters,
                self.search_button,
                self.results,
                self.source,
                self.load_button,
                self.status,
            ],
            **kwargs,
        )

    def _ensure_session(self):
        if self.session is not None:
            return True
        connector, message = connect_to_eln(eln_instance=self._requested_eln_instance)
        if connector is None or getattr(connector, "eln_type", "") != "openbis":
            self.status.value = (
                "<div class='alert alert-warning'>"
                f"{html.escape(str(message or 'The configured ELN is not openBIS.'))}"
                f" Configure it in {html.escape(self._path_to_root)}aiidalab-eln."
                "</div>"
            )
            return False
        self.session = connector.session
        self.eln_instance = str(connector.eln_instance).rstrip("/")
        return True

    def _mode_changed(self, _change=None):
        atomistic = self.mode.value == _ATOMISTIC_MODEL
        self.dimensionality_filter.layout.display = "" if atomistic else "none"
        self.elements_filter.layout.display = "" if atomistic else "none"
        self.max_atoms_filter.layout.display = "" if atomistic else "none"
        self.name_filter.description = (
            "Name or formula:" if atomistic else "Number, name, or formula:"
        )
        self.filters.children = [
            self.name_filter,
            self.dimensionality_filter,
            self.elements_filter,
            self.max_atoms_filter,
        ]
        self.results.options = ()
        self.source.options = ()
        self.load_button.disabled = True
        self.structure = None
        self.status.value = ""

    def _search(self, _button=None):
        if not self._ensure_session():
            return
        self.status.value = "<em>Searching openBIS...</em>"
        try:
            required_elements = (
                _parse_elements(self.elements_filter.value)
                if self.mode.value == _ATOMISTIC_MODEL
                else set()
            )
            objects = list(self.session.get_objects(type=self.mode.value) or [])
            query_tokens = self.name_filter.value.lower().split()
            matches = []
            self._objects = {}
            for openbis_object in objects:
                properties = _props(openbis_object)
                searchable = " ".join(
                    str(properties.get(key) or "")
                    for key in (
                        "empa_number",
                        "name",
                        "sum_formula",
                        "description",
                        "comments",
                    )
                ).lower()
                if any(token not in searchable for token in query_tokens):
                    continue

                if self.mode.value == _ATOMISTIC_MODEL:
                    dimensionality = properties.get("dimensionality")
                    selected_dimensionality = self.dimensionality_filter.value
                    if selected_dimensionality is not None and str(
                        dimensionality
                    ) != str(selected_dimensionality):
                        continue
                    counts = _chemical_counts(properties.get("name", ""))
                    if required_elements and (
                        counts is None or not required_elements.issubset(counts)
                    ):
                        continue
                    maximum = self.max_atoms_filter.value
                    if maximum and (counts is None or sum(counts.values()) > maximum):
                        continue
                    count_label = (
                        f"{sum(counts.values())} atoms"
                        if counts is not None
                        else "atoms unknown"
                    )
                    label = (
                        f"{properties.get('name') or 'Unnamed'} - "
                        f"{dimensionality if dimensionality is not None else '?'}D - "
                        f"{count_label} - {_permid(openbis_object)}"
                    )
                else:
                    number = properties.get("empa_number")
                    name = properties.get("name") or "Unnamed"
                    formula = properties.get("sum_formula") or "formula unavailable"
                    prefix = f"{number} - " if number else ""
                    label = f"{prefix}{name} - {formula} - {_permid(openbis_object)}"

                identifier = _permid(openbis_object)
                self._objects[identifier] = openbis_object
                matches.append((label, identifier))

            matches.sort(key=lambda item: item[0].lower())
            self.results.options = matches
            if matches:
                self.results.value = matches[0][1]
            self.status.value = (
                f"<b>{len(matches)}</b> matching "
                f"{'atomistic models' if self.mode.value == _ATOMISTIC_MODEL else 'molecular concepts'}."
            )
        except Exception as error:
            self.results.options = ()
            self.status.value = (
                "<div class='alert alert-danger'>Search failed: "
                f"{html.escape(str(error))}</div>"
            )

    def _selection_changed(self, _change=None):
        self.source.options = ()
        self._sources = {}
        identifier = self.results.value
        if not identifier:
            self.load_button.disabled = True
            return

        openbis_object = self._objects[identifier]
        properties = _props(openbis_object)
        options = []

        if self.mode.value == _ATOMISTIC_MODEL and properties.get("wfms_uuid"):
            self._sources[_AIIDA_SOURCE] = ("aiida", None, None)
            options.append(
                (
                    f"Original AiiDA StructureData ({properties['wfms_uuid']})",
                    _AIIDA_SOURCE,
                )
            )
        else:
            for dataset, filename in _dataset_files(openbis_object):
                suffix = Path(filename).suffix.lower()
                if suffix == ".cdxml" and self.mode.value == _MOLECULE:
                    kind = "cdxml"
                elif suffix in _SUPPORTED_STRUCTURE_SUFFIXES:
                    kind = "file"
                else:
                    continue
                source_id = f"{_permid(dataset)}::{filename}"
                self._sources[source_id] = (kind, dataset, filename)
                label = (
                    f"Planar CDXML - {Path(filename).name}"
                    if kind == "cdxml"
                    else f"Stored geometry - {Path(filename).name}"
                )
                options.append((label, source_id))

            if self.mode.value == _MOLECULE and properties.get("smiles"):
                self._sources["__smiles__"] = ("smiles", None, None)
                options.append(("3D geometry generated from SMILES", "__smiles__"))

        self.source.options = options
        if options:
            self.source.value = options[0][1]
        self.load_button.disabled = not bool(options)
        if not options:
            self.status.value = (
                "<div class='alert alert-warning'>No supported structural "
                "representation is available for this object.</div>"
            )

    def _source_changed(self, _change=None):
        self.load_button.disabled = not bool(self.source.value)

    def _origin(self, openbis_object, representation: str, dataset=None, filename=None):
        origin = {
            "eln_instance": self.eln_instance,
            "eln_type": "openbis",
            "sample_uuid": _permid(openbis_object),
            "data_type": self.mode.value,
            "representation": representation,
        }
        if dataset is not None:
            origin["dataset_uuid"] = _permid(dataset)
        if filename:
            origin["source_file"] = filename
        return origin

    def _concept_structure(self, openbis_object, source_kind, dataset, filename):
        properties = _props(openbis_object)
        if source_kind == "smiles":
            import aiidalab_widgets_base as awb

            generator = awb.SmilesWidget(add_auxiliary_cell=True)
            atoms = generator._mol_from_smiles(str(properties["smiles"]))
            if atoms is None:
                raise ValueError(generator.output.value or "Could not generate SMILES.")
        else:
            content = _download_dataset_file(dataset, filename)
            atoms = (
                _read_cdxml(content)
                if source_kind == "cdxml"
                else _read_structure_file(filename, content)
            )

        origin = self._origin(
            openbis_object, source_kind, dataset=dataset, filename=filename
        )
        origin["structure_fingerprint"] = structure_fingerprint(atoms)
        atoms.info[ELN_ORIGIN_EXTRA] = dict(origin)
        node = orm.StructureData(ase=atoms)
        node.base.extras.set(ELN_ORIGIN_EXTRA, origin)
        return node

    def _manual_atomistic_structure(
        self, openbis_object, source_kind, dataset, filename
    ):
        atoms = _read_structure_file(
            filename, _download_dataset_file(dataset, filename)
        )
        origin = self._origin(
            openbis_object, source_kind, dataset=dataset, filename=filename
        )
        origin["structure_fingerprint"] = structure_fingerprint(atoms)
        atoms.info[ELN_ORIGIN_EXTRA] = dict(origin)
        node = orm.StructureData(ase=atoms)
        node.base.extras.set(ELN_ORIGIN_EXTRA, origin)
        return node

    def _load(self, _button=None):
        identifier = self.results.value
        source_id = self.source.value
        if not identifier or not source_id:
            return
        self.status.value = "<em>Loading structure...</em>"
        self.load_button.disabled = True
        try:
            openbis_object = self._objects[identifier]
            source_kind, dataset, filename = self._sources[source_id]
            if self.mode.value == _ATOMISTIC_MODEL:
                if source_kind == "aiida":
                    structure_uuid = str(_props(openbis_object)["wfms_uuid"])
                    was_local = _local_structure(structure_uuid) is not None
                    structure = _restore_structure_from_openbis(
                        self.session, openbis_object, structure_uuid
                    )
                else:
                    structure = self._manual_atomistic_structure(
                        openbis_object, source_kind, dataset, filename
                    )
            else:
                structure = self._concept_structure(
                    openbis_object, source_kind, dataset, filename
                )
            self.structure = structure
            if (
                self.mode.value == _ATOMISTIC_MODEL
                and source_kind == "aiida"
                and was_local
            ):
                message = (
                    "Structure already present in the local AiiDA database "
                    f"(PK {structure.pk}); reusing it."
                )
            else:
                message = f"Loaded {getattr(structure, 'uuid', identifier)}."
            self.status.value = (
                "<div class='alert alert-success'>" f"{html.escape(str(message))}</div>"
            )
        except Exception as error:
            self.structure = None
            self.status.value = (
                "<div class='alert alert-danger'>Import failed: "
                f"{html.escape(str(error))}</div>"
            )
        finally:
            self.load_button.disabled = not bool(self.source.value)
