import io
import requests
from aiida.plugins import DataFactory

CifData = DataFactory('cif')  # pylint: disable=invalid-name


def get_cif(url, token):
    req = requests.get(f'{url}?token={token}', allow_redirects=False)
    return CifData(file=io.BytesIO(req.content))
