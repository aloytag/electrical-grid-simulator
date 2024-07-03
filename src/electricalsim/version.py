from importlib.metadata import version, PackageNotFoundError

try:
    VERSION = version('electricalsim')
except PackageNotFoundError:
    VERSION = 'development version'

DATE = '2024-07-03'
AUTHOR = 'Dr. Ing. Ariel S. Loyarte'
CONTACT = 'aloyarte@frsf.utn.edu.ar'
