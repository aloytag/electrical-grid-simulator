from importlib.metadata import version, PackageNotFoundError

try:
    VERSION = version('electricalsim')
except PackageNotFoundError:
    VERSION = 'development version'

<<<<<<< HEAD
DATE = '2024-09-25'
=======
DATE = '2024-09-02'
>>>>>>> 11f8ffbaa463d32ef0aaf17548bb014e5a0d8f18
AUTHOR = 'Dr. Ing. Ariel S. Loyarte'
CONTACT = 'aloyarte@frsf.utn.edu.ar'
