"""Module allowing for `python -m qdarktheme2.widget_gallery`."""
import sys

import qdarktheme2
from qdarktheme2.qtpy.QtWidgets import QApplication
from qdarktheme2.widget_gallery.main_window import WidgetGallery

if __name__ == "__main__":
    qdarktheme2.enable_hi_dpi()
    app = QApplication(sys.argv)
    qdarktheme2.setup_theme("auto")
    win = WidgetGallery()
    win.show()
    app.exec()
