# -*- coding: utf-8 -*-
"""Describe the module distribution to the Distutils."""
import json

from setuptools import find_packages, setup

with open("README.md", "r") as readme_handle:
    long_description = readme_handle.read()

with open("setup.json", "r", encoding="utf-8") as info:
    kwargs = json.load(info)
setup(
    include_package_data=True,
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    **kwargs
)
