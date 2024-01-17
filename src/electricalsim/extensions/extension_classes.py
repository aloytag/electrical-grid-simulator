#  -*- coding: utf-8 -*-

import os

from PySide6.QtUiTools import QUiLoader
from PySide6 import QtCore, QtGui, QtWidgets
import qtawesome as qta


directory = os.path.dirname(__file__)
root_dir, _ = os.path.split(directory)
extension_dialog_ui_path = os.path.join(root_dir, 'ui', 'extension.ui')
icon_path = os.path.join(root_dir, 'icons', 'app_icon.png')


class WorkerSignals(QtCore.QObject):
    """
    Signals for the extension worker in case of running in a
    separate thread.
    """
    data_signal = QtCore.Signal(str)
    finished = QtCore.Signal()


class StandardExtensionWin(QtWidgets.QDialog):
    """
    Standard extension dialog.
    """
    def __init__(self, extension_object):
        super().__init__()
        # self.w = QtCompat.loadUi(uifile=extension_dialog_ui_path)
        ui_file_ = QtCore.QFile(extension_dialog_ui_path)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        self.w = loader.load(ui_file_)
        self.w.setWindowIcon(QtGui.QIcon(icon_path))
        font = QtGui.QFont('unexistent')
        font.setStyleHint(QtGui.QFont.Monospace)
        self.w.text_output.setFont(font)

        self.ex_obj = extension_object

        self.w.run_btn.clicked.connect(self.run)
        self.w.clipboard_btn.clicked.connect(self.copy_to_clipboard)

        icon_size = QtCore.QSize(24, 24)
        self.w.close_btn.setIconSize(icon_size)
        self.w.close_btn.setIcon(qta.icon('mdi6.cancel'))
        self.w.clipboard_btn.setIconSize(icon_size)
        self.w.clipboard_btn.setIcon(qta.icon('mdi6.content-copy'))
        self.w.run_btn.setIconSize(icon_size)
        self.w.run_btn.setIcon(qta.icon('mdi6.play-circle-outline'))

    def run(self):
        """
        Runs the extension code when the dialog is opened.

        Returns: None

        """
        self.ex_obj.before_running()

        if self.ex_obj.separate_thread() is True:
            ex_wkr = ExtensionWorker(self.ex_obj)
            ex_wkr.signals.data_signal.connect(self.print_from_thread)
            ex_wkr.signals.finished.connect(self.ex_obj.finish)
            self.ex_obj.worker = ex_wkr
            ex_threadpool = QtCore.QThreadPool()
            ex_threadpool.start(ex_wkr)
        else:
            self.ex_obj()
            self.ex_obj.finish()

    def copy_to_clipboard(self):
        """
        Copy the output content to the clipboard.
        """
        cl = QtWidgets.QApplication.clipboard()
        txt = self.w.text_output.toPlainText()
        cl.setText(txt)

    def print_from_thread(self, data):
        self.w.text_output.appendPlainText(data)


class ExtensionWorker(QtCore.QRunnable):
    """
    Worker class for running extensions in a separate thread.
    """
    def __init__(self, extension_obj):
        """
        Args:
            extension_obj: Extension object (derived from 'ExtensionBase' class)
        """
        super(ExtensionWorker, self).__init__()
        self.extension_obj = extension_obj
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        print("Extension thread start")
        self.extension_obj()
        self.signals.finished.emit()
        print("Extension thread complete")


class ExtensionBase:
    """
    Base class for creating extensions.
    """
    def __init__(self, **kwargs):
        if 'graph' in kwargs:
            self.graph = kwargs['graph']
            self.net = self.graph.net
            self.__config_dir, _ = os.path.split(self.graph.config_file_path)
        else:
            self.__config_dir = None

        self.__separate_thread = False
        self.__extension_window = True
        self.standard_extension_win = StandardExtensionWin(self)
        self.__name = ''  # Extension name
        self.worker = None  # ExtensionWorker instance
        self.__egs_icon = QtGui.QIcon(icon_path)

    def set_separate_thread(self, bool_value):
        """
        Indicates whether the calculation must run on a separate thread.

        Args:
            bool_value: True or False

        Returns: None

        """
        self.__separate_thread = bool_value

    def separate_thread(self):
        """
        Returns a boolean that indicates whether the calculation runs in a separate thread.
        """
        return self.__separate_thread

    def set_extension_window(self, bool_value):
        """
        Indicates whether the extension uses the standard window.

        Args:
            bool_value: True or False

        Returns: None

        """
        self.__extension_window = bool_value

    def extension_window(self):
        """
        Returns a boolean that indicates whether the extension uses the standard window.
        """
        return self.__extension_window

    def clear_output(self):
        """
        Clears the output on the standard extension dialog.

        Returns: None

        """
        self.standard_extension_win.w.text_output.clear()

    def default_path(self):
        """
        Returns the default directory path.
        """
        return self.graph.config['general']['default_path']

    def set_name(self, name):
        """
        Sets the extension name for the standard dialog.
        Args:
            name: Extension name

        Returns: None

        """
        self.__name = name
        self.standard_extension_win.w.extension_name.setText(name)

    def name(self):
        """
        Returns the extension name.
        """
        return self.__name

    def egs_icon(self):
        """
        Returns the EGS icon (QIcon object).
        """
        return self.__egs_icon

    def show_dialog(self):
        """
        Shows the standard extension dialog.

        Returns: None

        """
        self.standard_extension_win.w.setWindowTitle(f'Extension: {self.__name}')
        self.standard_extension_win.w.exec()

    def config_dir(self):
        """
        Returns the config directory path.
        """
        return self.__config_dir

    def print(self, data):
        """
        Prints 'data' on the standard extension window.
        First it is necessary to execute self.set_extension_window(True).

        Returns: None

        """
        if self.__extension_window is False:
            return

        if self.__separate_thread is False:
            self.standard_extension_win.w.text_output.appendPlainText(str(data))
        else:
            self.worker.signals.data_signal.emit(str(data))

    def before_running(self):
        """
        Virtual function excecuted in the main thread just after
        the __init__() method and before __call__().

        When the standard extension window is used, it is excecuted
        after clicking on the Run button.
        """
        pass

    def finish(self):
        """
        Virtual function excecuted in the main thread after the __call__() method.
        """
        pass
