"""Package applying Qt compat of PyQt6, PySide6, PyQt5 and PySide2."""
from qdarktheme2.qtpy.qt_compat import QtImportError
from qdarktheme2.qtpy.qt_version import __version__

try:
    from qdarktheme2.qtpy import QtCore, QtGui, QtSvg, QtWidgets
except ImportError:
    from qdarktheme2._util import get_logger as __get_logger

    __logger = __get_logger(__name__)
    __logger.warning("Failed to import QtCore, QtGui, QtSvg and QtWidgets.")
