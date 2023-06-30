from importlib.metadata import version, PackageNotFoundError

try:
    VERSION = version('electricalsim')
except PackageNotFoundError:
    VERSION = 'development version'

DATE = '2023-06-30'
AUTHOR = 'PhD Ariel S. Loyarte'
CONTACT = 'aloyarte@frsf.utn.edu.ar'
