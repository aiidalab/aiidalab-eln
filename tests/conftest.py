import json
import uuid

import pytest

pytest_plugins = ["aiida.tools.pytest_fixtures"]


@pytest.fixture
def mock_eln_config():
    """Backup the ELN_CONFIG file and restore it after the test."""

    class _MockElnConfig:
        """Mock the ELN_CONFIG file."""

        def mock(self, original_config):
            """Backup the eln config file if it exists."""
            self.original_config = original_config
            self.backup_config_name = None
            if self.original_config.exists():
                self.backup_config_name = self.original_config.with_suffix(
                    f".bak.{uuid.uuid4()}"
                )
                self.original_config.rename(self.backup_config_name)

        def restore(self):
            """Restore the eln config file if it existed and delete the test one."""
            if self.original_config.exists():
                self.original_config.unlink()

            if self.backup_config_name and self.backup_config_name.exists():
                self.backup_config_name.rename(self.original_config)

        def populate_mock_config_with_cheminfo(self):
            """Populate the mock config file with cheminfo credentials."""

            dictionary = {
                "https://mydb.cheminfo.org/": {
                    "eln_type": "cheminfo",
                    "token": "1234567890abcdef",
                },
                "default": "https://mydb.cheminfo.org/",
            }
            self.write(dictionary)

        def write(self, config_dictionary):
            """Write a config dictionary to the config file."""
            with open(self.original_config, "w") as f:
                json.dump(config_dictionary, f)

        def get(self):
            """Return the path to the config file."""
            with open(self.original_config) as f:
                return json.load(f)

    return _MockElnConfig()
