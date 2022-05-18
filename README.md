# AiiDAlab-ELN

[![Continuous Integration](https://github.com/aiidalab/aiidalab-eln/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/aiidalab/aiidalab-eln/actions/workflows/pre-commit.yml)

Integrate AiiDAlab with Electronic Laboratory Notebooks (ELN). This repository implements a general API for interfacing AiiDAlab with some ELN and a concrete implementation for the integration with the [cheminfo ELN](cheminfo.github.io/).

## AiiDAlab-Cheminfo ELN implementation

As a first prototype we implemented an integration with the open-source [cheminfo ELN](cheminfo.github.io/).
The ELN and integration can be tested via the [public deployment of the ELN](c6h6.org). Documentation on how to use the frontend can be found [here](docs.c6h6.org).

## API

- `eln_instance` refers to the URL of the ELN API.
- `eln_type` referst to the type of ELN, e.g. "cheminfo", "openbis".
- `data_type` "subfolder" in the cheminfo data schema of characterization techniques, e.g., "xray", "isotherm" `spectrum_type` will be renamed to this
- `sample_uuid` refers to the sample unique identifier in the ELN database
- `file_name` refers to the name of the file attached to the sample and containing information of the specified `data_type`.
- `file_content` refers to the content of the file attached to the sample.
- `node` refers to the AiiDA database node.
- `token` refers to the token that gives access to the ELN database.
- `export_data()` sends the AiiDA node (stored in the `node` attribute) to the ELN.
- `import_data()` import ELN data into an AiiDA node.
- `sample` object that refers to an ELN sample, previously known as `sample_manager`.
- `sample.put_data()` - put data into the ELN sample.
- `sample.get_data()` - get data from the ELN sample.

## For maintainers

To create a new release, clone the repository, install development dependencies with `pip install '.[dev]'`, and then execute `bumpver update --major/--minor/--patch`.
This will:

  1. Create a tagged release with bumped version and push it to the repository.
  2. Trigger a GitHub actions workflow that creates a GitHub release.

Additional notes:

  - Use the `--dry` option to preview the release change.
  - The release tag (e.g. a/b/rc) is determined from the last release.
    Use the `--tag` option to switch the release tag.

## Acknowledgements

This work is supported by the [MARVEL National Centre for Competency in Research](<http://nccr-marvel.ch>)
funded by the [Swiss National Science Foundation](<http://www.snf.ch/en>), as well as by the [MaX
European Centre of Excellence](<http://www.max-centre.eu/>) funded by the Horizon 2020 EINFRA-5 program,
Grant No. 676598 and an European Research Council (ERC) Advanced Grant (Grant Agreement No. 666983, MaGic).

<div style="text-align:center">
 <img src="miscellaneous/logos/MARVEL.png" alt="MARVEL" height="75px">
 <img src="miscellaneous/logos/MaX.png" alt="MaX" height="75px">
</div>
