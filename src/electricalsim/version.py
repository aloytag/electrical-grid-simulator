import os
import tomllib
from importlib.metadata import version, PackageNotFoundError

directory = os.path.dirname(__file__)
root_dir, _ = os.path.split(os.path.split(directory)[0])
pyproject = os.path.join(root_dir, 'pyproject.toml')

if os.path.exists(pyproject):
    with open(pyproject, 'rb') as f:
        data = tomllib.load(f)
    version_ = data['project']['version']
    VERSION = version_ + ' (dev version)'
else:
    try:
        VERSION = version('electricalsim')
    except PackageNotFoundError:
        VERSION = 'development version'

DATE = '2025-08-27'
AUTHOR = 'Dr. Ing. Ariel S. Loyarte'
CONTACT = 'aloyarte@frsf.utn.edu.ar'
