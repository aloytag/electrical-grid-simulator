# -*- coding: utf-8 -*-

import os
from pathlib import Path
import configparser
from concurrent.futures import Future

import pandas as pd
import pandapower as pp

from PySide6.QtUiTools import QUiLoader
from PySide6 import QtGui, QtCore, QtWidgets
import qtawesome as qta
import qdarktheme

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.ticker import MaxNLocator
from matplotlib import rc

from fuzzysearch import find_near_matches

from lib.table_widget import TableWidget
from lib.auxiliary import icon_for_type, natsort2
from version import VERSION, DATE, AUTHOR, CONTACT

directory = os.path.dirname(__file__)
font = {'family' : 'sans-serif',
        'weight' : 'regular',
        'size'   : 14}
rc('font', **font)


def return_qtwindow(path_ui_file):
    """
    Retuns the Qt window from de .ui file path.
    """
    ui_file_ = QtCore.QFile(path_ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    window = loader.load(ui_file_)  # window
    return window


def about_dialog():
    """
    Returns the about dialog.
    """
    ui_file = os.path.join(directory, 'about_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    root_dir, _ = os.path.split(directory)
    
    app_logo_img_path = os.path.join(root_dir, 'icons', 'app_icon.png')
    app_logo = QtGui.QPixmap(app_logo_img_path)
    # app_logo = app_logo.scaled(300, 300, QtCore.Qt.KeepAspectRatio)
    app_logo = app_logo.scaledToWidth(290, QtCore.Qt.SmoothTransformation)
    dialog.img1.setPixmap(app_logo)
    
    institution_logo_img_path = os.path.join(root_dir, 'icons',
                                             'CIESE_UTN_Sta_Fe.png')
    institution_logo = QtGui.QPixmap(institution_logo_img_path)
    # institution_logo = institution_logo.scaled(300, 300,
    #                                            QtCore.Qt.KeepAspectRatio)
    institution_logo = institution_logo.scaledToWidth(290, QtCore.Qt.SmoothTransformation)
    dialog.img2.setPixmap(institution_logo)
    
    dialog.description.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
    dialog.description.setOpenExternalLinks(True)
    
    dialog.version.setText(VERSION)
    dialog.date.setText(DATE)
    dialog.author.setText(f'{AUTHOR} ({CONTACT})')
    
    return dialog


def bus_dialog():
    """
    Returns the bus dialog.
    """
    ui_file = os.path.join(directory, 'bus_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def min_vm_pu_changed(value):
        dialog.max_vm_pu.setMinimum(value)
        
    def max_vm_pu_changed(value):
        dialog.min_vm_pu.setMaximum(value)
    
    dialog.min_vm_pu.valueChanged.connect(min_vm_pu_changed)
    dialog.max_vm_pu.valueChanged.connect(max_vm_pu_changed)
    
    return dialog


def line_dialog():
    """
    Returns the line dialog.
    """
    ui_file = os.path.join(directory, 'line_dialog.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # return QtCompat.loadUi(uifile=ui_file)
    return dialog


def stdline_dialog(dataframe_stds, selected_std):
    """
    Returns the standard line dialog.
    
    dataframe_stds: pandas DataFrame with standard line parameters, obtained
                    with pp.available_std_types(self.net, 'line').
    selected_std: Name of the selected standard.
    """
    ui_file = os.path.join(directory, 'stdline_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    stds = dataframe_stds.index.tolist()
    dialog.std_type.addItems(stds)
    index_std = stds.index(selected_std)
    dialog.std_type.setCurrentIndex(index_std)
    
    pre_table = dataframe_stds.iloc[index_std, :]
    table_data = pd.DataFrame(data=pre_table.values,
                        index=pre_table.index,
                        columns=['Parameter'])
    
    table_std = TableWidget(table_data)
    dialog.layout_table.addWidget(table_std)
    height = table_std.table.horizontalHeader().height()
    for row in range(table_std.model.rowCount(None)):
        height += table_std.table.rowHeight(row)
    dialog.widget_table_container.setMinimumHeight(height * 1.2)
    
    def update_table(std_name):
        old_table = dialog.layout_table.itemAt(0).widget()
        old_table.setParent(None)
        
        index_std = stds.index(std_name)
        
        pre_table = dataframe_stds.iloc[index_std, :]
        table_data = pd.DataFrame(data=pre_table.values,
                            index=pre_table.index,
                            columns=['Parameter'])
        
        table_std = TableWidget(table_data)
        dialog.layout_table.addWidget(table_std)
        
        height = table_std.table.horizontalHeader().height()
        for row in range(table_std.model.rowCount(None)):
            height += table_std.table.rowHeight(row)
        dialog.widget_table_container.setMinimumHeight(height * 1.2)
    
    dialog.std_type.currentTextChanged.connect(update_table)
    
    return dialog


def dcline_dialog():
    """
    Returns the DC line dialog.
    """
    ui_file = os.path.join(directory, 'dcline_dialog.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # return QtCompat.loadUi(uifile=ui_file)
    return dialog


def impedance_dialog():
    """
    Returns the impedance dialog.
    """
    ui_file = os.path.join(directory, 'impedance_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def change_state_check1(state):
        dialog.rtf_pu.setEnabled(not state)
        dialog.xtf_pu.setEnabled(not state)
        if state:
            dialog.rtf_pu.setValue(dialog.rft_pu.value())
            dialog.xtf_pu.setValue(dialog.xft_pu.value())
        
    def change_state_check2(state):
        dialog.rtf0_pu.setEnabled(not state)
        dialog.xtf0_pu.setEnabled(not state)
        if state:
            dialog.rtf0_pu.setValue(dialog.rft0_pu.value())
            dialog.xtf0_pu.setValue(dialog.xft0_pu.value())
        
    def repeat_to_from(value):
        if dialog.check1.isChecked():
            dialog.rtf_pu.setValue(dialog.rft_pu.value())
            dialog.xtf_pu.setValue(dialog.xft_pu.value())
            
    def repeat_to_from_0(value):
        if dialog.check2.isChecked():
            dialog.rtf0_pu.setValue(dialog.rft0_pu.value())
            dialog.xtf0_pu.setValue(dialog.xft0_pu.value())
        
    dialog.check1.toggled.connect(change_state_check1)
    dialog.check2.toggled.connect(change_state_check2)
    dialog.rft_pu.valueChanged.connect(repeat_to_from)
    dialog.xft_pu.valueChanged.connect(repeat_to_from)
    dialog.rft0_pu.valueChanged.connect(repeat_to_from_0)
    dialog.xft0_pu.valueChanged.connect(repeat_to_from_0)
    
    return dialog


def choose_transformer_dialog():
    """
    Returns the dialog for selecting the transformer type to add.
    """
    ui_file = os.path.join(directory, 'choose_transformer_type.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # return QtCompat.loadUi(uifile=ui_file)
    return dialog


def choose_line_dialog():
    """
    Returns the dialog for selecting the line type to add (AC or DC line).
    """
    ui_file = os.path.join(directory, 'choose_line_type.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # return QtCompat.loadUi(uifile=ui_file)
    return dialog


def choose_generator_dialog():
    """
    Returns the dialog for selecting the generator type to add
    (voltage-controlled gen., static gen. or asymmetric static gen.).
    """
    ui_file = os.path.join(directory, 'choose_generator_type.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # return QtCompat.loadUi(uifile=ui_file)
    return dialog


def choose_bus_switch_dialog():
    """
    Returns the dialog for selecting a bus in order to add
    a switch.
    """
    ui_file = os.path.join(directory, 'choose_bus_switch.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # return QtCompat.loadUi(uifile=ui_file)
    return dialog


def transformer_dialog():
    """
    Returns the dialog for a two-winding transformer.
    """
    ui_file = os.path.join(directory, 'transformer_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def tap_min_changed(value):
        dialog.tap_pos.setMinimum(value)
        dialog.tap_neutral.setMinimum(value)
        
        if value>dialog.tap_max.value():
            dialog.tap_max.setValue(value)
        if value>dialog.tap_pos.value():
            dialog.tap_pos.setValue(value)
    
    def tap_max_changed(value):
        dialog.tap_pos.setMaximum(value)
        dialog.tap_neutral.setMaximum(value)
        
        if value<dialog.tap_min.value():
            dialog.tap_min.setValue(value)
        if value<dialog.tap_pos.value():
            dialog.tap_pos.setValue(value)
    
    dialog.tap_min.valueChanged.connect(tap_min_changed)
    dialog.tap_max.valueChanged.connect(tap_max_changed)
    
    return dialog


def stdtransformer_dialog(dataframe_stds, selected_std):
    """
    Returns the standard 2W-transformer dialog.
    
    dataframe_stds: pandas DataFrame with standard 2W-transformer parameters, obtained
                    with pp.available_std_types(self.net, 'trafo3w').
    selected_std: Name of the selected standard.
    """
    ui_file = os.path.join(directory, 'stdtransformer_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    stds = dataframe_stds.index.tolist()
    dialog.std_type.addItems(stds)
    index_std = stds.index(selected_std)
    dialog.std_type.setCurrentIndex(index_std)
    
    pre_table = dataframe_stds.iloc[index_std, :]
    table_data = pd.DataFrame(data=pre_table.values,
                        index=pre_table.index,
                        columns=['Parameter'])
    
    table_std = TableWidget(table_data)
    dialog.layout_table.addWidget(table_std)
    
    def update_table(std_name):
        old_table = dialog.layout_table.itemAt(0).widget()
        old_table.setParent(None)
        
        index_std = stds.index(std_name)
        
        pre_table = dataframe_stds.iloc[index_std, :]
        table_data = pd.DataFrame(data=pre_table.values,
                            index=pre_table.index,
                            columns=['Parameter'])
        
        table_std = TableWidget(table_data)
        dialog.layout_table.addWidget(table_std)
        
        dialog.tap_pos.setMinimum(table_data.at['tap_min', 'Parameter'])
        dialog.tap_pos.setMaximum(table_data.at['tap_max', 'Parameter'])
        dialog.tap_pos.setValue(table_data.at['tap_neutral', 'Parameter'])
        dialog.tap_pos_display.setText(str(table_data.at['tap_neutral', 'Parameter']))
        
        # height = table_std.table.horizontalHeader().height()
        # for row in range(table_std.model.rowCount(None)):
        #     height += table_std.table.rowHeight(row)
        # dialog.widget_table_container.setMinimumHeight(height * 1.2)
    
    dialog.std_type.currentTextChanged.connect(update_table)
    
    return dialog


def transformer3w_dialog():
    """
    Returns the dialog for a three-winding transformer.
    """
    ui_file = os.path.join(directory, 'transformer3w_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def tap_min_changed(value):
        dialog.tap_pos.setMinimum(value)
        dialog.tap_neutral.setMinimum(value)
        
        if value>dialog.tap_max.value():
            dialog.tap_max.setValue(value)
        if value>dialog.tap_pos.value():
            dialog.tap_pos.setValue(value)
    
    def tap_max_changed(value):
        dialog.tap_pos.setMaximum(value)
        dialog.tap_neutral.setMaximum(value)
        
        if value<dialog.tap_min.value():
            dialog.tap_min.setValue(value)
        if value<dialog.tap_pos.value():
            dialog.tap_pos.setValue(value)
    
    dialog.tap_min.valueChanged.connect(tap_min_changed)
    dialog.tap_max.valueChanged.connect(tap_max_changed)
    
    return dialog


def stdtransformer3w_dialog(dataframe_stds, selected_std):
    """
    Returns the standard 3W-transformer dialog.
    
    dataframe_stds: pandas DataFrame with standard 3W-transformer parameters, obtained
                    with pp.available_std_types(self.net, 'trafo3w').
    selected_std: Name of the selected standard.
    """
    ui_file = os.path.join(directory, 'stdtransformer3w_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    stds = dataframe_stds.index.tolist()
    dialog.std_type.addItems(stds)
    index_std = stds.index(selected_std)
    dialog.std_type.setCurrentIndex(index_std)
    
    pre_table = dataframe_stds.iloc[index_std, :]
    table_data = pd.DataFrame(data=pre_table.values,
                        index=pre_table.index,
                        columns=['Parameter'])
    
    table_std = TableWidget(table_data)
    dialog.layout_table.addWidget(table_std)
    
    def update_table(std_name):
        old_table = dialog.layout_table.itemAt(0).widget()
        old_table.setParent(None)
        
        index_std = stds.index(std_name)
        
        pre_table = dataframe_stds.iloc[index_std, :]
        table_data = pd.DataFrame(data=pre_table.values,
                            index=pre_table.index,
                            columns=['Parameter'])
        
        table_std = TableWidget(table_data)
        dialog.layout_table.addWidget(table_std)
        
        dialog.tap_pos.setMinimum(table_data.at['tap_min', 'Parameter'])
        dialog.tap_pos.setMaximum(table_data.at['tap_max', 'Parameter'])
        dialog.tap_pos.setValue(table_data.at['tap_neutral', 'Parameter'])
        dialog.tap_pos_display.setText(str(table_data.at['tap_neutral', 'Parameter']))
        
        # height = table_std.table.horizontalHeader().height()
        # for row in range(table_std.model.rowCount(None)):
        #     height += table_std.table.rowHeight(row)
        # dialog.widget_table_container.setMinimumHeight(height * 1.2)
    
    dialog.std_type.currentTextChanged.connect(update_table)
    
    return dialog


def gen_dialog():
    """
    Returns the generator dialog.
    """
    ui_file = os.path.join(directory, 'gen_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def min_vm_pu_changed(value):
        dialog.vm_pu.setMinimum(value)
        dialog.max_vm_pu.setMinimum(value)
        
    def max_vm_pu_changed(value):
        dialog.vm_pu.setMaximum(value)
        dialog.min_vm_pu.setMaximum(value)
        
    def min_p_mw_changed(value):
        dialog.p_mw.setMinimum(value)
        dialog.max_p_mw.setMinimum(value)
        
    def max_p_mw_changed(value):
        dialog.p_mw.setMaximum(value)
        dialog.min_p_mw.setMaximum(value)
    
    dialog.min_vm_pu.valueChanged.connect(min_vm_pu_changed)
    dialog.max_vm_pu.valueChanged.connect(max_vm_pu_changed)
    dialog.min_p_mw.valueChanged.connect(min_p_mw_changed)
    dialog.max_p_mw.valueChanged.connect(max_p_mw_changed)
    
    return dialog


def sgen_dialog():
    """
    Returns the static generator dialog.
    """
    ui_file = os.path.join(directory, 'sgen_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
        
    def min_p_mw_changed(value):
        dialog.p_mw.setMinimum(value)
        dialog.max_p_mw.setMinimum(value)
        
    def max_p_mw_changed(value):
        dialog.p_mw.setMaximum(value)
        dialog.min_p_mw.setMaximum(value)
        
    def min_q_mvar_changed(value):
        dialog.q_mvar.setMinimum(value)
        dialog.max_q_mvar.setMinimum(value)
        
    def max_q_mvar_changed(value):
        dialog.q_mvar.setMaximum(value)
        dialog.min_q_mvar.setMaximum(value)
    
    dialog.min_p_mw.valueChanged.connect(min_p_mw_changed)
    dialog.max_p_mw.valueChanged.connect(max_p_mw_changed)
    dialog.min_q_mvar.valueChanged.connect(min_q_mvar_changed)
    dialog.max_q_mvar.valueChanged.connect(max_q_mvar_changed)
    
    return dialog


def asgen_dialog():
    """
    Returns the asymmetric static generator dialog.
    """
    ui_file = os.path.join(directory, 'asgen_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    return dialog


def ext_grid_dialog():
    """
    Returns the external grid dialog.
    """
    ui_file = os.path.join(directory, 'ext_grid_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def min_p_mw_changed(value):
        dialog.max_p_mw.setMinimum(value)
        
    def max_p_mw_changed(value):
        dialog.min_p_mw.setMaximum(value)
        
    def min_q_mvar_changed(value):
        dialog.max_q_mvar.setMinimum(value)
        
    def max_q_mvar_changed(value):
        dialog.min_q_mvar.setMaximum(value)
        
    def s_sc_max_mva_changed(value):
        dialog.s_sc_min_mva.setMaximum(value)
        
    def s_sc_min_mva_changed(value):
        dialog.s_sc_max_mva.setMinimum(value)
    
    dialog.min_p_mw.valueChanged.connect(min_p_mw_changed)
    dialog.max_p_mw.valueChanged.connect(max_p_mw_changed)
    dialog.min_q_mvar.valueChanged.connect(min_q_mvar_changed)
    dialog.max_q_mvar.valueChanged.connect(max_q_mvar_changed)
    dialog.s_sc_max_mva.valueChanged.connect(s_sc_max_mva_changed)
    dialog.s_sc_min_mva.valueChanged.connect(s_sc_min_mva_changed)
    
    return dialog


def choose_load_dialog():
    """
    Returns the symmetric load, asymmetric load, shunt element, motor,
    ward or extended ward).
    """
    ui_file = os.path.join(directory, 'choose_load_type.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # return QtCompat.loadUi(uifile=ui_file)
    return dialog


def load_dialog():
    """
    Returns the symmetric load dialog.
    """
    ui_file = os.path.join(directory, 'load_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def min_p_mw_changed(value):
        dialog.p_mw.setMinimum(value)
        dialog.max_p_mw.setMinimum(value)
        
    def max_p_mw_changed(value):
        dialog.p_mw.setMaximum(value)
        dialog.min_p_mw.setMaximum(value)
        
    def min_q_mvar_changed(value):
        dialog.q_mvar.setMinimum(value)
        dialog.max_q_mvar.setMinimum(value)
        
    def max_q_mvar_changed(value):
        dialog.q_mvar.setMaximum(value)
        dialog.min_q_mvar.setMaximum(value)
    
    dialog.min_p_mw.valueChanged.connect(min_p_mw_changed)
    dialog.max_p_mw.valueChanged.connect(max_p_mw_changed)
    dialog.min_q_mvar.valueChanged.connect(min_q_mvar_changed)
    dialog.max_q_mvar.valueChanged.connect(max_q_mvar_changed)
    
    return dialog


def aload_dialog():
    """
    Returns the asymmetric load dialog.
    """
    ui_file = os.path.join(directory, 'aload_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    return dialog


def shunt_dialog():
    """
    Returns the shunt element dialog.
    """
    ui_file = os.path.join(directory, 'shunt_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def max_step_changed(value):
        dialog.step.setMaximum(value)
    
    dialog.max_step.valueChanged.connect(max_step_changed)
    
    return dialog


def motor_dialog():
    """
    Returns the motor dialog.
    """
    ui_file = os.path.join(directory, 'motor_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    return dialog


def ward_dialog():
    """
    Returns the ward dialog.
    """
    ui_file = os.path.join(directory, 'ward_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    return dialog


def xward_dialog():
    """
    Returns the extended ward dialog.
    """
    ui_file = os.path.join(directory, 'xward_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    return dialog


def storage_dialog():
    """
    Returns the storage dialog.
    """
    ui_file = os.path.join(directory, 'storage_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    def min_p_mw_changed(value):
        dialog.p_mw.setMinimum(value)
        dialog.max_p_mw.setMinimum(value)
        
    def max_p_mw_changed(value):
        dialog.p_mw.setMaximum(value)
        dialog.min_p_mw.setMaximum(value)
        
    def min_q_mvar_changed(value):
        dialog.q_mvar.setMinimum(value)
        dialog.max_q_mvar.setMinimum(value)
        
    def max_q_mvar_changed(value):
        dialog.q_mvar.setMaximum(value)
        dialog.min_q_mvar.setMaximum(value)
        
    def min_e_mwh_changed(value):
        dialog.max_e_mwh.setMinimum(value)
        
    def max_e_mwh_changed(value):
        dialog.min_e_mwh.setMaximum(value)
        
    dialog.min_p_mw.valueChanged.connect(min_p_mw_changed)
    dialog.max_p_mw.valueChanged.connect(max_p_mw_changed)
    dialog.min_q_mvar.valueChanged.connect(min_q_mvar_changed)
    dialog.max_q_mvar.valueChanged.connect(max_q_mvar_changed)
    dialog.min_e_mwh.valueChanged.connect(min_e_mwh_changed)
    dialog.max_e_mwh.valueChanged.connect(max_e_mwh_changed)
    
    return dialog


def switch_dialog():
    """
    Returns the switch dialog.
    """
    ui_file = os.path.join(directory, 'switch_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    return dialog


def network_settings_dialog():
    """
    Returns the network settings dialog.
    """
    ui_file = os.path.join(directory, 'network_settings_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    
    return dialog


def connecting_buses_dialog():
    """
    Returns a dialog to choose which element is connecting between two buses.
    """
    ui_file = os.path.join(directory, 'connecting_buses_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    dialog.setModal(True)
    dialog.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    dialog.option = None  # Element selected

    def line():
        dialog.option = 'line'
        dialog.accept()

    def stdline():
        dialog.option = 'stdline'
        dialog.accept()

    def dcline():
        dialog.option = 'dcline'
        dialog.accept()

    def impedance():
        dialog.option = 'impedance'
        dialog.accept()

    def trafo():
        dialog.option = 'trafo'
        dialog.accept()

    def stdtrafo():
        dialog.option = 'stdtrafo'
        dialog.accept()

    def switch():
        dialog.option = 'switch'
        dialog.accept()

    dialog.btn_close.setIcon(qta.icon('mdi6.close'))

    dialog.btnLine.setIcon(qta.icon('ph.line-segment'))
    dialog.btnLine.setText('AC line')
    dialog.btnLine.clicked.connect(line)

    dialog.btnStdLine.setIcon(qta.icon('ph.line-segment'))
    dialog.btnStdLine.setText('Standard AC line')
    dialog.btnStdLine.clicked.connect(stdline)

    dialog.btnDCLine.setIcon(qta.icon('ph.line-segment'))
    dialog.btnDCLine.setText('DC line')
    dialog.btnDCLine.clicked.connect(dcline)

    dialog.btnImpedance.setIcon(qta.icon('mdi6.alpha-z-box-outline'))
    dialog.btnImpedance.setText('Impedance')
    # dialog.btnImpedance.setStyleSheet("text-align:left;")
    # dialog.btnImpedance.setStyleSheet("border:0px; text-align:left;")
    dialog.btnImpedance.clicked.connect(impedance)

    dialog.btnTrafo.setIcon(qta.icon('ph.intersect'))
    dialog.btnTrafo.setText('2-winding transformer')
    dialog.btnTrafo.clicked.connect(trafo)

    dialog.btnStdTrafo.setIcon(qta.icon('ph.intersect'))
    dialog.btnStdTrafo.setText('Standard 2-winding transformer')
    dialog.btnStdTrafo.clicked.connect(stdtrafo)

    dialog.btnSwitch.setIcon(qta.icon('mdi6.electric-switch'))
    dialog.btnSwitch.setText('Switch')
    dialog.btnSwitch.clicked.connect(switch)

    # dialog.widget_container.setStyleSheet('border: 1px solid #d3d3d3')
    # dialog.widget_container.setStyleSheet('QWidget {border-left: 10px solid blue;}')
    # dialog.widget_container.setStyleSheet('background-color: #d3d3d3')
    dialog.setStyleSheet('font-size: 20px')
    dialog.label.setStyleSheet('font-size: 16px')

    return dialog


def search_node_dialog(all_nodes):
    """
    all_nodes: List of all nodes in the graph.

    Returns a dialog for searching nodes.
    """
    names = [node.name() for node in all_nodes]
    types = [node.type_ for node in all_nodes]

    ordered = sorted(enumerate(names), key=natsort2)
    all_names = []
    all_types = []
    for order, name in ordered:
        all_names.append(name)
        all_types.append(types[order])

    ui_file = os.path.join(directory, 'search_node_dialog.ui')
    # dialog = QtCompat.loadUi(uifile=ui_file)
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    dialog = loader.load(ui_file_)
    # dialog.setModal(True)
    dialog.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    dialog.selected_node = None  # Name of the selected element (node)

    dialog.btn_close.setIcon(qta.icon('mdi6.close'))

    dialog.setStyleSheet('font-size: 20px')
    dialog.label.setStyleSheet('font-size: 16px')
    # dialog.frame.setStyleSheet('border: 1px solid #d3d3d3')

    class SaveNodeName:
        def __init__(self, name):
            self.name = name

        def __call__(self):
            dialog.selected_node = self.name
            dialog.accept()

    def list_all_nodes():
        widget = QtWidgets.QWidget()
        dialog.vbox = QtWidgets.QVBoxLayout(widget)
        icon_size = QtCore.QSize(32, 32)

        button_group = QtWidgets.QButtonGroup(widget)
        button_group.setExclusive(True)

        for node_name, node_type in zip(all_names, all_types):
            btn_node = QtWidgets.QPushButton(widget)
            btn_node.setIcon(qta.icon(icon_for_type[node_type]))
            btn_node.setText(node_name)
            btn_node.setIconSize(icon_size)
            btn_node.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            # btn_node.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
            btn_node.setStyleSheet("border:0px; text-align:left;")
            btn_action = SaveNodeName(node_name)
            btn_node.clicked.connect(btn_action)
            btn_node.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
            btn_node.setAutoExclusive(False)
            dialog.vbox.addWidget(btn_node)
            button_group.addButton(btn_node)

        dialog.vbox.addStretch()
        widget.setLayout(dialog.vbox)
        dialog.scrollArea.setWidget(widget)

    list_all_nodes()

    # dialog.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
    dialog.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    dialog.scrollArea.setWidgetResizable(True)

    def nodes_found(text):
        dialog.scrollArea.takeWidget()  # Removing list...
        if text=='':
            list_all_nodes()
            return

        widget = QtWidgets.QWidget()
        dialog.vbox = QtWidgets.QVBoxLayout(widget)
        icon_size = QtCore.QSize(32, 32)

        button_group = QtWidgets.QButtonGroup(widget)
        button_group.setExclusive(True)

        for node_name, node_type in zip(all_names, all_types):
            search_text = node_name.join((node_name.lower(), node_name.upper()))
            found_list = find_near_matches(text, search_text, max_l_dist=1)
            if text in search_text or (found_list and not all([m.matched=='' for m in found_list])):
                btn_node = QtWidgets.QPushButton(widget)
                btn_node.setIcon(qta.icon(icon_for_type[node_type]))
                btn_node.setText(node_name)
                btn_node.setIconSize(icon_size)
                btn_node.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                # btn_node.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
                btn_node.setStyleSheet("border:0px; text-align:left;")
                btn_action = SaveNodeName(node_name)
                btn_node.clicked.connect(btn_action)
                btn_node.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
                btn_node.setAutoExclusive(False)
                dialog.vbox.addWidget(btn_node)
                button_group.addButton(btn_node)

        dialog.vbox.addStretch()
        widget.setLayout(dialog.vbox)
        dialog.scrollArea.setWidget(widget)


    dialog.input_search.textChanged.connect(nodes_found)

    return dialog


class Toolbar_Matplotlib_custom(NavigationToolbar):
    """
    Custom Matplotlib toolbar.
    """
    def __init__(self, plotCanvas, frame, theme):
        NavigationToolbar.__init__(self, plotCanvas, frame)
        
        # Removing unused buttons
        self.removeAction(self.actions()[-4])
        self.removeAction(self.actions()[-4])
        
        # Custom icons
        btn_save = self.actions()[-2]
        btn_save.setIcon(qta.icon('ph.floppy-disk'))
        
        btn_zoom = self.actions()[-4]
        btn_zoom.setIcon(qta.icon('ph.magnifying-glass-plus'))
        
        btn_move = self.actions()[-5]
        btn_move.setIcon(qta.icon('ph.arrows-out-cardinal'))
        
        btn_arrow_right = self.actions()[-7]
        btn_arrow_right.setIcon(qta.icon('ph.arrow-right'))
        
        btn_arrow_left = self.actions()[-8]
        btn_arrow_left.setIcon(qta.icon('ph.arrow-left'))
        
        btn_reset_zoom = self.actions()[-9]
        btn_reset_zoom.setIcon(qta.icon('ph.house'))
        
        # Setting the backgroud color and theme:
        if theme in ('light', 'auto'):
            style_toolbar = qdarktheme.load_stylesheet('light')
            style_toolbar = style_toolbar.replace(
                'background:rgba(235, 235, 235, 1.000)',
                'background:rgba(248, 249, 250, 1.000)'
                                                )
        elif theme=='dark':
            style_toolbar = qdarktheme.load_stylesheet('dark')
            style_toolbar = style_toolbar.replace(
                'background:rgba(51, 51, 51, 1.000)',
                'background:rgba(32, 33, 36, 1.000)'
                                                )
        self.setStyleSheet(style_toolbar)


class Power_Flow_Dialog(QtWidgets.QDialog):
    """
    Balanced AC Power Flow dialog.
    
    * net: Pandapower network
    * settings: Default settings for ACPF calculation
    * session_change_warning: session_change_warning() funtion from the graph
    * theme: color theme setting between 'light', 'dark' and 'auto'
    """
    def __init__(self, net, settings, session_change_warning, theme):
        self.net = net
        self.settings = settings
        self.session_change_warning = session_change_warning
        self.theme = theme
        
        super(Power_Flow_Dialog, self).__init__()
        ui_file = os.path.join(directory, 'power_flow_dialog.ui')
        # self.w = QtCompat.loadUi(uifile=ui_file)
        ui_file_ = QtCore.QFile(ui_file)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        self.w = loader.load(ui_file_)
        
        self.methods = ['nr', 'iwamoto_nr', 'bfsw', 'gs',
                        'fdbx', 'fdxb']  # solvers
        self.init_methods = ['auto', 'flat', 'dc', 'results']  # methods for initialization
        self.trafo3w_models = ['t', 'pi']
        self.trafo3w_loadings = ['current', 'power']
        self.trafo3w_losses_options = ['hv', 'mv', 'lv', 'star']
        self.load_settings()  # Load default settings on the first page
        
        self.w.btn_run.setIcon(qta.icon('mdi6.play-outline'))
        self.w.btn_run.setIconSize(QtCore.QSize(24, 24))
        
        root_dir, _ = os.path.split(directory)
        app_icon_dir = os.path.join(root_dir, 'icons', 'app_icon.png')
        self.setWindowIcon(QtGui.QIcon(app_icon_dir))
        self.w.setWindowIcon(QtGui.QIcon(app_icon_dir))
        
        self.w.stackedWidget.setCurrentIndex(0)
        
        # Upper toolbar:
        icon_size = QtCore.QSize(36, 36)
        self.w.layout_upper_toolbar.addStretch()
        
        self.settings_and_run = QtWidgets.QToolButton(self.w)
        self.settings_and_run.setToolTip('Settings & Execution')
        self.settings_and_run.setIconSize(icon_size)
        self.settings_and_run.setIcon(qta.icon('mdi6.play-outline'))
        self.settings_and_run.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.settings_and_run.setText('Settings && Execution')
        self.settings_and_run.setCheckable(True)
        self.settings_and_run.setAutoExclusive(True)
        self.settings_and_run.setChecked(True)
        self.w.layout_upper_toolbar.addWidget(self.settings_and_run)
        self.settings_and_run.clicked.connect(lambda : self.change_page(0))
        
        # self.logging = QtWidgets.QToolButton(self.w)
        # self.logging.setToolTip('Output Log')
        # self.logging.setIconSize(icon_size)
        # self.logging.setIcon(qta.icon('mdi6.text-box-outline'))
        # self.logging.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        # self.logging.setText('Output Log')
        # self.logging.setCheckable(True)
        # self.logging.setAutoExclusive(True)
        # self.w.layout_upper_toolbar.addWidget(self.logging)
        # self.logging.clicked.connect(lambda : self.change_page(1))
        
        self.data_results = QtWidgets.QToolButton(self.w)
        self.data_results.setToolTip('Results Data')
        self.data_results.setIconSize(icon_size)
        self.data_results.setIcon(qta.icon('ph.table'))
        self.data_results.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.data_results.setText('Results Data')
        self.data_results.setCheckable(True)
        self.data_results.setAutoExclusive(True)
        self.w.layout_upper_toolbar.addWidget(self.data_results)
        self.data_results.clicked.connect(lambda : self.change_page(1))
        
        self.plot_results = QtWidgets.QToolButton(self.w)
        self.plot_results.setToolTip('Plot Results')
        self.plot_results.setIconSize(icon_size)
        self.plot_results.setIcon(qta.icon('mdi6.chart-bar'))
        self.plot_results.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.plot_results.setText('Plot Results')
        self.plot_results.setCheckable(True)
        self.plot_results.setAutoExclusive(True)
        self.w.layout_upper_toolbar.addWidget(self.plot_results)
        self.plot_results.clicked.connect(lambda : self.change_page(2))
        
        self.w.layout_upper_toolbar.addStretch()
        
        self.load_dataframes()
        self.build_plots_page()
        self.plot()
        
        # List of plots in third page:
        list_of_plots = ['Voltage magnitudes', 'Voltages (only PQ load buses)',
                         'Voltage box plot', 'AC line loading',
                         'AC line voltages', 'Two winding transformers loading',
                         'Three winding transformers loading',
                         'Reactive power on PV generators']
        model_plot_list = QtGui.QStandardItemModel()
        self.w.listView.setModel(model_plot_list)
        for name in list_of_plots:
            item = QtGui.QStandardItem(name)  # row
            item.setSizeHint(QtCore.QSize(36, 36))  # row height
            model_plot_list.appendRow(item)
        first_item_index = model_plot_list.index(0, 0)
        self.w.listView.setCurrentIndex(first_item_index)
        self.w.stacked_plots.setCurrentIndex(0)
        
        # Connecting some signals:
        self.w.btn_run.clicked.connect(self.run_pf)
        self.w.listView.clicked.connect(lambda index :
                self.w.stacked_plots.setCurrentIndex(index.row()))
        
    def load_settings(self):
        """
        Load default settings on the first page.
        """
        booleans = {'True': True, 'False': False}
        
        for name, value in self.settings.items():
            if name=='algorithm':
                index = self.methods.index(value)
                self.w.algorithm.setCurrentIndex(index)
            elif name=='max_iteration':
                self.w.max_iteration.setValue(int(value))
            elif name=='tolerance_mva':
                self.w.tolerance_mva.setValue(float(value))
            elif name=='delta_q':
                self.w.delta_q.setValue(float(value))
            elif name=='check_connectivity':
                self.w.check_connectivity.setChecked(booleans[value])
            elif name=='init':
                index = self.init_methods.index(value)
                self.w.init.setCurrentIndex(index)
            elif name=='trafo_model':
                index = self.trafo3w_models.index(value)
                self.w.trafo_model.setCurrentIndex(index)
            elif name=='trafo3w_loading':
                index = self.trafo3w_loadings.index(value)
                self.w.trafo3w_loading.setCurrentIndex(index)
            elif name=='trafo3w_losses':
                index = self.trafo3w_losses_options.index(value)
                self.w.trafo3w_losses.setCurrentIndex(index)
            elif name=='switch_rx_ratio':
                self.w.switch_rx_ratio.setValue(float(value))
            elif name=='neglect_open_switch_branches':
                self.w.neglect_open_switch_branches.setChecked(booleans[value])
            elif name=='enforce_q_lims':
                self.w.enforce_q_lims.setChecked(booleans[value])
            elif name=='voltage_depend_loads':
                self.w.voltage_depend_loads.setChecked(booleans[value])
            elif name=='consider_line_temperature':
                self.w.consider_line_temperature.setChecked(booleans[value])
            elif name=='distributed_slack':
                self.w.distributed_slack.setChecked(booleans[value])
            elif name=='tdpf':
                self.w.tdpf.setChecked(booleans[value])
            elif name=='tdpf_delay_s' and value=='None':
                self.w.tdpf_delay_s_check.setChecked(False)
            elif name=='tdpf_delay_s' and value!='None':
                self.w.tdpf_delay_s_check.setChecked(True)
                self.w.tdpf_delay_s.setValue(float(value))
            elif name=='tdpf_update_r_theta':
                self.w.tdpf_update_r_theta.setChecked(booleans[value])
        
    def change_page(self, index):
        """
        Change to the page indicated by the index. First page is the number 0.
        """
        if index==1:
            self.update_dataframes()
        
        self.w.stackedWidget.setCurrentIndex(index)
        
    def load_dataframes(self):
        """
        Load results DataFrames to the GUI.
        """
        # Adding Bus DataFrame from pandapower network:
        df_bus_widget = TableWidget(self.net.res_bus)
        self.w.layout_bus.addWidget(df_bus_widget)
        
        # Adding Line DataFrame from pandapower network:
        df_line_widget = TableWidget(self.net.res_line)
        self.w.layout_line.addWidget(df_line_widget)
        
        # Adding DC Line DataFrame from pandapower network:
        df_dcline_widget = TableWidget(self.net.res_dcline)
        self.w.layout_dcline.addWidget(df_dcline_widget)
        
        # Adding Impedance DataFrame from pandapower network:
        df_impedance_widget = TableWidget(self.net.res_impedance)
        self.w.layout_impedance.addWidget(df_impedance_widget)
        
        # Adding Two Winding Transformer DataFrame from pandapower network:
        df_trafo_widget = TableWidget(self.net.res_trafo)
        self.w.layout_trafo.addWidget(df_trafo_widget)
        
        # Adding Three Winding Transformer DataFrame from pandapower network:
        df_trafo3w_widget = TableWidget(self.net.res_trafo3w)
        self.w.layout_trafo3w.addWidget(df_trafo3w_widget)
        
        # Adding Generator DataFrame from pandapower network:
        df_gen_widget = TableWidget(self.net.res_gen)
        self.w.layout_gen.addWidget(df_gen_widget)
        
        # Adding Static Generator DataFrame from pandapower network:
        df_sgen_widget = TableWidget(self.net.res_sgen)
        self.w.layout_sgen.addWidget(df_sgen_widget)
        
        # Adding Asymmetric Static Generator DataFrame from pandapower network:
        df_asgen_widget = TableWidget(self.net.res_asymmetric_sgen)
        self.w.layout_asgen.addWidget(df_asgen_widget)
        
        # Adding External Grid DataFrame from pandapower network:
        df_ext_grid_widget = TableWidget(self.net.res_ext_grid)
        self.w.layout_ext_grid.addWidget(df_ext_grid_widget)
        
        # Adding Symmetric Load DataFrame from pandapower network:
        df_load_widget = TableWidget(self.net.res_load)
        self.w.layout_load.addWidget(df_load_widget)
        
        # Adding Asymmetric Load DataFrame from pandapower network:
        df_aload_widget = TableWidget(self.net.res_asymmetric_load)
        self.w.layout_aload.addWidget(df_aload_widget)
        
        # Adding Shunt DataFrame from pandapower network:
        df_shunt_widget = TableWidget(self.net.res_shunt)
        self.w.layout_shunt.addWidget(df_shunt_widget)
        
        # Adding Motor DataFrame from pandapower network:
        df_motor_widget = TableWidget(self.net.res_motor)
        self.w.layout_motor.addWidget(df_motor_widget)
        
        # Adding Ward DataFrame from pandapower network:
        df_ward_widget = TableWidget(self.net.res_ward)
        self.w.layout_ward.addWidget(df_ward_widget)
        
        # Adding Extended Ward DataFrame from pandapower network:
        df_xward_widget = TableWidget(self.net.res_xward)
        self.w.layout_xward.addWidget(df_xward_widget)
        
        # Adding Storage DataFrame from pandapower network:
        df_storage_widget = TableWidget(self.net.res_storage)
        self.w.layout_storage.addWidget(df_storage_widget)
        
        # Adding Switch DataFrame from pandapower network:
        df_switch_widget = TableWidget(self.net.res_switch)
        self.w.layout_switch.addWidget(df_switch_widget)
        
    def update_dataframes(self):
        """
        Update results DataFrames to the GUI.
        """
        # Adding Bus DataFrame from pandapower network:
        old_bus_table = self.w.layout_bus.itemAt(0).widget()
        old_bus_table.setParent(None)
        df_bus_widget = TableWidget(self.net.res_bus)
        self.w.layout_bus.addWidget(df_bus_widget)
        
        # Adding Line DataFrame from pandapower network:
        old_line_table = self.w.layout_line.itemAt(0).widget()
        old_line_table.setParent(None)
        df_line_widget = TableWidget(self.net.res_line)
        self.w.layout_line.addWidget(df_line_widget)
        
        # Adding DC Line DataFrame from pandapower network:
        old_dcline_table = self.w.layout_dcline.itemAt(0).widget()
        old_dcline_table.setParent(None)
        df_dcline_widget = TableWidget(self.net.res_dcline)
        self.w.layout_dcline.addWidget(df_dcline_widget)
        
        # Adding Impedance DataFrame from pandapower network:
        old_impedance_table = self.w.layout_impedance.itemAt(0).widget()
        old_impedance_table.setParent(None)
        df_impedance_widget = TableWidget(self.net.res_impedance)
        self.w.layout_impedance.addWidget(df_impedance_widget)
        
        # Adding Two Winding Transformer DataFrame from pandapower network:
        old_trafo_table = self.w.layout_trafo.itemAt(0).widget()
        old_trafo_table.setParent(None)
        df_trafo_widget = TableWidget(self.net.res_trafo)
        self.w.layout_trafo.addWidget(df_trafo_widget)
        
        # Adding Three Winding Transformer DataFrame from pandapower network:
        old_trafo3w_table = self.w.layout_trafo3w.itemAt(0).widget()
        old_trafo3w_table.setParent(None)
        df_trafo3w_widget = TableWidget(self.net.res_trafo3w)
        self.w.layout_trafo3w.addWidget(df_trafo3w_widget)
        
        # Adding Generator DataFrame from pandapower network:
        old_gen_table = self.w.layout_gen.itemAt(0).widget()
        old_gen_table.setParent(None)
        df_gen_widget = TableWidget(self.net.res_gen)
        self.w.layout_gen.addWidget(df_gen_widget)
        
        # Adding Static Generator DataFrame from pandapower network:
        old_sgen_table = self.w.layout_sgen.itemAt(0).widget()
        old_sgen_table.setParent(None)
        df_sgen_widget = TableWidget(self.net.res_sgen)
        self.w.layout_sgen.addWidget(df_sgen_widget)
        
        # Adding Asymmetric Static Generator DataFrame from pandapower network:
        old_asgen_table = self.w.layout_asgen.itemAt(0).widget()
        old_asgen_table.setParent(None)
        df_asgen_widget = TableWidget(self.net.res_asymmetric_sgen)
        self.w.layout_asgen.addWidget(df_asgen_widget)
        
        # Adding External Grid DataFrame from pandapower network:
        old_ext_grid_table = self.w.layout_ext_grid.itemAt(0).widget()
        old_ext_grid_table.setParent(None)
        df_ext_grid_widget = TableWidget(self.net.res_ext_grid)
        self.w.layout_ext_grid.addWidget(df_ext_grid_widget)
        
        # Adding Symmetric Load DataFrame from pandapower network:
        old_load_table = self.w.layout_load.itemAt(0).widget()
        old_load_table.setParent(None)
        df_load_widget = TableWidget(self.net.res_load)
        self.w.layout_load.addWidget(df_load_widget)
        
        # Adding Asymmetric Load DataFrame from pandapower network:
        old_aload_table = self.w.layout_aload.itemAt(0).widget()
        old_aload_table.setParent(None)
        df_aload_widget = TableWidget(self.net.res_asymmetric_load)
        self.w.layout_aload.addWidget(df_aload_widget)
        
        # Adding Shunt DataFrame from pandapower network:
        old_shunt_table = self.w.layout_shunt.itemAt(0).widget()
        old_shunt_table.setParent(None)
        df_shunt_widget = TableWidget(self.net.res_shunt)
        self.w.layout_shunt.addWidget(df_shunt_widget)
        
        # Adding Motor DataFrame from pandapower network:
        old_motor_table = self.w.layout_motor.itemAt(0).widget()
        old_motor_table.setParent(None)
        df_motor_widget = TableWidget(self.net.res_motor)
        self.w.layout_motor.addWidget(df_motor_widget)
        
        # Adding Ward DataFrame from pandapower network:
        old_ward_table = self.w.layout_ward.itemAt(0).widget()
        old_ward_table.setParent(None)
        df_ward_widget = TableWidget(self.net.res_ward)
        self.w.layout_ward.addWidget(df_ward_widget)
        
        # Adding Extended Ward DataFrame from pandapower network:
        old_xward_table = self.w.layout_xward.itemAt(0).widget()
        old_xward_table.setParent(None)
        df_xward_widget = TableWidget(self.net.res_xward)
        self.w.layout_xward.addWidget(df_xward_widget)
        
        # Adding Storage DataFrame from pandapower network:
        old_storage_table = self.w.layout_storage.itemAt(0).widget()
        old_storage_table.setParent(None)
        df_storage_widget = TableWidget(self.net.res_storage)
        self.w.layout_storage.addWidget(df_storage_widget)
        
        # Adding Switch DataFrame from pandapower network:
        old_switch_table = self.w.layout_switch.itemAt(0).widget()
        old_switch_table.setParent(None)
        df_switch_widget = TableWidget(self.net.res_switch)
        self.w.layout_switch.addWidget(df_switch_widget)

    def build_plots_page(self):
        """
        Build the plot page.
        """
        if self.theme in ('light', 'auto'):
            facecolor_figure = [0.97254902, 0.97647059, 0.98039216]
        else:
            facecolor_figure = [0.1254902 , 0.12941176, 0.14117647]
            
        self.list_of_figures = []
        
        # Voltage magnitudes plot:
        self.layout_vm = QtWidgets.QVBoxLayout()
        self.w.vm.setLayout(self.layout_vm)
        self.figure_vm = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_vm = self.figure_vm.add_subplot(111)
        canvas_vm = FigureCanvas(self.figure_vm)
        self.layout_vm.addWidget(canvas_vm)
        self.ax_vm.set_xlabel('Bus')
        self.ax_vm.set_ylabel('Voltage mangnitude (p.u.)')
        self.mpl_toolbar_vm = Toolbar_Matplotlib_custom(canvas_vm,
                                                        self.w.vm,
                                                        self.theme)
        self.layout_vm.addWidget(self.mpl_toolbar_vm)
        self.list_of_figures.append(self.figure_vm)
        
        # Voltages plot (only PQ buses):
        self.layout_vm_load = QtWidgets.QVBoxLayout()
        self.w.vm_load.setLayout(self.layout_vm_load)
        self.figure_vm_load = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_vm_load = self.figure_vm_load.add_subplot(111)
        canvas_vm_load = FigureCanvas(self.figure_vm_load)
        self.layout_vm_load.addWidget(canvas_vm_load)
        self.ax_vm_load.set_xlabel('Bus')
        self.ax_vm_load.set_ylabel('Voltage mangnitude (p.u.)')
        self.mpl_toolbar_vm_load = Toolbar_Matplotlib_custom(canvas_vm_load,
                                                        self.w.vm_load,
                                                        self.theme)
        self.layout_vm_load.addWidget(self.mpl_toolbar_vm_load)
        self.list_of_figures.append(self.figure_vm_load)
        
        # Voltage box plot:
        self.layout_vm_box = QtWidgets.QVBoxLayout()
        self.w.vm_box.setLayout(self.layout_vm_box)
        self.figure_vm_box = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_vm_box = self.figure_vm_box.add_subplot(111)
        canvas_vm_box = FigureCanvas(self.figure_vm_box)
        self.layout_vm_box.addWidget(canvas_vm_box)
        self.ax_vm_box.set_xlabel('Voltage mangnitude (p.u.)')
        self.mpl_toolbar_vm_box = Toolbar_Matplotlib_custom(canvas_vm_box,
                                                        self.w.vm_box,
                                                        self.theme)
        self.layout_vm_box.addWidget(self.mpl_toolbar_vm_box)
        self.list_of_figures.append(self.figure_vm_box)
        
        # AC line loading plot:
        self.layout_line_loading = QtWidgets.QVBoxLayout()
        self.w.line_loading.setLayout(self.layout_line_loading)
        self.figure_line_loading = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_line_loading = self.figure_line_loading.add_subplot(111)
        canvas_line_loading = FigureCanvas(self.figure_line_loading)
        self.layout_line_loading.addWidget(canvas_line_loading)
        self.ax_line_loading.set_xlabel('AC Line')
        self.ax_line_loading.set_ylabel('Loading (%)')
        self.mpl_toolbar_line_loading = Toolbar_Matplotlib_custom(canvas_line_loading,
                                                        self.w.line_loading,
                                                        self.theme)
        self.layout_line_loading.addWidget(self.mpl_toolbar_line_loading)
        self.list_of_figures.append(self.figure_line_loading)
        
        # AC line voltages plot:
        self.layout_line_vm = QtWidgets.QVBoxLayout()
        self.w.line_vm.setLayout(self.layout_line_vm)
        self.figure_line_vm = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_line_vm = self.figure_line_vm.add_subplot(111)
        canvas_line_vm = FigureCanvas(self.figure_line_vm)
        self.layout_line_vm.addWidget(canvas_line_vm)
        self.ax_line_vm.set_xlabel('AC Line')
        self.ax_line_vm.set_ylabel('Voltage magnitudes (p.u.)')
        self.mpl_toolbar_line_vm = Toolbar_Matplotlib_custom(canvas_line_vm,
                                                             self.w.line_vm,
                                                             self.theme)
        self.layout_line_vm.addWidget(self.mpl_toolbar_line_vm)
        self.list_of_figures.append(self.figure_line_vm)
        
        # Two winding transformer loading plot:
        self.layout_trafo_loading = QtWidgets.QVBoxLayout()
        self.w.trafo_load.setLayout(self.layout_trafo_loading)
        self.figure_trafo_loading = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_trafo_loading = self.figure_trafo_loading.add_subplot(111)
        canvas_trafo_loading = FigureCanvas(self.figure_trafo_loading)
        self.layout_trafo_loading.addWidget(canvas_trafo_loading)
        self.ax_trafo_loading.set_xlabel('Two winding transformer')
        self.ax_trafo_loading.set_ylabel('Loading (%)')
        self.mpl_toolbar_trafo_loading = Toolbar_Matplotlib_custom(canvas_trafo_loading,
                                                        self.w.trafo_load,
                                                        self.theme)
        self.layout_trafo_loading.addWidget(self.mpl_toolbar_trafo_loading)
        self.list_of_figures.append(self.figure_trafo_loading)
        
        # Three winding transformer loading plot:
        self.layout_trafo3w_loading = QtWidgets.QVBoxLayout()
        self.w.trafo3w_loading.setLayout(self.layout_trafo3w_loading)
        self.figure_trafo3w_loading = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_trafo3w_loading = self.figure_trafo3w_loading.add_subplot(111)
        canvas_trafo3w_loading = FigureCanvas(self.figure_trafo3w_loading)
        self.layout_trafo3w_loading.addWidget(canvas_trafo3w_loading)
        self.ax_trafo3w_loading.set_xlabel('Three winding transformer')
        self.ax_trafo3w_loading.set_ylabel('Loading (%)')
        self.mpl_toolbar_trafo3w_loading = Toolbar_Matplotlib_custom(canvas_trafo3w_loading,
                                                        self.w.trafo3w_loading,
                                                        self.theme)
        self.layout_trafo3w_loading.addWidget(self.mpl_toolbar_trafo3w_loading)
        self.list_of_figures.append(self.figure_trafo3w_loading)
        
        # Reactive power on PV generators plot:
        self.layout_gen_q_mvar = QtWidgets.QVBoxLayout()
        self.w.gen_q_mvar.setLayout(self.layout_gen_q_mvar)
        self.figure_gen_q_mvar = Figure(dpi=72, tight_layout=True, facecolor=facecolor_figure)
        self.ax_gen_q_mvar = self.figure_gen_q_mvar.add_subplot(111)
        canvas_gen_q_mvar = FigureCanvas(self.figure_gen_q_mvar)
        self.layout_gen_q_mvar.addWidget(canvas_gen_q_mvar)
        self.ax_gen_q_mvar.set_xlabel('Generator (PV mode)')
        self.ax_gen_q_mvar.set_ylabel('Reactive generated power (Mvar)')
        self.mpl_toolbar_gen_q_mvar = Toolbar_Matplotlib_custom(canvas_gen_q_mvar,
                                                        self.w.gen_q_mvar,
                                                        self.theme)
        self.layout_gen_q_mvar.addWidget(self.mpl_toolbar_gen_q_mvar)
        self.list_of_figures.append(self.figure_gen_q_mvar)
        
        # Setting the axes color:
        self.list_of_axes = [self.ax_vm, self.ax_vm_load, self.ax_vm_box,
                             self.ax_line_loading, self.ax_line_vm,
                             self.ax_trafo_loading, self.ax_trafo3w_loading,
                             self.ax_gen_q_mvar]
        for ax in self.list_of_axes:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))  # xticks int
            if self.theme in ('light', 'auto'):
                ax.xaxis.label.set_color('black')
                ax.yaxis.label.set_color('black')
                ax.tick_params(axis='x', colors='black')
                ax.tick_params(axis='y', colors='black')
            elif self.theme=='dark':
                ax.xaxis.label.set_color('white')
                ax.yaxis.label.set_color('white')
                ax.tick_params(axis='x', colors='white')
                ax.tick_params(axis='y', colors='white')
        
    def run_pf(self):
        """
        Run the ACPF calculation.
        """
        if self.net.ext_grid.empty:
            title = 'No slack bus!'
            content = 'There is no slack bus.'
            QtWidgets.QMessageBox.critical(self.w, title, content)
            return
        
        self.w.btn_run.setEnabled(False)
        self.w.btn_run.setText('Running...')
        self.w.btn_run.setStyleSheet('background-color: red')
        
        def pf_calculation():
            if self.w.tdpf_delay_s_check.isChecked():
                tdpf_delay_s = self.w.tdpf_delay_s.value()
            else:
                tdpf_delay_s = None
            
            try:
                pp.runpp(self.net,
                    algorithm=self.methods[self.w.algorithm.currentIndex()],
                    max_iteration=self.w.max_iteration.value(),
                    tolerance_mva=self.w.tolerance_mva.value() * 1e-6,
                    delta_q=self.w.delta_q.value(),
                    check_connectivity=self.w.check_connectivity.isChecked(),
                    init=self.w.init.currentText(),
                    trafo_model=self.w.trafo_model.currentText(),
                    trafo_loading=self.w.trafo_loading.currentText(),
                    trafo3w_losses=self.w.trafo3w_losses.currentText(),
                    switch_rx_ratio=self.w.switch_rx_ratio.value(),
                    neglect_open_switch_branches=self.w.neglect_open_switch_branches.isChecked(),
                    enforce_q_lims=self.w.enforce_q_lims.isChecked(),
                    voltage_depend_loads=self.w.voltage_depend_loads.isChecked(),
                    consider_line_temperature=self.w.consider_line_temperature.isChecked(),
                    distributed_slack=self.w.distributed_slack.isChecked(),
                    tdpf=self.w.tdpf.isChecked(),
                    tdpf_delay_s=tdpf_delay_s,
                    tdpf_update_r_theta=self.w.tdpf_update_r_theta.isChecked())

                # if self.net._ppc['success']:
                if self.net.converged:
                    title = 'Success!'
                    et = self.net._ppc['et']
                    try:
                        iterations = self.net._ppc['iterations']
                        content = f'Solver converged in {et: .2f} (s) after {iterations} iterations.'
                    except KeyError:
                        content = f'Solver converged in {et: .2f} (s).'
                    QtWidgets.QMessageBox.information(self.w, title, content)
                else:
                    title = 'Failed!'
                    content = 'Solver did not converge.'
                    QtWidgets.QMessageBox.critical(self.w, title, content)
                
            except ValueError:
                title = 'Failed!'
                content = 'Solver failed.'
                QtWidgets.QMessageBox.critical(self.w, title, content)
                
            except pp.LoadflowNotConverged:
                title = 'Failed!'
                content = 'Solver failed.'
                QtWidgets.QMessageBox.critical(self.w, title, content)
            
            except UserWarning as uw:
                title = 'Failed!'
                content = 'Solver failed.\n' + str(uw) + '.'
                QtWidgets.QMessageBox.critical(self.w, title, content)
            
        
        def callback_pf_finished(*args):
            self.w.btn_run.setText('Run power flow')
            self.w.btn_run.setStyleSheet('')
            self.w.btn_run.setEnabled(True)
                
            self.session_change_warning(tooltip_default=False)
            self.plot()
        
        future = Future()
        future.add_done_callback(callback_pf_finished)
        future.set_result(pf_calculation())       
        
    def clear_plots(self):
        """
        Clear all the plots.
        """
        for ax in self.list_of_axes:
            ax.clear()
            
        for figure in self.list_of_figures:
            figure.canvas.draw()
            figure.canvas.flush_events()

    def plot(self):
        """
        Make the plots.
        """
        if not self.net.converged:
            self.clear_plots()
            return
        
        try:
            if not self.net.res_bus.empty:
                self.ax_vm.clear()
                min_vm = self.net.res_bus['vm_pu'].min()
                max_vm = self.net.res_bus['vm_pu'].max()
                mean_vm = self.net.res_bus['vm_pu'].mean()
                std_vm = self.net.res_bus['vm_pu'].std()
                title_vm = f'Min: {min_vm: .5f}    ;    Max: {max_vm: .5f}    ;    Mean: {mean_vm: .5f}    ;    Dstd: {std_vm: .5f}'
                colors = []
                for mi, ma, v in zip(self.net.bus['min_vm_pu'], self.net.bus['max_vm_pu'], self.net.res_bus['vm_pu']):
                    if v<mi:
                        colors.append('khaki')
                    elif v>ma:
                        colors.append('tomato')
                    else:
                        colors.append('mediumslateblue')
                self.net.res_bus.plot(y='vm_pu', kind='bar', ax=self.ax_vm,
                                    color=colors,
                                    xlabel='Bus',
                                    ylabel='Voltage mangnitude (p.u.)',
                                    title=title_vm)
                
                self.ax_vm_load.clear()
                series_vm_load = self.net.res_bus.loc[self.net.load['bus'], 'vm_pu']
                series_vm_load.sort_index(inplace=True)
                min_vm_load = series_vm_load.min()
                max_vm_load = series_vm_load.max()
                mean_vm_load = series_vm_load.mean()
                std_vm_load = series_vm_load.std()
                title_vm_load = f'Min: {min_vm_load: .5f}    ;    Max: {max_vm_load: .5f}    ;    Mean: {mean_vm_load: .5f}    ;    Dstd: {std_vm_load: .5f}'
                colors = []
                for index, v in series_vm_load.items():
                    mi = self.net.bus.at[index, 'min_vm_pu']
                    ma = self.net.bus.at[index, 'max_vm_pu']
                    if v<mi:
                        colors.append('khaki')
                    elif v>ma:
                        colors.append('tomato')
                    else:
                        colors.append('mediumslateblue')
                if colors:
                    series_vm_load.plot(kind='bar', ax=self.ax_vm_load,
                                        color=colors,
                                        xlabel='Bus',
                                        ylabel='Voltage mangnitude (p.u.)',
                                        title=title_vm_load)
                
                self.ax_vm_box.clear()
                q1 = self.net.res_bus['vm_pu'].quantile(0.25)
                q2 = self.net.res_bus['vm_pu'].quantile(0.5)
                q3 = self.net.res_bus['vm_pu'].quantile(0.75)
                title_vm_box = f'Q1: {q1: .5f}    ;    Q2: {q2: .5f}    ;    Q3: {q3: .5f}'
                self.net.res_bus.plot(y='vm_pu', kind='box',
                                    ax=self.ax_vm_box,
                                    xlabel='Voltage mangnitude (p.u.)',
                                    title=title_vm_box,
                                    vert=False,
                                    boxprops=dict(linewidth=2,
                                                    color='mediumslateblue'),
                                    whiskerprops=dict(linewidth=2, color='b'),
                                    medianprops=dict(linewidth=2, color='g'))

                if self.theme=='dark':
                    self.ax_vm.xaxis.label.set_color('white')
                    self.ax_vm_load.xaxis.label.set_color('white')
                    self.ax_vm_box.xaxis.label.set_color('white')

                    self.ax_vm.yaxis.label.set_color('white')
                    self.ax_vm_load.yaxis.label.set_color('white')
                    self.ax_vm_box.yaxis.label.set_color('white')

                    self.ax_vm.title.set_color('white')
                    self.ax_vm_load.title.set_color('white')
                    self.ax_vm_box.title.set_color('white')

            if not self.net.res_line.empty:
                self.ax_line_loading.clear()
                min_line_loading = self.net.res_line['loading_percent'].min()
                max_line_loading = self.net.res_line['loading_percent'].max()
                mean_line_loading = self.net.res_line['loading_percent'].mean()
                std_line_loading = self.net.res_line['loading_percent'].std()
                title_line_loading = f'Min: {min_line_loading: .1f}    ;    Max: {max_line_loading: .1f}    ;    Mean: {mean_line_loading: .1f}    ;    Dstd: {std_line_loading: .1f}'
                colors = []
                for rate in self.net.res_line['loading_percent']:
                    if rate<=100:
                        colors.append('mediumaquamarine')
                    else:
                        colors.append('tomato')
                self.net.res_line.plot(y='loading_percent', kind='bar',
                                    ax=self.ax_line_loading,
                                    xlabel='AC line',
                                    ylabel='Loading (%)',
                                    title=title_line_loading,
                                    color=colors)
                
                self.ax_line_vm.clear()
                diff_vm_line = self.net.res_line['vm_from_pu'] - self.net.res_line['vm_to_pu']
                min_diff_vm_line = diff_vm_line.abs().min()
                max_diff_vm_line = diff_vm_line.abs().max()
                mean_diff_vm_line = diff_vm_line.abs().mean()
                title_line_vm = f'DIFFERENCE:   Min: {min_diff_vm_line: .5f}    ;    Max: {max_diff_vm_line: .5f}    ;    Mean: {mean_diff_vm_line: .5f}'
                self.ax_line_vm.bar(x=self.net.res_line.index,
                                    height=self.net.res_line['vm_from_pu'] - self.net.res_line['vm_to_pu'],
                                    bottom=self.net.res_line['vm_to_pu'],
                                    color='mediumslateblue')
                self.ax_line_vm.set_xlabel('AC line')
                self.ax_line_vm.set_ylabel('Voltage magnitude (p.u.)')
                self.ax_line_vm.set_title(title_line_vm)
                self.ax_line_vm.xaxis.set_major_locator(MaxNLocator(integer=True))  # xticks int
                self.ax_line_vm.tick_params(axis='x', labelrotation=90)

                if self.theme=='dark':
                    self.ax_line_loading.xaxis.label.set_color('white')
                    self.ax_line_vm.xaxis.label.set_color('white')

                    self.ax_line_loading.yaxis.label.set_color('white')
                    self.ax_line_vm.yaxis.label.set_color('white')

                    self.ax_line_loading.title.set_color('white')
                    self.ax_line_vm.title.set_color('white')
                
            if not self.net.res_trafo.empty:
                self.ax_trafo_loading.clear()
                min_trafo_loading = self.net.res_trafo['loading_percent'].min()
                max_trafo_loading = self.net.res_trafo['loading_percent'].max()
                mean_trafo_loading = self.net.res_trafo['loading_percent'].mean()
                std_trafo_loading = self.net.res_trafo['loading_percent'].std()
                title_trafo_loading = f'Min: {min_trafo_loading: .1f}    ;    Max: {max_trafo_loading: .1f}    ;    Mean: {mean_trafo_loading: .1f}    ;    Dstd: {std_trafo_loading: .1f}'
                colors = []
                for rate in self.net.res_trafo['loading_percent']:
                    if rate<=100:
                        colors.append('mediumaquamarine')
                    else:
                        colors.append('tomato')
                self.net.res_trafo.plot(y='loading_percent', kind='bar',
                                    ax=self.ax_trafo_loading,
                                    xlabel='Two winding transformer',
                                    ylabel='Loading (%)',
                                    title=title_trafo_loading,
                                    color=colors)
                
                if self.theme=='dark':
                    self.ax_trafo_loading.xaxis.label.set_color('white')
                    self.ax_trafo_loading.yaxis.label.set_color('white')
                    self.ax_trafo_loading.title.set_color('white')

            if not self.net.res_trafo3w.empty:
                self.ax_trafo3w_loading.clear()
                min_trafo3w_loading = self.net.res_trafo3w['loading_percent'].min()
                max_trafo3w_loading = self.net.res_trafo3w['loading_percent'].max()
                mean_trafo3w_loading = self.net.res_trafo3w['loading_percent'].mean()
                std_trafo3w_loading = self.net.res_trafo3w['loading_percent'].std()
                title_trafo3w_loading = f'Min: {min_trafo3w_loading: .1f}    ;    Max: {max_trafo3w_loading: .1f}    ;    Mean: {mean_trafo3w_loading: .1f}    ;    Dstd: {std_trafo3w_loading: .1f}'
                colors = []
                for rate in self.net.res_trafo3w['loading_percent']:
                    if rate<=100:
                        colors.append('mediumaquamarine')
                    else:
                        colors.append('tomato')
                self.net.res_trafo3w.plot(y='loading_percent', kind='bar',
                                    ax=self.ax_trafo3w_loading,
                                    xlabel='Three winding transformer',
                                    ylabel='Loading (%)',
                                    title=title_trafo3w_loading,
                                    color=colors)
                
                if self.theme=='dark':
                    self.ax_trafo3w_loading.xaxis.label.set_color('white')
                    self.ax_trafo3w_loading.yaxis.label.set_color('white')
                    self.ax_trafo3w_loading.title.set_color('white')

            if not self.net.res_gen.empty:
                self.ax_gen_q_mvar.clear()
                self.net.res_gen.plot(y='q_mvar', kind='bar',
                                    ax=self.ax_gen_q_mvar,
                                    xlabel='Generator (PV mode)',
                                    ylabel='Reactive generated power (Mvar)',
                                    color='skyblue')

                if self.theme=='dark':
                    self.ax_gen_q_mvar.xaxis.label.set_color('white')
                    self.ax_gen_q_mvar.yaxis.label.set_color('white')
                    self.ax_gen_q_mvar.title.set_color('white')

        except KeyError:
            pass
         
        # Updating the figures view:
        for figure in self.list_of_figures:
            figure.canvas.draw()
            figure.canvas.flush_events()


class Settings_Dialog:
    """
    Returns the settings dialog.
    
    * main_window: Main window of the application (parent)
    * config: Config parser with all the settings
    * dataframe_line_stds: pandas DataFrame with standard line parameters, obtained
                    with pp.available_std_types(self.net, 'line')
    * dataframe_trafo_stds: pandas DataFrame with standard 2W-transformer parameters, obtained
                    with pp.available_std_types(self.net, 'trafo')
    * dataframe_trafo3w_stds: pandas DataFrame with standard 2W-transformer parameters, obtained
                    with pp.available_std_types(self.net, 'trafo3w')
    """
    def __init__(self, main_window, config, dataframe_line_stds,
                 dataframe_trafo_stds, dataframe_trafo3w_stds):
        self.main_window = main_window
        self.config = config
        self.dataframe_line_stds = dataframe_line_stds
        self.dataframe_trafo_stds = dataframe_trafo_stds
        self.dataframe_trafo3w_stds = dataframe_trafo3w_stds
        
    def exec(self):
        """
        Shows the dialog and returns the modified settings (config parser).
        """
        ui_file = os.path.join(directory, 'settings_dialog.ui')
        # self.dialog = QtCompat.loadUi(uifile=ui_file)
        ui_file_ = QtCore.QFile(ui_file)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        self.dialog = loader.load(ui_file_)
        self.dialog.restore_settings.clicked.connect(self.restore_defaults)
        
        root_dir, _ = os.path.split(directory)
        app_icon_dir = os.path.join(root_dir, 'icons', 'app_icon.png')
        self.dialog.setWindowIcon(QtGui.QIcon(app_icon_dir))
        
        # General page-----------------------------------------------------
        theme_options = 'light', 'dark', 'auto', 'system'
        index_theme = theme_options.index(self.config['general']['theme'])
        self.dialog.theme.setCurrentIndex(index_theme)
        if self.config['general']['grid']=='True':
            self.dialog.grid.setChecked(True)
        else:
            self.dialog.grid.setChecked(False)
        pipe_style_options = 'curved', 'straight', 'angle'
        index_pipe_style = pipe_style_options.index(self.config['general']['pipe_style'])
        self.dialog.pipe_style.setCurrentIndex(index_pipe_style)
        default_path = self.config['general']['default_path']
        if os.path.exists(default_path):
            self.dialog.default_path.setPlainText(default_path)
        else:
            self.dialog.default_path.setPlainText(str(Path.home()))
        self.dialog.btn_change_default_path.clicked.connect(self.change_default_path)
        
        # Network page------------------------------------------------------
        ui_file_network = os.path.join(directory, 'network_settings_dialog.ui')
        # network = QtCompat.loadUi(uifile=ui_file_network)  # dialog
        ui_file_ = QtCore.QFile(ui_file_network)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        network = loader.load(ui_file_)  # dialog
        network.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['network']
        network.name.setText(settings['name'])
        network.sn_mva.setValue(float(settings['sn_mva']))
        network.f_hz.setValue(float(settings['f_hz']))
        
        layout_network = QtWidgets.QVBoxLayout()
        layout_network.addWidget(network)
        layout_network.addStretch()
        self.dialog.page_network.setLayout(layout_network)
        
        # Balanced AC Power Flow page--------------------------------------
        ui_file_pf = os.path.join(directory, 'pf_settings_widget.ui')
        ui_file_ = QtCore.QFile(ui_file_pf)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        pf = loader.load(ui_file_)  # dialog
        # pf = QtCompat.loadUi(uifile=ui_file_pf)
        
        settings = self.config['pf']
        booleans = {'True': True, 'False': False}
        methods = ['nr', 'iwamoto_nr', 'bfsw', 'gs',
                   'fdbx', 'fdxb']  # solvers
        init_methods = ['auto', 'flat', 'dc', 'results']  # methods for initialization
        trafo_models = ['t', 'pi']
        trafo_loadings = ['current', 'power']
        trafo3w_losses_options = ['hv', 'mv', 'lv', 'star']
        
        for name, value in settings.items():
            if name=='algorithm':
                index = methods.index(value)
                pf.algorithm.setCurrentIndex(index)
            elif name=='max_iteration':
                pf.max_iteration.setValue(int(value))
            elif name=='tolerance_mva':
                pf.tolerance_mva.setValue(float(value))
            elif name=='delta_q':
                pf.delta_q.setValue(float(value))
            elif name=='check_connectivity':
                pf.check_connectivity.setChecked(booleans[value])
            elif name=='init':
                index = init_methods.index(value)
                pf.init.setCurrentIndex(index)
            elif name=='trafo_model':
                index = trafo_models.index(value)
                pf.trafo_model.setCurrentIndex(index)
            elif name=='trafo_loading':
                index = trafo_loadings.index(value)
                pf.trafo_loading.setCurrentIndex(index)
            elif name=='trafo3w_losses':
                index = trafo3w_losses_options.index(value)
                pf.trafo3w_losses.setCurrentIndex(index)
            elif name=='switch_rx_ratio':
                pf.switch_rx_ratio.setValue(float(value))
            elif name=='neglect_open_switch_branches':
                pf.neglect_open_switch_branches.setChecked(booleans[value])
            elif name=='enforce_q_lims':
                pf.enforce_q_lims.setChecked(booleans[value])
            elif name=='voltage_depend_loads':
                pf.voltage_depend_loads.setChecked(booleans[value])
            elif name=='consider_line_temperature':
                pf.consider_line_temperature.setChecked(booleans[value])
            elif name=='distributed_slack':
                pf.distributed_slack.setChecked(booleans[value])
            elif name=='tdpf':
                pf.tdpf.setChecked(booleans[value])
            elif name=='tdpf_delay_s' and value=='None':
                pf.tdpf_delay_s_check.setChecked(False)
            elif name=='tdpf_delay_s' and value!='None':
                pf.tdpf_delay_s_check.setChecked(True)
                pf.tdpf_delay_s.setValue(float(value))
            elif name=='tdpf_update_r_theta':
                pf.tdpf_update_r_theta.setChecked(booleans[value])
        
        layout_pf = QtWidgets.QVBoxLayout()
        layout_pf.addWidget(pf)
        layout_pf.addStretch()
        self.dialog.page_pf.setLayout(layout_pf)
        
        # Bus page---------------------------------------------------------
        ui_file_bus = os.path.join(directory, 'bus_dialog.ui')
        # bus = QtCompat.loadUi(uifile=ui_file_bus)  # dialog
        ui_file_ = QtCore.QFile(ui_file_bus)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        bus = loader.load(ui_file_)  # dialog
        bus.buttonBox.setParent(None)  # remove the button box
        
        def bus_min_vm_pu_changed(value):
            bus.max_vm_pu.setMinimum(value)
        
        def bus_max_vm_pu_changed(value):
            bus.min_vm_pu.setMaximum(value)
    
        bus.min_vm_pu.valueChanged.connect(bus_min_vm_pu_changed)
        bus.max_vm_pu.valueChanged.connect(bus_max_vm_pu_changed)
        
        settings = self.config['bus']
        bus.vn_kv.setValue(float(settings['vn_kv']))
        bus.min_vm_pu.setValue(float(settings['min_vm_pu']))
        bus.max_vm_pu.setValue(float(settings['max_vm_pu']))
        
        layout_bus = QtWidgets.QVBoxLayout()
        layout_bus.addWidget(bus)
        layout_bus.addStretch()
        self.dialog.page_bus.setLayout(layout_bus)
        
        # AC line page-----------------------------------------------------
        ui_file_line = os.path.join(directory, 'line_dialog.ui')
        # line = QtCompat.loadUi(uifile=ui_file_line)  # dialog
        ui_file_ = QtCore.QFile(ui_file_line)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        line = loader.load(ui_file_)  # dialog
        line.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['line']
        line.length_km.setValue(float(settings['length_km']))
        line.parallel.setValue(float(settings['parallel']))
        line.df.setValue(float(settings['df']))
        line.r_ohm_per_km.setValue(float(settings['r_ohm_per_km']))
        line.x_ohm_per_km.setValue(float(settings['x_ohm_per_km']))
        line.c_nf_per_km.setValue(float(settings['c_nf_per_km']))
        line.g_us_per_km.setValue(float(settings['g_us_per_km']))
        line.max_i_ka.setValue(float(settings['max_i_ka']))
        line.r0_ohm_per_km.setValue(float(settings['r0_ohm_per_km']))
        line.x0_ohm_per_km.setValue(float(settings['x0_ohm_per_km']))
        line.c0_nf_per_km.setValue(float(settings['c0_nf_per_km']))
        line.g0_us_per_km.setValue(float(settings['g0_us_per_km']))
        line.max_loading_percent.setValue(float(settings['max_loading_percent']))
        line.alpha.setValue(float(settings['alpha']))
        line.temperature_degree_celsius.setValue(float(settings['temperature_degree_celsius']))
        line.endtemp_degree.setValue(float(settings['endtemp_degree']))
        
        layout_line = QtWidgets.QVBoxLayout()
        layout_line.addWidget(line)
        layout_line.addStretch()
        self.dialog.page_line.setLayout(layout_line)
        
        # Standard AC line page--------------------------------------------
        ui_file_stdline = os.path.join(directory, 'stdline_dialog.ui')
        # stdline = QtCompat.loadUi(uifile=ui_file_stdline)  # dialog
        ui_file_ = QtCore.QFile(ui_file_stdline)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        stdline = loader.load(ui_file_)  # dialog
        stdline.buttonBox.setParent(None)  # remove the button box
        
        stds_line = self.dataframe_line_stds.index.tolist()
        stdline.std_type.addItems(stds_line)
        index_std = stds_line.index(self.config['stdline']['std_type'])
        stdline.std_type.setCurrentIndex(index_std)
        
        pre_table = self.dataframe_line_stds.iloc[index_std, :]
        table_data = pd.DataFrame(data=pre_table.values,
                            index=pre_table.index,
                            columns=['Parameter'])
        
        table_std = TableWidget(table_data)
        stdline.layout_table.addWidget(table_std)
        height = table_std.table.horizontalHeader().height()
        for row in range(table_std.model.rowCount(None)):
            height += table_std.table.rowHeight(row)
        stdline.widget_table_container.setMinimumHeight(height * 1.2)
        
        settings = self.config['stdline']
        stdline.length_km.setValue(float(settings['length_km']))
        stdline.parallel.setValue(float(settings['parallel']))
        stdline.df.setValue(float(settings['df']))
        stdline.max_loading_percent.setValue(float(settings['max_loading_percent']))
        
        def update_table_stdline(std_name):
            old_table = stdline.layout_table.itemAt(0).widget()
            old_table.setParent(None)
            
            index_std = stds_line.index(std_name)
            
            pre_table = self.dataframe_line_stds.iloc[index_std, :]
            table_data = pd.DataFrame(data=pre_table.values,
                                index=pre_table.index,
                                columns=['Parameter'])
            
            table_std = TableWidget(table_data)
            stdline.layout_table.addWidget(table_std)
            
            height = table_std.table.horizontalHeader().height()
            for row in range(table_std.model.rowCount(None)):
                height += table_std.table.rowHeight(row)
            stdline.widget_table_container.setMinimumHeight(height * 1.2)
    
        stdline.std_type.currentTextChanged.connect(update_table_stdline)
        
        layout_stdline = QtWidgets.QVBoxLayout()
        layout_stdline.addWidget(stdline)
        layout_stdline.addStretch()
        self.dialog.page_stdline.setLayout(layout_stdline)
        
        # DC line page-----------------------------------------------------
        ui_file_dcline = os.path.join(directory, 'dcline_dialog.ui')
        # dcline = QtCompat.loadUi(uifile=ui_file_dcline)  # dialog
        ui_file_ = QtCore.QFile(ui_file_dcline)
        ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        dcline = loader.load(ui_file_)  # dialog
        dcline.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['dcline']
        dcline.p_mw.setValue(float(settings['p_mw']))
        dcline.loss_percent.setValue(float(settings['loss_percent']))
        dcline.loss_mw.setValue(float(settings['loss_mw']))
        dcline.vm_from_pu.setValue(float(settings['vm_from_pu']))
        dcline.vm_to_pu.setValue(float(settings['vm_to_pu']))
        dcline.max_p_mw.setValue(float(settings['max_p_mw']))
        dcline.min_q_from_mvar.setValue(float(settings['min_q_from_mvar']))
        dcline.min_q_to_mvar.setValue(float(settings['min_q_to_mvar']))
        dcline.max_q_from_mvar.setValue(float(settings['max_q_from_mvar']))
        dcline.max_q_to_mvar.setValue(float(settings['max_q_to_mvar']))
        
        layout_dcline = QtWidgets.QVBoxLayout()
        layout_dcline.addWidget(dcline)
        layout_dcline.addStretch()
        self.dialog.page_dcline.setLayout(layout_dcline)
        
        # Impedance page---------------------------------------------------
        ui_file_impedance = os.path.join(directory, 'impedance_dialog.ui')
        impedance = return_qtwindow(ui_file_impedance)  # dialog
        impedance.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['impedance']
        impedance.rft_pu.setValue(float(settings['rft_pu']))
        impedance.xft_pu.setValue(float(settings['xft_pu']))
        impedance.sn_mva.setValue(float(settings['sn_mva']))
        impedance.rtf_pu.setValue(float(settings['rtf_pu']))
        impedance.xtf_pu.setValue(float(settings['xtf_pu']))
        impedance.rft0_pu.setValue(float(settings['rft0_pu']))
        impedance.xft0_pu.setValue(float(settings['xft0_pu']))
        impedance.rtf0_pu.setValue(float(settings['rtf0_pu']))
        impedance.xtf0_pu.setValue(float(settings['xtf0_pu']))
        
        layout_impedance = QtWidgets.QVBoxLayout()
        layout_impedance.addWidget(impedance)
        layout_impedance.addStretch()
        self.dialog.page_impedance.setLayout(layout_impedance)
        
        # Two winding transformer page-------------------------------------
        ui_file_trafo = os.path.join(directory, 'transformer_dialog.ui')
        trafo = return_qtwindow(ui_file_trafo)
        trafo.buttonBox.setParent(None)  # remove the button box
        
        def trafo_tap_min_changed(value):
            trafo.tap_pos.setMinimum(value)
            trafo.tap_neutral.setMinimum(value)
            
            if value>trafo.tap_max.value():
                trafo.tap_max.setValue(value)
            if value>trafo.tap_pos.value():
                trafo.tap_pos.setValue(value)
        
        def trafo_tap_max_changed(value):
            trafo.tap_pos.setMaximum(value)
            trafo.tap_neutral.setMaximum(value)
            
            if value<trafo.tap_min.value():
                trafo.tap_min.setValue(value)
            if value<trafo.tap_pos.value():
                trafo.tap_pos.setValue(value)
    
        trafo.tap_min.valueChanged.connect(trafo_tap_min_changed)
        trafo.tap_max.valueChanged.connect(trafo_tap_max_changed)
        
        settings = self.config['trafo']
        trafo.sn_mva.setValue(float(settings['sn_mva']))
        trafo.vn_hv_kv.setValue(float(settings['vn_hv_kv']))
        trafo.vn_lv_kv.setValue(float(settings['vn_lv_kv']))
        trafo.vkr_percent.setValue(float(settings['vkr_percent']))
        trafo.vk_percent.setValue(float(settings['vk_percent']))
        trafo.pfe_kw.setValue(float(settings['pfe_kw']))
        trafo.i0_percent.setValue(float(settings['i0_percent']))
        trafo.shift_degree.setValue(float(settings['shift_degree']))
        trafo.tap_neutral.setValue(float(settings['tap_neutral']))
        
        trafo.tap_max.setValue(float(settings['tap_max']))
        trafo.tap_min.setValue(float(settings['tap_min']))
        trafo.tap_step_percent.setValue(float(settings['tap_step_percent']))
        trafo.tap_step_degree.setValue(float(settings['tap_step_degree']))
        trafo.tap_pos.setValue(float(settings['tap_pos']))
        trafo.tap_pos_display.setText(str(settings['tap_pos']))
        trafo.max_loading_percent.setValue(float(settings['max_loading_percent']))
        trafo.parallel.setValue(float(settings['parallel']))
        trafo.df.setValue(float(settings['df']))
        trafo.vk0_percent.setValue(float(settings['vk0_percent']))
        trafo.vkr0_percent.setValue(float(settings['vkr0_percent']))
        trafo.mag0_percent.setValue(float(settings['mag0_percent']))
        trafo.mag0_rx.setValue(float(settings['mag0_rx']))
        trafo.si0_hv_partial.setValue(float(settings['si0_hv_partial']))
        trafo.xn_ohm.setValue(float(settings['xn_ohm']))
        trafo.tap_phase_shifter.setChecked(True if settings['tap_phase_shifter']=='True' else False)
        trafo.oltc.setChecked(True if settings['oltc']=='True' else False)
        trafo_tap_side_options = 'hv', 'lv'
        trafo.tap_side.setCurrentIndex(trafo_tap_side_options.index(settings['tap_side']))
        trafo_vector_group_options = 'Dyn', 'Yyn', 'Yzn', 'YNyn'
        trafo.vector_group.setCurrentIndex(trafo_vector_group_options.index(settings['vector_group']))
        
        layout_trafo = QtWidgets.QVBoxLayout()
        scroll_area_trafo = QtWidgets.QScrollArea()
        scroll_area_trafo.setWidget(trafo)
        scroll_area_trafo.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout_trafo.addWidget(scroll_area_trafo)
        # layout_trafo.addStretch()
        self.dialog.page_trafo.setLayout(layout_trafo)
        
        # Standard two winding transformer page----------------------------
        ui_file_stdtrafo = os.path.join(directory, 'stdtransformer_dialog.ui')
        stdtrafo = return_qtwindow(ui_file_stdtrafo)
        stdtrafo.buttonBox.setParent(None)  # remove the button box
        stdtrafo.label_tap_pos.setParent(None)  # remove the tap position options
        stdtrafo.tap_pos.setParent(None)
        stdtrafo.tap_pos_display.setParent(None)
        stdtrafo.layout_tap_pos.setParent(None)
        
        stds_trafo = self.dataframe_trafo_stds.index.tolist()
        stdtrafo.std_type.addItems(stds_trafo)
        index_stdtrafo = stds_trafo.index(self.config['stdtrafo']['std_type'])
        stdtrafo.std_type.setCurrentIndex(index_stdtrafo)
        
        pre_table_stdtrafo = self.dataframe_trafo_stds.iloc[index_stdtrafo, :]
        table_data_stdtrafo = pd.DataFrame(data=pre_table_stdtrafo.values,
                                           index=pre_table_stdtrafo.index,
                                           columns=['Parameter'])
        
        table_std_stdtrafo = TableWidget(table_data_stdtrafo)
        stdtrafo.layout_table.addWidget(table_std_stdtrafo)
        
        def stdtrafo_update_table(std_name):
            old_table = stdtrafo.layout_table.itemAt(0).widget()
            old_table.setParent(None)
            
            index_stdtrafo = stds_trafo.index(std_name)
            
            pre_table_stdtrafo = self.dataframe_trafo_stds.iloc[index_stdtrafo, :]
            table_data = pd.DataFrame(data=pre_table_stdtrafo.values,
                                index=pre_table_stdtrafo.index,
                                columns=['Parameter'])
            
            table_std = TableWidget(table_data)
            stdtrafo.layout_table.addWidget(table_std)
        
        stdtrafo.std_type.currentTextChanged.connect(stdtrafo_update_table)
        
        settings = self.config['stdtrafo']
        stdtrafo.vk0_percent.setValue(float(settings['vk0_percent']))
        stdtrafo.vkr0_percent.setValue(float(settings['vkr0_percent']))
        stdtrafo.mag0_percent.setValue(float(settings['mag0_percent']))
        stdtrafo.mag0_rx.setValue(float(settings['mag0_rx']))
        stdtrafo.si0_hv_partial.setValue(float(settings['si0_hv_partial']))
        stdtrafo.xn_ohm.setValue(float(settings['xn_ohm']))
        stdtrafo.parallel.setValue(float(settings['parallel']))
        stdtrafo.df.setValue(float(settings['df']))
        stdtrafo.max_loading_percent.setValue(float(settings['max_loading_percent']))
        
        layout_stdtrafo = QtWidgets.QVBoxLayout()
        scroll_area_stdtrafo = QtWidgets.QScrollArea()
        scroll_area_stdtrafo.setWidget(stdtrafo)
        scroll_area_stdtrafo.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout_stdtrafo.addWidget(scroll_area_stdtrafo)
        layout_stdtrafo.addStretch()
        self.dialog.page_stdtrafo.setLayout(layout_stdtrafo)
        
        # Three winding transformer page-----------------------------------
        ui_file_trafo3w = os.path.join(directory, 'transformer3w_dialog.ui')
        trafo3w = return_qtwindow(ui_file_trafo3w)
        trafo3w.buttonBox.setParent(None)  # remove the button box
        
        def trafo3w_tap_min_changed(value):
            trafo3w.tap_pos.setMinimum(value)
            trafo3w.tap_neutral.setMinimum(value)
            
            if value>trafo3w.tap_max.value():
                trafo3w.tap_max.setValue(value)
            if value>trafo3w.tap_pos.value():
                trafo3w.tap_pos.setValue(value)
        
        def trafo3w_tap_max_changed(value):
            trafo3w.tap_pos.setMaximum(value)
            trafo3w.tap_neutral.setMaximum(value)
            
            if value<trafo3w.tap_min.value():
                trafo3w.tap_min.setValue(value)
            if value<trafo3w.tap_pos.value():
                trafo3w.tap_pos.setValue(value)
        
        trafo3w.tap_min.valueChanged.connect(trafo3w_tap_min_changed)
        trafo3w.tap_max.valueChanged.connect(trafo3w_tap_max_changed)
        
        settings = self.config['trafo3w']
        trafo3w.sn_hv_mva.setValue(float(settings['sn_hv_mva']))
        trafo3w.sn_mv_mva.setValue(float(settings['sn_mv_mva']))
        trafo3w.sn_lv_mva.setValue(float(settings['sn_lv_mva']))
        trafo3w.vn_hv_kv.setValue(float(settings['vn_hv_kv']))
        trafo3w.vn_mv_kv.setValue(float(settings['vn_mv_kv']))
        trafo3w.vn_lv_kv.setValue(float(settings['vn_lv_kv']))
        trafo3w.vkr_hv_percent.setValue(float(settings['vkr_hv_percent']))
        trafo3w.vkr_mv_percent.setValue(float(settings['vkr_mv_percent']))
        trafo3w.vkr_lv_percent.setValue(float(settings['vkr_lv_percent']))
        trafo3w.vk_hv_percent.setValue(float(settings['vk_hv_percent']))
        trafo3w.vk_mv_percent.setValue(float(settings['vk_mv_percent']))
        trafo3w.vk_lv_percent.setValue(float(settings['vk_lv_percent']))
        trafo3w.pfe_kw.setValue(float(settings['pfe_kw']))
        trafo3w.i0_percent.setValue(float(settings['i0_percent']))
        trafo3w.shift_mv_degree.setValue(float(settings['shift_mv_degree']))
        trafo3w.shift_lv_degree.setValue(float(settings['shift_lv_degree']))
        trafo3w.tap_neutral.setValue(float(settings['tap_neutral']))
        
        trafo3w.tap_max.setValue(float(settings['tap_max']))
        trafo3w.tap_min.setValue(float(settings['tap_min']))
        trafo3w.tap_step_percent.setValue(float(settings['tap_step_percent']))
        trafo3w.tap_step_degree.setValue(float(settings['tap_step_degree']))
        trafo3w.tap_pos.setValue(float(settings['tap_pos']))
        trafo3w.tap_pos_display.setText(str(int(settings['tap_pos'])))
        trafo3w.max_loading_percent.setValue(float(settings['max_loading_percent']))
        trafo3w.vk0_hv_percent.setValue(float(settings['vk0_hv_percent']))
        trafo3w.vk0_mv_percent.setValue(float(settings['vk0_mv_percent']))
        trafo3w.vk0_lv_percent.setValue(float(settings['vk0_lv_percent']))
        trafo3w.vkr0_hv_percent.setValue(float(settings['vkr0_hv_percent']))
        trafo3w.vkr0_mv_percent.setValue(float(settings['vkr0_mv_percent']))
        trafo3w.vkr0_lv_percent.setValue(float(settings['vkr0_lv_percent']))
        trafo3w.tap_at_star_point.setChecked(True if settings['tap_at_star_point']=='True' else False)
        trafo3w_tap_side_options = 'hv', 'mv', 'lv'
        trafo3w.tap_side.setCurrentIndex(trafo3w_tap_side_options.index(settings['tap_side']))
        trafo3w_vector_group_options = ('Ddd', 'Ddy', 'Dyd', 'Dyy', 'Ydd', 'Ydy',
                                        'Yyd', 'Yyy', 'YNyd', 'YNdy', 'Yynd',
                                        'Ydyn', 'YNynd', 'YNdyn', 'YNdd', 'YNyy')
        trafo3w.vector_group.setCurrentIndex(trafo3w_vector_group_options.index(settings['vector_group']))
        
        layout_trafo3w = QtWidgets.QVBoxLayout()
        scroll_area_trafo3w = QtWidgets.QScrollArea()
        scroll_area_trafo3w.setWidget(trafo3w)
        scroll_area_trafo3w.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout_trafo3w.addWidget(scroll_area_trafo3w)
        # layout_trafo3w.addStretch()
        self.dialog.page_trafo3w.setLayout(layout_trafo3w)
        
        # Standard three winding transformer page--------------------------
        ui_file_stdtrafo3w = os.path.join(directory, 'stdtransformer3w_dialog.ui')
        stdtrafo3w = return_qtwindow(ui_file_stdtrafo3w)
        stdtrafo3w.buttonBox.setParent(None)  # remove the button box
        stdtrafo3w.label_tap_pos.setParent(None)  # remove the tap position options
        stdtrafo3w.tap_pos.setParent(None)
        stdtrafo3w.tap_pos_display.setParent(None)
        stdtrafo3w.layout_tap_pos.setParent(None)
        
        stds_trafo3w = self.dataframe_trafo3w_stds.index.tolist()
        stdtrafo3w.std_type.addItems(stds_trafo3w)
        index_stdtrafo3w = stds_trafo3w.index(self.config['stdtrafo3w']['std_type'])
        stdtrafo3w.std_type.setCurrentIndex(index_stdtrafo3w)
        
        pre_table3w = self.dataframe_trafo3w_stds.iloc[index_stdtrafo3w, :]
        table_data3w = pd.DataFrame(data=pre_table3w.values,
                                    index=pre_table3w.index,
                                    columns=['Parameter'])
        
        table_std = TableWidget(table_data3w)
        stdtrafo3w.layout_table.addWidget(table_std)
        
        def update_table(std_name):
            old_table = stdtrafo3w.layout_table.itemAt(0).widget()
            old_table.setParent(None)
            
            index_stdtrafo3w = stds_trafo3w.index(std_name)
            
            pre_table3w = self.dataframe_trafo3w_stds.iloc[index_stdtrafo3w, :]
            table_data3w = pd.DataFrame(data=pre_table3w.values,
                                        index=pre_table3w.index,
                                        columns=['Parameter'])
            
            table_std_3w = TableWidget(table_data3w)
            stdtrafo3w.layout_table.addWidget(table_std_3w)
        
        stdtrafo3w.std_type.currentTextChanged.connect(update_table)
        
        settings = self.config['stdtrafo3w']
        stdtrafo3w.tap_at_star_point.setChecked(True if settings['tap_at_star_point']=='True' else False)
        stdtrafo3w.max_loading_percent.setValue(float(settings['max_loading_percent']))
        
        layout_stdtrafo3w = QtWidgets.QVBoxLayout()
        scroll_area_stdtrafo3w = QtWidgets.QScrollArea()
        scroll_area_stdtrafo3w.setWidget(stdtrafo3w)
        scroll_area_stdtrafo3w.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout_stdtrafo3w.addWidget(scroll_area_stdtrafo3w)
        layout_stdtrafo3w.addStretch()
        self.dialog.page_stdtrafo3w.setLayout(layout_stdtrafo3w)
        
        # Generator (PV mode) page-----------------------------------------
        ui_file_gen = os.path.join(directory, 'gen_dialog.ui')
        gen = return_qtwindow(ui_file_gen)
        gen.buttonBox.setParent(None)  # remove the button box
        
        def gen_min_vm_pu_changed(value):
            gen.vm_pu.setMinimum(value)
            gen.max_vm_pu.setMinimum(value)
            
        def gen_max_vm_pu_changed(value):
            gen.vm_pu.setMaximum(value)
            gen.min_vm_pu.setMaximum(value)
            
        def gen_min_p_mw_changed(value):
            gen.p_mw.setMinimum(value)
            gen.max_p_mw.setMinimum(value)
            
        def gen_max_p_mw_changed(value):
            gen.p_mw.setMaximum(value)
            gen.min_p_mw.setMaximum(value)
        
        gen.min_vm_pu.valueChanged.connect(gen_min_vm_pu_changed)
        gen.max_vm_pu.valueChanged.connect(gen_max_vm_pu_changed)
        gen.min_p_mw.valueChanged.connect(gen_min_p_mw_changed)
        gen.max_p_mw.valueChanged.connect(gen_max_p_mw_changed)
        
        settings = self.config['gen']
        gen.controllable.setChecked(True if settings['controllable']=='True' else False)
        gen.p_mw.setValue(float(settings['p_mw']))
        gen.vm_pu.setValue(float(settings['vm_pu']))
        gen.sn_mva.setValue(float(settings['sn_mva']))
        gen.scaling.setValue(float(settings['scaling']))
        gen.slack_weight.setValue(float(settings['slack_weight']))
        gen.vn_kv.setValue(float(settings['vn_kv']))
        gen.xdss_pu.setValue(float(settings['xdss_pu']))
        gen.rdss_ohm.setValue(float(settings['rdss_ohm']))
        gen.cos_phi.setValue(float(settings['cos_phi']))
        gen.max_p_mw.setValue(float(settings['max_p_mw']))
        gen.min_p_mw.setValue(float(settings['min_p_mw']))
        gen.max_q_mvar.setValue(float(settings['max_q_mvar']))
        gen.min_q_mvar.setValue(float(settings['min_q_mvar']))
        gen.min_vm_pu.setValue(float(settings['min_vm_pu']))
        gen.max_vm_pu.setValue(float(settings['max_vm_pu']))
        
        layout_gen = QtWidgets.QVBoxLayout()
        layout_gen.addWidget(gen)
        layout_gen.addStretch()
        self.dialog.page_gen.setLayout(layout_gen)
        
        # Static generator page--------------------------------------------
        ui_file_sgen = os.path.join(directory, 'sgen_dialog.ui')
        sgen = return_qtwindow(ui_file_sgen)
        sgen.buttonBox.setParent(None)  # remove the button box
            
        def sgen_min_p_mw_changed(value):
            sgen.p_mw.setMinimum(value)
            sgen.max_p_mw.setMinimum(value)
            
        def sgen_max_p_mw_changed(value):
            sgen.p_mw.setMaximum(value)
            sgen.min_p_mw.setMaximum(value)
            
        def sgen_min_q_mvar_changed(value):
            sgen.q_mvar.setMinimum(value)
            sgen.max_q_mvar.setMinimum(value)
            
        def sgen_max_q_mvar_changed(value):
            sgen.q_mvar.setMaximum(value)
            sgen.min_q_mvar.setMaximum(value)
        
        sgen.min_p_mw.valueChanged.connect(sgen_min_p_mw_changed)
        sgen.max_p_mw.valueChanged.connect(sgen_max_p_mw_changed)
        sgen.min_q_mvar.valueChanged.connect(sgen_min_q_mvar_changed)
        sgen.max_q_mvar.valueChanged.connect(sgen_max_q_mvar_changed)
        
        settings = self.config['sgen']
        sgen.p_mw.setValue(float(settings['p_mw']))
        sgen.q_mvar.setValue(float(settings['q_mvar']))
        sgen.sn_mva.setValue(float(settings['sn_mva']))
        sgen.scaling.setValue(float(settings['scaling']))
        sgen.max_p_mw.setValue(float(settings['max_p_mw']))
        sgen.min_p_mw.setValue(float(settings['min_p_mw']))
        sgen.max_q_mvar.setValue(float(settings['max_q_mvar']))
        sgen.min_q_mvar.setValue(float(settings['min_q_mvar']))
        sgen.current_source.setChecked(True if settings['current_source']=='True' else False)
        sgen.controllable.setChecked(True if settings['controllable']=='True' else False)
        if settings['k']=='NaN':
            sgen.k_check.setChecked(False)
        else:
            sgen.k_check.setChecked(True)
            sgen.k.setValue(float(settings['k']))
        
        if settings['rx']=='NaN':
            sgen.rx_check.setChecked(False)
        else:
            sgen.rx_check.setChecked(True)
            sgen.rx.setValue(float(settings['rx']))
            
        if settings['lrc_pu']=='NaN':
            sgen.lrc_pu_check.setChecked(False)
        else:
            sgen.lrc_pu_check.setChecked(True)
            sgen.lrc_pu.setValue(float(settings['lrc_pu']))
            
        if settings['max_ik_ka']=='NaN':
            sgen.max_ik_ka_check.setChecked(False)
        else:
            sgen.max_ik_ka_check.setChecked(True)
            sgen.max_ik_ka.setValue(float(settings['max_ik_ka']))
            
        if settings['kappa']=='NaN':
            sgen.kappa_check.setChecked(False)
        else:
            sgen.kappa_check.setChecked(True)
            sgen.kappa.setValue(float(settings['kappa']))
            
        sgen_type_options = 'wye', 'delta'
        sgen.type.setCurrentIndex(sgen_type_options.index(settings['type']))
        sgen_generator_type_options = 'None', 'current_source', 'async', 'async_doubly_fed'
        sgen.generator_type.setCurrentIndex(sgen_generator_type_options.index(settings['generator_type']))
        
        layout_sgen = QtWidgets.QVBoxLayout()
        layout_sgen.addWidget(sgen)
        layout_sgen.addStretch()
        self.dialog.page_sgen.setLayout(layout_sgen)
        
        # Asymmetric static generator page---------------------------------
        ui_file_asgen = os.path.join(directory, 'asgen_dialog.ui')
        asgen = return_qtwindow(ui_file_asgen)
        asgen.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['asymmetric_sgen']
        asgen.p_a_mw.setValue(float(settings['p_a_mw']))
        asgen.q_a_mvar.setValue(float(settings['q_a_mvar']))
        asgen.p_b_mw.setValue(float(settings['p_b_mw']))
        asgen.q_b_mvar.setValue(float(settings['q_b_mvar']))
        asgen.p_c_mw.setValue(float(settings['p_c_mw']))
        asgen.q_c_mvar.setValue(float(settings['q_c_mvar']))
        asgen.sn_mva.setValue(float(settings['sn_mva']))
        asgen.scaling.setValue(float(settings['scaling']))
        asgen_type_options = 'wye', 'delta'
        asgen.type.setCurrentIndex(asgen_type_options.index(settings['type']))
        
        layout_asgen = QtWidgets.QVBoxLayout()
        layout_asgen.addWidget(asgen)
        layout_asgen.addStretch()
        self.dialog.page_asymmetric_sgen.setLayout(layout_asgen)
        
        # External grid page-----------------------------------------------
        ui_file_ext_grid = os.path.join(directory, 'ext_grid_dialog.ui')
        ext_grid = return_qtwindow(ui_file_ext_grid)
        ext_grid.buttonBox.setParent(None)  # remove the button box
        
        def ext_grid_min_p_mw_changed(value):
            ext_grid.max_p_mw.setMinimum(value)
            
        def ext_grid_max_p_mw_changed(value):
            ext_grid.min_p_mw.setMaximum(value)
            
        def ext_grid_min_q_mvar_changed(value):
            ext_grid.max_q_mvar.setMinimum(value)
            
        def ext_grid_max_q_mvar_changed(value):
            ext_grid.min_q_mvar.setMaximum(value)
            
        def ext_grid_s_sc_max_mva_changed(value):
            ext_grid.s_sc_min_mva.setMaximum(value)
            
        def ext_grid_s_sc_min_mva_changed(value):
            ext_grid.s_sc_max_mva.setMinimum(value)
        
        ext_grid.min_p_mw.valueChanged.connect(ext_grid_min_p_mw_changed)
        ext_grid.max_p_mw.valueChanged.connect(ext_grid_max_p_mw_changed)
        ext_grid.min_q_mvar.valueChanged.connect(ext_grid_min_q_mvar_changed)
        ext_grid.max_q_mvar.valueChanged.connect(ext_grid_max_q_mvar_changed)
        ext_grid.s_sc_max_mva.valueChanged.connect(ext_grid_s_sc_max_mva_changed)
        ext_grid.s_sc_min_mva.valueChanged.connect(ext_grid_s_sc_min_mva_changed)
        
        settings = self.config['ext_grid']
        ext_grid.vm_pu.setValue(float(settings['vm_pu']))
        ext_grid.va_degree.setValue(float(settings['va_degree']))
        ext_grid.slack_weight.setValue(float(settings['slack_weight']))
        ext_grid.max_p_mw.setValue(float(settings['max_p_mw']))
        ext_grid.min_p_mw.setValue(float(settings['min_p_mw']))
        ext_grid.max_q_mvar.setValue(float(settings['max_q_mvar']))
        ext_grid.min_q_mvar.setValue(float(settings['min_q_mvar']))
        ext_grid.controllable.setChecked(True if settings['controllable']=='True' else False)
        if settings['s_sc_max_mva']=='NaN':
            ext_grid.s_sc_max_mva_check.setChecked(False)
        else:
            ext_grid.s_sc_max_mva_check.setChecked(True)
            ext_grid.s_sc_max_mva.setValue(float(settings['s_sc_max_mva']))
            
        if settings['s_sc_min_mva']=='NaN':
            ext_grid.s_sc_min_mva_check.setChecked(False)
        else:
            ext_grid.s_sc_min_mva_check.setChecked(True)
            ext_grid.s_sc_min_mva.setValue(float(settings['s_sc_min_mva']))
            
        if settings['rx_max']=='NaN':
            ext_grid.rx_max_check.setChecked(False)
        else:
            ext_grid.rx_max_check.setChecked(True)
            ext_grid.rx_max.setValue(float(settings['rx_max']))
            
        if settings['rx_min']=='NaN':
            ext_grid.rx_min_check.setChecked(False)
        else:
            ext_grid.rx_min_check.setChecked(True)
            ext_grid.rx_min.setValue(float(settings['rx_min']))
            
        if settings['r0x0_max']=='NaN':
            ext_grid.r0x0_max_check.setChecked(False)
        else:
            ext_grid.r0x0_max_check.setChecked(True)
            ext_grid.r0x0_max.setValue(float(settings['r0x0_max']))
            
        if settings['x0x_max']=='NaN':
            ext_grid.x0x_max_check.setChecked(False)
        else:
            ext_grid.x0x_max_check.setChecked(True)
            ext_grid.x0x_max.setValue(float(settings['x0x_max']))
        
        layout_ext_grid = QtWidgets.QVBoxLayout()
        layout_ext_grid.addWidget(ext_grid)
        layout_ext_grid.addStretch()
        self.dialog.page_ext_grid.setLayout(layout_ext_grid)
        
        # Load page--------------------------------------------------------
        ui_file_load = os.path.join(directory, 'load_dialog.ui')
        load = return_qtwindow(ui_file_load)
        load.buttonBox.setParent(None)  # remove the button box
        
        def load_min_p_mw_changed(value):
            load.p_mw.setMinimum(value)
            load.max_p_mw.setMinimum(value)
            
        def load_max_p_mw_changed(value):
            load.p_mw.setMaximum(value)
            load.min_p_mw.setMaximum(value)
            
        def load_min_q_mvar_changed(value):
            load.q_mvar.setMinimum(value)
            load.max_q_mvar.setMinimum(value)
            
        def load_max_q_mvar_changed(value):
            load.q_mvar.setMaximum(value)
            load.min_q_mvar.setMaximum(value)
        
        load.min_p_mw.valueChanged.connect(load_min_p_mw_changed)
        load.max_p_mw.valueChanged.connect(load_max_p_mw_changed)
        load.min_q_mvar.valueChanged.connect(load_min_q_mvar_changed)
        load.max_q_mvar.valueChanged.connect(load_max_q_mvar_changed)
        
        settings = self.config['load']
        load.p_mw.setValue(float(settings['p_mw']))
        load.q_mvar.setValue(float(settings['q_mvar']))
        load.const_z_percent.setValue(float(settings['const_z_percent']))
        load.const_i_percent.setValue(float(settings['const_i_percent']))
        load.sn_mva.setValue(float(settings['sn_mva']))
        load.scaling.setValue(float(settings['scaling']))
        load.max_p_mw.setValue(float(settings['max_p_mw']))
        load.min_p_mw.setValue(float(settings['min_p_mw']))
        load.max_q_mvar.setValue(float(settings['max_q_mvar']))
        load.min_q_mvar.setValue(float(settings['min_q_mvar']))
        load.controllable.setChecked(True if settings['controllable']=='True' else False)
        load_type_options = 'wye', 'delta'
        load.type.setCurrentIndex(load_type_options.index(settings['type']))
        
        layout_load = QtWidgets.QVBoxLayout()
        layout_load.addWidget(load)
        layout_load.addStretch()
        self.dialog.page_load.setLayout(layout_load)
        
        # Asymmetric load page---------------------------------------------
        ui_file_aload = os.path.join(directory, 'aload_dialog.ui')
        aload = return_qtwindow(ui_file_aload)
        aload.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['asymmetric_load']
        aload.p_a_mw.setValue(float(settings['p_a_mw']))
        aload.q_a_mvar.setValue(float(settings['q_a_mvar']))
        aload.p_b_mw.setValue(float(settings['p_b_mw']))
        aload.q_b_mvar.setValue(float(settings['q_b_mvar']))
        aload.p_c_mw.setValue(float(settings['p_c_mw']))
        aload.q_c_mvar.setValue(float(settings['q_c_mvar']))
        aload.sn_mva.setValue(float(settings['sn_mva']))
        aload.scaling.setValue(float(settings['scaling']))
        aload_type_options = 'wye', 'delta'
        aload.type.setCurrentIndex(aload_type_options.index(settings['type']))
        
        layout_aload = QtWidgets.QVBoxLayout()
        layout_aload.addWidget(aload)
        layout_aload.addStretch()
        self.dialog.page_asymmetric_load.setLayout(layout_aload)
        
        # Shunt page-------------------------------------------------------
        ui_file_shunt = os.path.join(directory, 'shunt_dialog.ui')
        shunt = return_qtwindow(ui_file_shunt)
        shunt.buttonBox.setParent(None)  # remove the button box
        
        def shunt_max_step_changed(value):
            shunt.step.setMaximum(value)
        
        shunt.max_step.valueChanged.connect(shunt_max_step_changed)
        
        settings = self.config['shunt']
        shunt.p_mw.setValue(float(settings['p_mw']))
        shunt.q_mvar.setValue(float(settings['q_mvar']))
        shunt.step.setValue(float(settings['step']))
        shunt.max_step.setValue(float(settings['max_step']))
        if settings['vn_kv']=='None':
            shunt.vn_kv_check.setChecked(False)
        else:
            shunt.vn_kv_check.setChecked(True)
            shunt.vn_kv.setValue(float(settings['vn_kv']))
        
        layout_shunt = QtWidgets.QVBoxLayout()
        layout_shunt.addWidget(shunt)
        layout_shunt.addStretch()
        self.dialog.page_shunt.setLayout(layout_shunt)
        
        # Motor page-------------------------------------------------------
        ui_file_motor = os.path.join(directory, 'motor_dialog.ui')
        motor = return_qtwindow(ui_file_motor)
        motor.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['motor']
        motor.pn_mech_mw.setValue(float(settings['pn_mech_mw']))
        motor.cos_phi.setValue(float(settings['cos_phi']))
        motor.efficiency_percent.setValue(float(settings['efficiency_percent']))
        motor.loading_percent.setValue(float(settings['loading_percent']))
        motor.scaling.setValue(float(settings['scaling']))
        motor.efficiency_n_percent.setValue(float(settings['efficiency_n_percent']))
        if settings['cos_phi_n']=='NaN':
            motor.cos_phi_n_check.setChecked(False)
        else:
            motor.cos_phi_n_check.setChecked(True)
            motor.cos_phi_n.setValue(float(settings['cos_phi_n']))
            
        if settings['lrc_pu']=='NaN':
            motor.lrc_pu_check.setChecked(False)
        else:
            motor.lrc_pu_check.setChecked(True)
            motor.lrc_pu.setValue(float(settings['lrc_pu']))
            
        if settings['rx']=='NaN':
            motor.rx_check.setChecked(False)
        else:
            motor.rx_check.setChecked(True)
            motor.rx.setValue(float(settings['rx']))
            
        if settings['vn_kv']=='NaN':
            motor.vn_kv_check.setChecked(False)
        else:
            motor.vn_kv_check.setChecked(True)
            motor.vn_kv.setValue(float(settings['vn_kv']))
        
        layout_motor = QtWidgets.QVBoxLayout()
        layout_motor.addWidget(motor)
        layout_motor.addStretch()
        self.dialog.page_motor.setLayout(layout_motor)
        
        # Ward page--------------------------------------------------------
        ui_file_ward = os.path.join(directory, 'ward_dialog.ui')
        ward = return_qtwindow(ui_file_ward)
        ward.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['ward']
        ward.ps_mw.setValue(float(settings['ps_mw']))
        ward.qs_mvar.setValue(float(settings['qs_mvar']))
        ward.pz_mw.setValue(float(settings['pz_mw']))
        ward.qz_mvar.setValue(float(settings['qz_mvar']))
        
        layout_ward = QtWidgets.QVBoxLayout()
        layout_ward.addWidget(ward)
        layout_ward.addStretch()
        self.dialog.page_ward.setLayout(layout_ward)
        
        # Extended ward page-----------------------------------------------
        ui_file_xward = os.path.join(directory, 'xward_dialog.ui')
        xward = return_qtwindow(ui_file_xward)
        xward.buttonBox.setParent(None)  # remove the button box
        
        settings = self.config['xward']
        xward.ps_mw.setValue(float(settings['ps_mw']))
        xward.qs_mvar.setValue(float(settings['qs_mvar']))
        xward.pz_mw.setValue(float(settings['pz_mw']))
        xward.qz_mvar.setValue(float(settings['qz_mvar']))
        xward.r_ohm.setValue(float(settings['r_ohm']))
        xward.x_ohm.setValue(float(settings['x_ohm']))
        xward.vm_pu.setValue(float(settings['vm_pu']))
        xward.slack_weight.setValue(float(settings['slack_weight']))
        
        layout_xward = QtWidgets.QVBoxLayout()
        layout_xward.addWidget(xward)
        layout_xward.addStretch()
        self.dialog.page_xward.setLayout(layout_xward)
        
        # Storage page-----------------------------------------------------
        ui_file_storage = os.path.join(directory, 'storage_dialog.ui')
        storage = return_qtwindow(ui_file_storage)
        storage.buttonBox.setParent(None)  # remove the button box
        
        def storage_min_p_mw_changed(value):
            storage.p_mw.setMinimum(value)
            storage.max_p_mw.setMinimum(value)
            
        def storage_max_p_mw_changed(value):
            storage.p_mw.setMaximum(value)
            storage.min_p_mw.setMaximum(value)
            
        def storage_min_q_mvar_changed(value):
            storage.q_mvar.setMinimum(value)
            storage.max_q_mvar.setMinimum(value)
            
        def storage_max_q_mvar_changed(value):
            storage.q_mvar.setMaximum(value)
            storage.min_q_mvar.setMaximum(value)
            
        def storage_min_e_mwh_changed(value):
            storage.max_e_mwh.setMinimum(value)
            
        def storage_max_e_mwh_changed(value):
            storage.min_e_mwh.setMaximum(value)
            
        storage.min_p_mw.valueChanged.connect(storage_min_p_mw_changed)
        storage.max_p_mw.valueChanged.connect(storage_max_p_mw_changed)
        storage.min_q_mvar.valueChanged.connect(storage_min_q_mvar_changed)
        storage.max_q_mvar.valueChanged.connect(storage_max_q_mvar_changed)
        storage.min_e_mwh.valueChanged.connect(storage_min_e_mwh_changed)
        storage.max_e_mwh.valueChanged.connect(storage_max_e_mwh_changed)
        
        settings = self.config['storage']
        storage.p_mw.setValue(float(settings['p_mw']))
        storage.q_mvar.setValue(float(settings['q_mvar']))
        storage.sn_mva.setValue(float(settings['sn_mva']))
        storage.scaling.setValue(float(settings['scaling']))
        storage.max_e_mwh.setValue(float(settings['max_e_mwh']))
        storage.min_e_mwh.setValue(float(settings['min_e_mwh']))
        storage.soc_percent.setValue(float(settings['soc_percent']))
        storage.max_p_mw.setValue(float(settings['max_p_mw']))
        storage.min_p_mw.setValue(float(settings['min_p_mw']))
        storage.max_q_mvar.setValue(float(settings['max_q_mvar']))
        storage.min_q_mvar.setValue(float(settings['min_q_mvar']))
        storage.controllable.setChecked(True if settings['controllable']=='True' else False)
        storage.type.setText(settings['type'])
        
        layout_storage = QtWidgets.QVBoxLayout()
        layout_storage.addWidget(storage)
        layout_storage.addStretch()
        self.dialog.page_storage.setLayout(layout_storage)
        
        # Switch page------------------------------------------------------
        ui_file_switch = os.path.join(directory, 'switch_dialog.ui')
        switch = return_qtwindow(ui_file_switch)
        switch.buttonBox.setParent(None)  # remove the button box
        # switch.layout_closed.setParent(None)
        # switch.closed.setParent(None)
        
        settings = self.config['switch']
        switch.closed.setChecked(True if settings['closed']=='True' else False)
        switch_type_options = 'None', 'LS', 'CB', 'LBS', 'DS'
        switch.type.setCurrentIndex(switch_type_options.index(settings['type']))
        switch.z_ohm.setValue(float(settings['z_ohm']))
        if settings['in_ka']=='NaN':
            switch.in_ka_check.setChecked(False)
        else:
            switch.in_ka_check.setChecked(True)
            switch.in_ka.setValue(float(settings['in_ka']))
        
        layout_switch = QtWidgets.QVBoxLayout()
        layout_switch.addWidget(switch)
        layout_switch.addStretch()
        self.dialog.page_switch.setLayout(layout_switch)
        
        
        
        self.build_list_views()
            
        if self.dialog.exec():
            # General page-----------------------------------------------------------
            self.config['general']['theme'] = theme_options[self.dialog.theme.currentIndex()]
            self.config['general']['pipe_style'] = pipe_style_options[self.dialog.pipe_style.currentIndex()]
            if self.dialog.grid.isChecked():
                self.config['general']['grid'] = 'True'
            else:
                self.config['general']['grid'] = 'False'
            self.config['general']['default_path'] = self.dialog.default_path.toPlainText()
            
            # Network page-----------------------------------------------------------
            self.config['network']['name'] = network.name.text()
            self.config['network']['sn_mva'] = str(network.sn_mva.value())
            self.config['network']['f_hz'] = str(network.f_hz.value())
            
            # Balanced AC Power Flow page--------------------------------------------
            self.config['pf']['algorithm'] = methods[pf.algorithm.currentIndex()]
            self.config['pf']['max_iteration'] = str(pf.max_iteration.value())
            self.config['pf']['tolerance_mva'] = str(pf.tolerance_mva.value())
            self.config['pf']['delta_q'] = str(pf.delta_q.value())
            self.config['pf']['check_connectivity'] = 'True' if pf.check_connectivity.isChecked() else 'False'
            self.config['pf']['init'] = init_methods[pf.init.currentIndex()]
            self.config['pf']['trafo_model'] = trafo_models[pf.trafo_model.currentIndex()]
            self.config['pf']['trafo_loading'] = trafo_loadings[pf.trafo_loading.currentIndex()]
            self.config['pf']['trafo3w_losses'] = trafo3w_losses_options[pf.trafo3w_losses.currentIndex()]
            self.config['pf']['switch_rx_ratio'] = str(pf.switch_rx_ratio.value())
            self.config['pf']['neglect_open_switch_branches'] = 'True' if pf.neglect_open_switch_branches.isChecked() else 'False'
            self.config['pf']['enforce_q_lims'] = 'True' if pf.enforce_q_lims.isChecked() else 'False'
            self.config['pf']['voltage_depend_loads'] = 'True' if pf.voltage_depend_loads.isChecked() else 'False'
            self.config['pf']['consider_line_temperature'] = 'True' if pf.consider_line_temperature.isChecked() else 'False'
            self.config['pf']['distributed_slack'] = 'True' if pf.distributed_slack.isChecked() else 'False'
            self.config['pf']['tdpf'] = 'True' if pf.tdpf.isChecked() else 'False'
            if pf.tdpf_delay_s_check.isChecked():
                self.config['pf']['tdpf_delay_s'] = str(pf.tdpf_delay_s.value())
            else:
                self.config['pf']['tdpf_delay_s'] = 'None'
            self.config['pf']['tdpf_update_r_theta'] = 'True' if pf.tdpf_update_r_theta.isChecked() else 'False'
            
            # Bus page---------------------------------------------------------------
            self.config['bus']['vn_kv'] = str(bus.vn_kv.value())
            self.config['bus']['min_vm_pu'] = str(bus.min_vm_pu.value())
            self.config['bus']['max_vm_pu'] = str(bus.max_vm_pu.value())
            
            # AC line page-----------------------------------------------------------
            self.config['line']['length_km'] = str(line.length_km.value())
            self.config['line']['parallel'] = str(line.parallel.value())
            self.config['line']['df'] = str(line.df.value())
            self.config['line']['r_ohm_per_km'] = str(line.r_ohm_per_km.value())
            self.config['line']['x_ohm_per_km'] = str(line.x_ohm_per_km.value())
            self.config['line']['c_nf_per_km'] = str(line.c_nf_per_km.value())
            self.config['line']['g_us_per_km'] = str(line.g_us_per_km.value())
            self.config['line']['max_i_ka'] = str(line.max_i_ka.value())
            self.config['line']['r0_ohm_per_km'] = str(line.r0_ohm_per_km.value())
            self.config['line']['x0_ohm_per_km'] = str(line.x0_ohm_per_km.value())
            self.config['line']['c0_nf_per_km'] = str(line.c0_nf_per_km.value())
            self.config['line']['g0_us_per_km'] = str(line.g0_us_per_km.value())
            self.config['line']['max_loading_percent'] = str(line.max_loading_percent.value())
            self.config['line']['alpha'] = str(line.alpha.value())
            self.config['line']['temperature_degree_celsius'] = str(line.temperature_degree_celsius.value())
            self.config['line']['endtemp_degree'] = str(line.endtemp_degree.value())
            
            # Standard AC line page--------------------------------------------------
            self.config['stdline']['length_km'] = str(stdline.length_km.value())
            std_line_index = stdline.std_type.currentIndex()
            self.config['stdline']['std_type'] = stds_line[std_line_index]
            self.config['stdline']['parallel'] = str(stdline.parallel.value())
            self.config['stdline']['df'] = str(stdline.df.value())
            self.config['stdline']['max_loading_percent'] = str(stdline.max_loading_percent.value())
            
            # DC line page-----------------------------------------------------------
            self.config['dcline']['p_mw'] = str(dcline.p_mw.value())
            self.config['dcline']['loss_percent'] = str(dcline.loss_percent.value())
            self.config['dcline']['loss_mw'] = str(dcline.loss_mw.value())
            self.config['dcline']['vm_from_pu'] = str(dcline.vm_from_pu.value())
            self.config['dcline']['vm_to_pu'] = str(dcline.vm_to_pu.value())
            self.config['dcline']['max_p_mw'] = str(dcline.max_p_mw.value())
            self.config['dcline']['min_q_from_mvar'] = str(dcline.min_q_from_mvar.value())
            self.config['dcline']['min_q_to_mvar'] = str(dcline.min_q_to_mvar.value())
            self.config['dcline']['max_q_from_mvar'] = str(dcline.max_q_from_mvar.value())
            self.config['dcline']['max_q_to_mvar'] = str(dcline.max_q_to_mvar.value())
            
            # Impedance page---------------------------------------------------------
            self.config['impedance']['rft_pu'] = str(impedance.rft_pu.value())
            self.config['impedance']['xft_pu'] = str(impedance.xft_pu.value())
            self.config['impedance']['sn_mva'] = str(impedance.sn_mva.value())
            self.config['impedance']['rtf_pu'] = str(impedance.rtf_pu.value())
            self.config['impedance']['xtf_pu'] = str(impedance.xtf_pu.value())
            self.config['impedance']['rft0_pu'] = str(impedance.rft0_pu.value())
            self.config['impedance']['xft0_pu'] = str(impedance.xft0_pu.value())
            self.config['impedance']['rtf0_pu'] = str(impedance.rtf0_pu.value())
            self.config['impedance']['xtf0_pu'] = str(impedance.xtf0_pu.value())
            
            # Two winding transformer page-------------------------------------------
            self.config['trafo']['sn_mva'] = str(trafo.sn_mva.value())
            self.config['trafo']['vn_hv_kv'] = str(trafo.vn_hv_kv.value())
            self.config['trafo']['vn_lv_kv'] = str(trafo.vn_lv_kv.value())
            self.config['trafo']['vkr_percent'] = str(trafo.vkr_percent.value())
            self.config['trafo']['vk_percent'] = str(trafo.vk_percent.value())
            self.config['trafo']['pfe_kw'] = str(trafo.pfe_kw.value())
            self.config['trafo']['i0_percent'] = str(trafo.i0_percent.value())
            self.config['trafo']['shift_degree'] = str(trafo.shift_degree.value())
            self.config['trafo']['tap_neutral'] = str(int(trafo.tap_neutral.value()))
            self.config['trafo']['tap_max'] = str(int(trafo.tap_max.value()))
            self.config['trafo']['tap_min'] = str(int(trafo.tap_min.value()))
            self.config['trafo']['tap_step_percent'] = str(trafo.tap_step_percent.value())
            self.config['trafo']['tap_step_degree'] = str(trafo.tap_step_degree.value())
            self.config['trafo']['tap_pos'] = str(int(trafo.tap_pos.value()))
            self.config['trafo']['max_loading_percent'] = str(trafo.max_loading_percent.value())
            self.config['trafo']['parallel'] = str(int(trafo.parallel.value()))
            self.config['trafo']['df'] = str(trafo.df.value())
            self.config['trafo']['vk0_percent'] = str(trafo.vk0_percent.value())
            self.config['trafo']['vkr0_percent'] = str(trafo.vkr0_percent.value())
            self.config['trafo']['mag0_percent'] = str(trafo.mag0_percent.value())
            self.config['trafo']['mag0_rx'] = str(trafo.mag0_rx.value())
            self.config['trafo']['si0_hv_partial'] = str(trafo.si0_hv_partial.value())
            self.config['trafo']['xn_ohm'] = str(trafo.xn_ohm.value())
            self.config['trafo']['tap_side'] = trafo_tap_side_options[trafo.tap_side.currentIndex()]
            self.config['trafo']['vector_group'] = trafo_vector_group_options[trafo.vector_group.currentIndex()]
            self.config['trafo']['tap_phase_shifter'] = 'True' if trafo.tap_phase_shifter.isChecked() else 'False'
            self.config['trafo']['oltc'] = 'True' if trafo.oltc.isChecked() else 'False'
            
            # Standard two winding transformer page----------------------------------
            self.config['stdtrafo']['std_type'] = stds_trafo[stdtrafo.std_type.currentIndex()]
            self.config['stdtrafo']['max_loading_percent'] = str(stdtrafo.max_loading_percent.value())
            self.config['stdtrafo']['parallel'] = str(int(stdtrafo.parallel.value()))
            self.config['stdtrafo']['df'] = str(stdtrafo.df.value())
            self.config['stdtrafo']['vk0_percent'] = str(stdtrafo.vk0_percent.value())
            self.config['stdtrafo']['vkr0_percent'] = str(stdtrafo.vkr0_percent.value())
            self.config['stdtrafo']['mag0_percent'] = str(stdtrafo.mag0_percent.value())
            self.config['stdtrafo']['mag0_rx'] = str(stdtrafo.mag0_rx.value())
            self.config['stdtrafo']['si0_hv_partial'] = str(stdtrafo.si0_hv_partial.value())
            self.config['stdtrafo']['xn_ohm'] = str(stdtrafo.xn_ohm.value())
            
            # Three winding transformer page-----------------------------------------
            self.config['trafo3w']['sn_hv_mva'] = str(trafo3w.sn_hv_mva.value())
            self.config['trafo3w']['sn_mv_mva'] = str(trafo3w.sn_mv_mva.value())
            self.config['trafo3w']['sn_lv_mva'] = str(trafo3w.sn_lv_mva.value())
            self.config['trafo3w']['vn_hv_kv'] = str(trafo3w.vn_hv_kv.value())
            self.config['trafo3w']['vn_mv_kv'] = str(trafo3w.vn_mv_kv.value())
            self.config['trafo3w']['vn_lv_kv'] = str(trafo3w.vn_lv_kv.value())
            self.config['trafo3w']['vkr_hv_percent'] = str(trafo3w.vkr_hv_percent.value())
            self.config['trafo3w']['vkr_mv_percent'] = str(trafo3w.vkr_mv_percent.value())
            self.config['trafo3w']['vkr_lv_percent'] = str(trafo3w.vkr_lv_percent.value())
            self.config['trafo3w']['vk_hv_percent'] = str(trafo3w.vk_hv_percent.value())
            self.config['trafo3w']['vk_mv_percent'] = str(trafo3w.vk_mv_percent.value())
            self.config['trafo3w']['vk_lv_percent'] = str(trafo3w.vk_lv_percent.value())
            self.config['trafo3w']['pfe_kw'] = str(trafo3w.pfe_kw.value())
            self.config['trafo3w']['i0_percent'] = str(trafo3w.i0_percent.value())
            self.config['trafo3w']['shift_mv_degree'] = str(trafo3w.shift_mv_degree.value())
            self.config['trafo3w']['shift_lv_degree'] = str(trafo3w.shift_lv_degree.value())
            self.config['trafo3w']['tap_neutral'] = str(int(trafo3w.tap_neutral.value()))
            self.config['trafo3w']['tap_max'] = str(int(trafo3w.tap_max.value()))
            self.config['trafo3w']['tap_min'] = str(int(trafo3w.tap_min.value()))
            self.config['trafo3w']['tap_step_percent'] = str(trafo3w.tap_step_percent.value())
            self.config['trafo3w']['tap_step_degree'] = str(trafo3w.tap_step_degree.value())
            self.config['trafo3w']['tap_pos'] = str(int(trafo3w.tap_pos.value()))
            self.config['trafo3w']['max_loading_percent'] = str(trafo3w.max_loading_percent.value())
            self.config['trafo3w']['vk0_hv_percent'] = str(trafo3w.vk0_hv_percent.value())
            self.config['trafo3w']['vk0_mv_percent'] = str(trafo3w.vk0_mv_percent.value())
            self.config['trafo3w']['vk0_lv_percent'] = str(trafo3w.vk0_lv_percent.value())
            self.config['trafo3w']['vkr0_hv_percent'] = str(trafo3w.vkr0_hv_percent.value())
            self.config['trafo3w']['vkr0_mv_percent'] = str(trafo3w.vkr0_mv_percent.value())
            self.config['trafo3w']['vkr0_lv_percent'] = str(trafo3w.vkr0_lv_percent.value())
            self.config['trafo3w']['tap_side'] = trafo3w_tap_side_options[trafo3w.tap_side.currentIndex()]
            self.config['trafo3w']['vector_group'] = trafo3w_vector_group_options[trafo3w.vector_group.currentIndex()]
            self.config['trafo3w']['tap_at_star_point'] = 'True' if trafo3w.tap_at_star_point.isChecked() else 'False'
            
            # Standard three winding transformer page--------------------------------
            self.config['stdtrafo3w']['std_type'] = stds_trafo3w[stdtrafo3w.std_type.currentIndex()]
            self.config['stdtrafo3w']['max_loading_percent'] = str(stdtrafo3w.max_loading_percent.value())
            self.config['stdtrafo3w']['tap_at_star_point'] = 'True' if stdtrafo3w.tap_at_star_point.isChecked() else 'False'
            
            # Generator (PV mode) page-----------------------------------------------
            self.config['gen']['p_mw'] = str(gen.p_mw.value())
            self.config['gen']['vm_pu'] = str(gen.vm_pu.value())
            self.config['gen']['sn_mva'] = str(gen.sn_mva.value())
            self.config['gen']['scaling'] = str(gen.scaling.value())
            self.config['gen']['slack_weight'] = str(gen.slack_weight.value())
            self.config['gen']['vn_kv'] = str(gen.vn_kv.value())
            self.config['gen']['xdss_pu'] = str(gen.xdss_pu.value())
            self.config['gen']['rdss_ohm'] = str(gen.rdss_ohm.value())
            self.config['gen']['cos_phi'] = str(gen.cos_phi.value())
            self.config['gen']['max_p_mw'] = str(gen.max_p_mw.value())
            self.config['gen']['min_p_mw'] = str(gen.min_p_mw.value())
            self.config['gen']['max_q_mvar'] = str(gen.max_q_mvar.value())
            self.config['gen']['min_q_mvar'] = str(gen.min_q_mvar.value())
            self.config['gen']['min_vm_pu'] = str(gen.min_vm_pu.value())
            self.config['gen']['max_vm_pu'] = str(gen.max_vm_pu.value())
            self.config['gen']['controllable'] = 'True' if gen.controllable.isChecked() else 'False'
            
            # Static generator page--------------------------------------------------
            self.config['sgen']['p_mw'] = str(sgen.p_mw.value())
            self.config['sgen']['q_mvar'] = str(sgen.q_mvar.value())
            self.config['sgen']['sn_mva'] = str(sgen.sn_mva.value())
            self.config['sgen']['scaling'] = str(sgen.scaling.value())
            self.config['sgen']['max_p_mw'] = str(sgen.max_p_mw.value())
            self.config['sgen']['min_p_mw'] = str(sgen.min_p_mw.value())
            self.config['sgen']['max_q_mvar'] = str(sgen.max_q_mvar.value())
            self.config['sgen']['min_q_mvar'] = str(sgen.min_q_mvar.value())
            self.config['sgen']['current_source'] = 'True' if sgen.current_source.isChecked() else 'False'
            self.config['sgen']['controllable'] = 'True' if sgen.controllable.isChecked() else 'False'
            self.config['sgen']['type'] = sgen_type_options[sgen.type.currentIndex()]
            self.config['sgen']['generator_type'] = sgen_generator_type_options[sgen.generator_type.currentIndex()]
            self.config['sgen']['k'] = str(sgen.k.value()) if sgen.k_check.isChecked() else 'NaN'
            self.config['sgen']['rx'] = str(sgen.rx.value()) if sgen.rx_check.isChecked() else 'NaN'
            self.config['sgen']['lrc_pu'] = str(sgen.lrc_pu.value()) if sgen.lrc_pu_check.isChecked() else 'NaN'
            self.config['sgen']['max_ik_ka'] = str(sgen.max_ik_ka.value()) if sgen.max_ik_ka_check.isChecked() else 'NaN'
            self.config['sgen']['kappa'] = str(sgen.kappa.value()) if sgen.kappa_check.isChecked() else 'NaN'
            
            # Asymmetric static generator page---------------------------------------
            self.config['asymmetric_sgen']['p_a_mw'] = str(asgen.p_a_mw.value())
            self.config['asymmetric_sgen']['q_a_mvar'] = str(asgen.q_a_mvar.value())
            self.config['asymmetric_sgen']['p_b_mw'] = str(asgen.p_b_mw.value())
            self.config['asymmetric_sgen']['q_b_mvar'] = str(asgen.q_b_mvar.value())
            self.config['asymmetric_sgen']['p_c_mw'] = str(asgen.p_c_mw.value())
            self.config['asymmetric_sgen']['q_c_mvar'] = str(asgen.q_c_mvar.value())
            self.config['asymmetric_sgen']['sn_mva'] = str(asgen.sn_mva.value())
            self.config['asymmetric_sgen']['scaling'] = str(asgen.scaling.value())
            self.config['asymmetric_sgen']['type'] = asgen_type_options[asgen.type.currentIndex()]
            
            # External grid page-----------------------------------------------------
            self.config['ext_grid']['vm_pu'] = str(ext_grid.vm_pu.value())
            self.config['ext_grid']['va_degree'] = str(ext_grid.va_degree.value())
            self.config['ext_grid']['slack_weight'] = str(ext_grid.slack_weight.value())
            self.config['ext_grid']['max_p_mw'] = str(ext_grid.max_p_mw.value())
            self.config['ext_grid']['min_p_mw'] = str(ext_grid.min_p_mw.value())
            self.config['ext_grid']['max_q_mvar'] = str(ext_grid.max_q_mvar.value())
            self.config['ext_grid']['min_q_mvar'] = str(ext_grid.min_q_mvar.value())
            self.config['ext_grid']['controllable'] = 'True' if ext_grid.controllable.isChecked() else 'False'
            self.config['ext_grid']['s_sc_max_mva'] = str(ext_grid.s_sc_max_mva.value()) if ext_grid.s_sc_max_mva_check.isChecked() else 'NaN'
            self.config['ext_grid']['s_sc_min_mva'] = str(ext_grid.s_sc_min_mva.value()) if ext_grid.s_sc_min_mva_check.isChecked() else 'NaN'
            self.config['ext_grid']['rx_max'] = str(ext_grid.rx_max.value()) if ext_grid.rx_max_check.isChecked() else 'NaN'
            self.config['ext_grid']['rx_min'] = str(ext_grid.rx_min.value()) if ext_grid.rx_min_check.isChecked() else 'NaN'
            self.config['ext_grid']['r0x0_max'] = str(ext_grid.r0x0_max.value()) if ext_grid.r0x0_max_check.isChecked() else 'NaN'
            self.config['ext_grid']['x0x_max'] = str(ext_grid.x0x_max.value()) if ext_grid.x0x_max_check.isChecked() else 'NaN'
            
            # Load page--------------------------------------------------------------
            self.config['load']['p_mw'] = str(load.p_mw.value())
            self.config['load']['q_mvar'] = str(load.q_mvar.value())
            self.config['load']['const_z_percent'] = str(load.const_z_percent.value())
            self.config['load']['const_i_percent'] = str(load.const_i_percent.value())
            self.config['load']['sn_mva'] = str(load.sn_mva.value())
            self.config['load']['scaling'] = str(load.scaling.value())
            self.config['load']['max_p_mw'] = str(load.max_p_mw.value())
            self.config['load']['min_p_mw'] = str(load.min_p_mw.value())
            self.config['load']['max_q_mvar'] = str(load.max_q_mvar.value())
            self.config['load']['min_q_mvar'] = str(load.min_q_mvar.value())
            self.config['load']['controllable'] = 'True' if load.controllable.isChecked() else 'False'
            self.config['load']['type'] = load_type_options[load.type.currentIndex()]
            
            # Asymmentric load page--------------------------------------------------
            self.config['asymmetric_load']['p_a_mw'] = str(aload.p_a_mw.value())
            self.config['asymmetric_load']['q_a_mvar'] = str(aload.q_a_mvar.value())
            self.config['asymmetric_load']['p_b_mw'] = str(aload.p_b_mw.value())
            self.config['asymmetric_load']['q_b_mvar'] = str(aload.q_b_mvar.value())
            self.config['asymmetric_load']['p_c_mw'] = str(aload.p_c_mw.value())
            self.config['asymmetric_load']['q_c_mvar'] = str(aload.q_c_mvar.value())
            self.config['asymmetric_load']['sn_mva'] = str(aload.sn_mva.value())
            self.config['asymmetric_load']['scaling'] = str(aload.scaling.value())
            self.config['asymmetric_load']['type'] = aload_type_options[aload.type.currentIndex()]
            
            # Shunt page-------------------------------------------------------------
            self.config['shunt']['p_mw'] = str(shunt.p_mw.value())
            self.config['shunt']['q_mvar'] = str(shunt.q_mvar.value())
            self.config['shunt']['step'] = str(int(shunt.step.value()))
            self.config['shunt']['max_step'] = str(int(shunt.max_step.value()))
            self.config['shunt']['vn_kv'] = str(shunt.vn_kv.value()) if shunt.vn_kv_check.isChecked() else 'None'
            
            # Motor page-------------------------------------------------------------
            self.config['motor']['pn_mech_mw'] = str(motor.pn_mech_mw.value())
            self.config['motor']['cos_phi'] = str(motor.cos_phi.value())
            self.config['motor']['efficiency_percent'] = str(motor.efficiency_percent.value())
            self.config['motor']['loading_percent'] = str(motor.loading_percent.value())
            self.config['motor']['scaling'] = str(motor.scaling.value())
            self.config['motor']['efficiency_n_percent'] = str(motor.efficiency_n_percent.value())
            self.config['motor']['cos_phi_n'] = str(motor.cos_phi_n.value()) if motor.cos_phi_n_check.isChecked() else 'NaN'
            self.config['motor']['lrc_pu'] = str(motor.lrc_pu.value()) if motor.lrc_pu_check.isChecked() else 'NaN'
            self.config['motor']['rx'] = str(motor.rx.value()) if motor.rx_check.isChecked() else 'NaN'
            self.config['motor']['vn_kv'] = str(motor.vn_kv.value()) if motor.vn_kv_check.isChecked() else 'NaN'
            
            # Ward page--------------------------------------------------------------
            self.config['ward']['ps_mw'] = str(ward.ps_mw.value())
            self.config['ward']['qs_mvar'] = str(ward.qs_mvar.value())
            self.config['ward']['pz_mw'] = str(ward.pz_mw.value())
            self.config['ward']['qz_mvar'] = str(ward.qz_mvar.value())
            
            # Extended ward page-----------------------------------------------------
            self.config['xward']['ps_mw'] = str(xward.ps_mw.value())
            self.config['xward']['qs_mvar'] = str(xward.qs_mvar.value())
            self.config['xward']['pz_mw'] = str(xward.pz_mw.value())
            self.config['xward']['qz_mvar'] = str(xward.qz_mvar.value())
            self.config['xward']['r_ohm'] = str(xward.r_ohm.value())
            self.config['xward']['x_ohm'] = str(xward.x_ohm.value())
            self.config['xward']['vm_pu'] = str(xward.vm_pu.value())
            self.config['xward']['slack_weight'] = str(xward.slack_weight.value())
            
            # Storage page-----------------------------------------------------------
            self.config['storage']['p_mw'] = str(storage.p_mw.value())
            self.config['storage']['q_mvar'] = str(storage.q_mvar.value())
            self.config['storage']['sn_mva'] = str(storage.sn_mva.value())
            self.config['storage']['scaling'] = str(storage.scaling.value())
            self.config['storage']['max_e_mwh'] = str(storage.max_e_mwh.value())
            self.config['storage']['min_e_mwh'] = str(storage.min_e_mwh.value())
            self.config['storage']['soc_percent'] = str(storage.soc_percent.value())
            self.config['storage']['max_p_mw'] = str(storage.max_p_mw.value())
            self.config['storage']['min_p_mw'] = str(storage.min_p_mw.value())
            self.config['storage']['max_q_mvar'] = str(storage.max_q_mvar.value())
            self.config['storage']['min_q_mvar'] = str(storage.min_q_mvar.value())
            self.config['storage']['controllable'] = 'True' if storage.controllable.isChecked() else 'False'
            self.config['storage']['type'] = storage.type.text()
            
            # Switch page------------------------------------------------------------
            self.config['switch']['closed'] = 'True' if switch.closed.isChecked() else 'False'
            self.config['switch']['type'] = switch_type_options[switch.type.currentIndex()]
            self.config['switch']['z_ohm'] = str(switch.z_ohm.value())
            self.config['switch']['in_ka'] = str(switch.in_ka.value()) if switch.in_ka_check.isChecked() else 'NaN'
            
            
            
        return self.config
    
    def build_list_views(self):
        """
        Build the list view panels.
        """
        # First ListView-----------------------------------------------------------
        list_view1_options = ['General', 'Network (defaults)', 'Balanced AC Power Flow (defaults)']
        model_view1 = QtGui.QStandardItemModel()
        self.dialog.listView_main.setModel(model_view1)
        for name in list_view1_options:
            item = QtGui.QStandardItem(name)  # row
            item.setSizeHint(QtCore.QSize(36, 36))  # row height
            model_view1.appendRow(item)
        first_item_index = model_view1.index(0, 0)
        
        self.dialog.listView_main.clicked.connect(self.change_page)
        
        # Second ListView-----------------------------------------------------------
        list_view2_options = ['Bus', 'AC line', 'Standard AC line', 'DC line',
                              'Impedance', 'Two winding transformer',
                              'Standard two winding transformer', 'Three winding transformer',
                              'Standard three winding transformer',
                              'Voltage controled generator', 'Static generator',
                              'Asymmetric static generator', 'External grid',
                              'Symmetric load', 'Asymmetric load', 'Shunt element',
                              'Motor', 'Ward equivalent', 'Extended ward equivalent',
                              'Storage', 'Switch']
        model_view2 = QtGui.QStandardItemModel()
        self.dialog.listView_components.setModel(model_view2)
        for name in list_view2_options:
            item = QtGui.QStandardItem(name)  # row
            item.setSizeHint(QtCore.QSize(36, 36))  # row height
            model_view2.appendRow(item)
        
        self.dialog.listView_components.clicked.connect(self.change_page_second_list)
        
        # Initial position-----------------------------------------------------------
        self.dialog.listView_components.clearSelection()
        self.dialog.listView_main.setCurrentIndex(first_item_index)
        self.dialog.stackedWidget.setCurrentIndex(0)
        
    def change_page(self, index):
        """
        Change the page in the QStackedWidget.
        
        * index: The index of the page
        """
        self.dialog.listView_components.clearSelection()
        page_number = index.row()
        self.dialog.stackedWidget.setCurrentIndex(page_number)
        
    def change_page_second_list(self, index):
        """
        Change the page in the QStackedWidget.
        
        * index: The index of the page
        """
        self.dialog.listView_main.clearSelection()
        page_number = index.row()
        self.dialog.stackedWidget.setCurrentIndex(page_number +
                    self.dialog.listView_main.model().rowCount())
        
    def change_default_path(self):
        """
        Opens the dialog for selecting a new default path.
        """
        default_path = self.config['general']['default_path']
        if os.path.exists(default_path):
            dir_path = default_path
        else:
            dir_path = str(Path.home())
        full_file_path = QtWidgets.QFileDialog.getExistingDirectory(self.dialog,
                                    caption='Select the default path',
                                    dir=dir_path)

        if full_file_path:
            self.dialog.default_path.setPlainText(full_file_path)

    def restore_defaults(self):
        """
        Restore the default settings.
        """
        box = QtWidgets.QMessageBox(parent=self.dialog)
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setWindowTitle('Restore the default settings')
        box.setText('Do you want to restore the default settings?' +
                    ' This will overwrite the current configuration.' )
        box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        buttonY = box.button(QtWidgets.QMessageBox.Yes)
        buttonN = box.button(QtWidgets.QMessageBox.No)
        box.setDefaultButton(buttonN)
        box.exec()
        button_response = box.clickedButton()

        if button_response==buttonY:
            root_directory, _ = os.path.split(directory)
            default_config_file_path = os.path.join(root_directory, 'config.ini')
            self.config = configparser.ConfigParser()
            self.config.read(default_config_file_path)
            self.dialog.reject()
            
            QtWidgets.QMessageBox.information(self.main_window,
                                              'Success!',
                                              'Default settings restored!')
