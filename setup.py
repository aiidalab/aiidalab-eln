import json
from io import open
from setuptools import setup, find_packages

with open('setup.json', 'r', encoding='utf-8') as info:
    kwargs = json.load(info)
setup(include_package_data=True,
      packages=find_packages(),
      long_description=open('README.md', encoding='utf-8').read(),
      long_description_content_type='text/markdown',
      **kwargs)

