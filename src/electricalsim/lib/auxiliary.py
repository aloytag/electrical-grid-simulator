# -*- coding: utf-8 -*-

import os
import configparser
import re

from PySide6 import QtWidgets, QtGui
import qtawesome as qta
from pynput.keyboard import Key, Controller
from platformdirs import user_config_dir

from NodeGraphQt6.constants import PortEnum

directory = os.path.dirname(__file__)
root_dir, _ = os.path.split(directory)

icon_for_type = {'BusNode.BusNode': 'ph.git-commit',
                 'LineNode.LineNode': 'ph.line-segment',
                 'StdLineNode.StdLineNode': 'ph.line-segment',
                 'DCLineNode.DCLineNode': 'ph.line-segment',
                 'ImpedanceNode.ImpedanceNode': 'mdi6.alpha-z-box-outline',
                 'TrafoNode.TrafoNode': 'ph.intersect',
                 'StdTrafoNode.StdTrafoNode': 'ph.intersect',
                 'Trafo3wNode.Trafo3wNode': 'ph.intersect',
                 'StdTrafo3wNode.StdTrafo3wNode': 'ph.intersect',
                 'GenNode.GenNode': 'mdi6.alpha-g-circle-outline',
                 'SGenNode.SGenNode': 'mdi6.alpha-g-circle-outline',
                 'ASGenNode.ASGenNode': 'mdi6.alpha-g-circle-outline',
                 'ExtGridNode.ExtGridNode': 'mdi6.grid',
                 'LoadNode.LoadNode': 'mdi6.download-circle-outline',
                 'ALoadNode.ALoadNode': 'mdi6.download-circle-outline',
                 'ShuntNode.ShuntNode': 'mdi6.download-circle-outline',
                 'MotorNode.MotorNode': 'mdi6.download-circle-outline',
                 'WardNode.WardNode': 'mdi6.download-circle-outline',
                 'XWardNode.XWardNode': 'mdi6.download-circle-outline',
                 'StorageNode.StorageNode': 'mdi6.battery-medium',
                 'SwitchNode.SwitchNode': 'mdi6.electric-switch'}


def natsort(s):
    """
    Function key for natural sorting.

    s: List with strings.
    """
    return [int(t) if t.isdigit() else t.lower() for t in re.split('(\d+)', s)]


def natsort2(s):
    """
    Function key for natural sorting.

    s: List obtained as enumerate(list with strings).
    """
    return [int(t) if t.isdigit() else t.lower() for t in re.split('(\d+)', s[1])]


def show_WIP(window_parent):
    """
    Show a warning popup dialog which indicates work in progress,
    so that option is not available yet.
    """
    title = 'Work in progress'
    text_content = 'Sorry, this feature is not available yet.'
    QtWidgets.QMessageBox.warning(window_parent, title, text_content)


def simulate_ESC_key():
    """
    Simulate the press and release of ESC key.
    
    This is used for avoiding freezes due to a Qt error with
    open/save dialogs (workaround).
    """
    keyboard = Controller()
    keyboard.press(Key.esc)
    keyboard.release(Key.esc)
    

def simulate_H_key():
    """
    Simulate the press and release of H key.
    """
    keyboard = Controller()
    keyboard.press('h')
    keyboard.release('h')


def simulate_V_key():
    """
    Simulate the press and release of V key.
    """
    keyboard = Controller()
    keyboard.press('v')
    keyboard.release('v')


def egs_path():
    """
    Returns the EGS installation path (directory).
    """
    return root_dir


class QMainWindow2(QtWidgets.QMainWindow):
    """
    Same as default QMainWindow, but ask for permission before closing.
    """
    def __init__(self, main_window, **kwargs):
        super().__init__(**kwargs)
        self.main_window = main_window
        self.resize(1399, 790)
        self.setCentralWidget(self.main_window)
        
    def closeEvent(self, event):
        status_msg = self.main_window.statusbar.findChild(QtWidgets.QWidget, 'unsaved_message')
        if not status_msg.isVisible():
            event.accept()
            return
        
        event.ignore()
        
        box = QtWidgets.QMessageBox(parent=self.main_window)
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setWindowTitle('Exit the application')
        box.setText('Session is unsaved. All the data will be lost when closing the application. '+
                    'Do you want to continue anyway?')
        box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        buttonY = box.button(QtWidgets.QMessageBox.Yes)
        buttonN = box.button(QtWidgets.QMessageBox.No)
        box.setDefaultButton(buttonN)
        box.exec()
        button_response = box.clickedButton()

        if button_response==buttonY:
            event.accept()


class QVLine(QtWidgets.QFrame):
    """
    Vertical line for making a vertical separator.
    """
    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)


class NodeMovedCmd(QtGui.QUndoCommand):
    """
    Node moved command. (MODIFIED VERSION)

    Args:
        node (NodeGraphQt6.NodeObject): node.
        pos (tuple(float, float)): new node position.
        prev_pos (tuple(float, float)): previous node position.
        graph: ElectricalGraph intance.
    """

    def __init__(self, node, pos, prev_pos, graph):
        QtGui.QUndoCommand.__init__(self)
        self.node = node
        self.pos = pos
        self.prev_pos = prev_pos
        self.graph = graph
        if self.node.type_=='BusNode.BusNode':
            self.bus_index = self.node.get_property('bus_index')

    def undo(self):
        self.node.view.xy_pos = self.prev_pos
        self.node.model.pos = self.prev_pos
        if self.node.type_=='BusNode.BusNode':
            self.graph.net.bus_geodata.loc[self.bus_index, ['x', 'y']] = self.prev_pos

    def redo(self):
        if self.pos == self.prev_pos:
            return
        self.node.view.xy_pos = self.pos
        self.node.model.pos = self.pos
        if self.node.type_=='BusNode.BusNode':
            self.graph.net.bus_geodata.loc[self.bus_index, ['x', 'y']] = self.pos


class StatusMessageUnsaved(QtWidgets.QWidget):
    """
    Widget for the satusbar.
    Shows a message when the latest changes are unsaved.
    """
    def __init__(self):
        super().__init__()
        
        self.setObjectName('unsaved_message')
        
        layout = QtWidgets.QHBoxLayout()
        icon_widget = qta.IconWidget('mdi6.circle', color='red')
        txt = QtWidgets.QLabel('Unsaved session')
        
        layout.addWidget(icon_widget)
        layout.addWidget(txt)
        
        self.setLayout(layout)


class PropertyChangedCmd(QtGui.QUndoCommand):
    """
    MODIFIED VERSION.
    
    Node property changed command.

    Args:
        node (NodeGraphQt6.NodeObject): node.
        name (str): node property name.
        value (object): node property value.
        graph (ElectricalGraph): graph reference.
    """

    def __init__(self, node, name, value):
        QtGui.QUndoCommand.__init__(self)
        
        if name == 'name':
            self.setText('renamed "{}" to "{}"'.format(node.name(), value))
        else:
            self.setText('property "{}:{}"'.format(node.name(), name))
        self.node = node
        self.name = name
        self.old_val = node.get_property(name)
        self.new_val = value
        self.graph = self.node.graph

    def set_node_prop(self, name, value):
        """
        updates the node view and model.
        """
        # set model data.
        model = self.node.model
        model.set_property(name, value)

        # set view data.
        view = self.node.view

        # view widgets.
        if hasattr(view, 'widgets') and name in view.widgets.keys():
            # check if previous value is identical to current value,
            # prevent signals from causing a infinite loop.
            if view.widgets[name].get_value() != value:
                view.widgets[name].set_value(value)

        # view properties.
        if name in view.properties.keys():
            # remap "pos" to "xy_pos" node view has pre-existing pos method.
            if name == 'pos':
                name = 'xy_pos'
            setattr(view, name, value)

    def undo(self):
        if self.old_val != self.new_val:
            self.set_node_prop(self.name, self.old_val)

            # emit property changed signal.
            graph = self.node.graph
            graph.property_changed.emit(self.node, self.name, self.old_val)
            
            # In case of 'name' changed:
            if self.node.type_=='BusNode.BusNode' and self.name=='name':
                bus_index = self.node.get_property('bus_index')
                self.graph.net.bus.loc[bus_index, 'name'] = self.old_val
            elif self.node.type_=='LineNode.LineNode' and self.name=='name':
                line_row = self.graph.net.line[self.graph.net.line['name']==self.new_val]
                if not line_row.empty:
                    line_index = line_row.index[0]
                    self.graph.net.line.loc[line_index, 'name'] = self.old_val
            elif self.node.type_=='StdLineNode.StdLineNode' and self.name=='name':
                line_row = self.graph.net.line[self.graph.net.line['name']==self.new_val]
                if not line_row.empty:
                    line_index = line_row.index[0]
                    self.graph.net.line.loc[line_index, 'name'] = self.old_val
            elif self.node.type_=='DCLineNode.DCLineNode' and self.name=='name':
                line_row = self.graph.net.dcline[self.graph.net.dcline['name']==self.new_val]
                if not line_row.empty:
                    line_index = line_row.index[0]
                    self.graph.net.dcline.loc[line_index, 'name'] = self.old_val
            elif self.node.type_=='ImpedanceNode.ImpedanceNode' and self.name=='name':
                impedance_row = self.graph.net.impedance[self.graph.net.impedance['name']==self.new_val]
                if not impedance_row.empty:
                    impedance_index = impedance_row.index[0]
                    self.graph.net.impedance.loc[impedance_index, 'name'] = self.old_val
            elif self.node.type_=='TrafoNode.TrafoNode' and self.name=='name':
                transformer_row = self.graph.net.trafo[self.graph.net.trafo['name']==self.new_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo.loc[transformer_index, 'name'] = self.old_val
            elif self.node.type_=='StdTrafoNode.StdTrafoNode' and self.name=='name':
                transformer_row = self.graph.net.trafo[self.graph.net.trafo['name']==self.new_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo.loc[transformer_index, 'name'] = self.old_val
            elif self.node.type_=='Trafo3wNode.Trafo3wNode' and self.name=='name':
                transformer_row = self.graph.net.trafo3w[self.graph.net.trafo3w['name']==self.new_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo3w.loc[transformer_index, 'name'] = self.old_val
            elif self.node.type_=='StdTrafo3wNode.StdTrafo3wNode' and self.name=='name':
                transformer_row = self.graph.net.trafo3w[self.graph.net.trafo3w['name']==self.new_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo3w.loc[transformer_index, 'name'] = self.old_val
            elif self.node.type_=='GenNode.GenNode' and self.name=='name':
                gen_row = self.graph.net.gen[self.graph.net.gen['name']==self.new_val]
                if not gen_row.empty:
                    gen_index = gen_row.index[0]
                    self.graph.net.gen.loc[gen_index, 'name'] = self.old_val
            elif self.node.type_=='SGenNode.SGenNode' and self.name=='name':
                gen_row = self.graph.net.sgen[self.graph.net.sgen['name']==self.new_val]
                if not gen_row.empty:
                    gen_index = gen_row.index[0]
                    self.graph.net.sgen.loc[gen_index, 'name'] = self.old_val
            elif self.node.type_=='ASGenNode.ASGenNode' and self.name=='name':
                gen_row = self.graph.net.asymmetric_sgen[self.graph.net.asymmetric_sgen['name']==self.new_val]
                if not gen_row.empty:
                    gen_index = gen_row.index[0]
                    self.graph.net.asymmetric_sgen.loc[gen_index, 'name'] = self.old_val
            elif self.node.type_=='ExtGridNode.ExtGridNode' and self.name=='name':
                grid_row = self.graph.net.ext_grid[self.graph.net.ext_grid['name']==self.new_val]
                if not grid_row.empty:
                    grid_index = grid_row.index[0]
                    self.graph.net.ext_grid.loc[grid_index, 'name'] = self.old_val
            elif self.node.type_=='LoadNode.LoadNode' and self.name=='name':
                load_row = self.graph.net.load[self.graph.net.load['name']==self.new_val]
                if not load_row.empty:
                    load_index = load_row.index[0]
                    self.graph.net.load.loc[load_index, 'name'] = self.old_val
            elif self.node.type_=='ALoadNode.ALoadNode' and self.name=='name':
                load_row = self.graph.net.asymmetric_load[self.graph.net.asymmetric_load['name']==self.new_val]
                if not load_row.empty:
                    load_index = load_row.index[0]
                    self.graph.net.asymmetric_load.loc[load_index, 'name'] = self.old_val
            elif self.node.type_=='ShuntNode.ShuntNode' and self.name=='name':
                shunt_row = self.graph.net.shunt[self.graph.net.shunt['name']==self.new_val]
                if not shunt_row.empty:
                    shunt_index = shunt_row.index[0]
                    self.graph.net.shunt.loc[shunt_index, 'name'] = self.old_val
            elif self.node.type_=='MotorNode.MotorNode' and self.name=='name':
                motor_row = self.graph.net.motor[self.graph.net.motor['name']==self.new_val]
                if not motor_row.empty:
                    motor_index = motor_row.index[0]
                    self.graph.net.motor.loc[motor_index, 'name'] = self.old_val
            elif self.node.type_=='WardNode.WardNode' and self.name=='name':
                ward_row = self.graph.net.ward[self.graph.net.ward['name']==self.new_val]
                if not ward_row.empty:
                    ward_index = ward_row.index[0]
                    self.graph.net.ward.loc[ward_index, 'name'] = self.old_val
            elif self.node.type_=='XWardNode.XWardNode' and self.name=='name':
                ward_row = self.graph.net.xward[self.graph.net.xward['name']==self.new_val]
                if not ward_row.empty:
                    ward_index = ward_row.index[0]
                    self.graph.net.xward.loc[ward_index, 'name'] = self.old_val
            elif self.node.type_=='StorageNode.StorageNode' and self.name=='name':
                storage_row = self.graph.net.storage[self.graph.net.storage['name']==self.new_val]
                if not storage_row.empty:
                    storage_index = storage_row.index[0]
                    self.graph.net.storage.loc[storage_index, 'name'] = self.old_val
            elif self.node.type_=='SwitchNode.SwitchNode' and self.name=='name':
                switch_row = self.graph.net.switch[self.graph.net.switch['name']==self.new_val]
                if not switch_row.empty:
                    switch_index = switch_row.index[0]
                    self.graph.net.switch.loc[switch_index, 'name'] = self.old_val
                    
            self.disable_case()  # In case of 'disable' change.

    def redo(self):
        if self.old_val != self.new_val:
            self.set_node_prop(self.name, self.new_val)

            # emit property changed signal.
            graph = self.node.graph
            graph.property_changed.emit(self.node, self.name, self.new_val)
            
            # In case of 'name' changed:
            if self.node.type_=='BusNode.BusNode' and self.name=='name':
                bus_index = self.node.get_property('bus_index')
                self.graph.net.bus.loc[bus_index, 'name'] = self.new_val
            elif self.node.type_=='LineNode.LineNode' and self.name=='name':
                line_row = self.graph.net.line[self.graph.net.line['name']==self.old_val]
                if not line_row.empty:
                    line_index = line_row.index[0]
                    self.graph.net.line.loc[line_index, 'name'] = self.new_val
            elif self.node.type_=='StdLineNode.StdLineNode' and self.name=='name':
                line_row = self.graph.net.line[self.graph.net.line['name']==self.old_val]
                if not line_row.empty:
                    line_index = line_row.index[0]
                    self.graph.net.line.loc[line_index, 'name'] = self.new_val
            elif self.node.type_=='DCLineNode.DCLineNode' and self.name=='name':
                line_row = self.graph.net.dcline[self.graph.net.dcline['name']==self.old_val]
                if not line_row.empty:
                    line_index = line_row.index[0]
                    self.graph.net.dcline.loc[line_index, 'name'] = self.new_val
            elif self.node.type_=='ImpedanceNode.ImpedanceNode' and self.name=='name':
                impedance_row = self.graph.net.impedance[self.graph.net.impedance['name']==self.old_val]
                if not impedance_row.empty:
                    impedance_index = impedance_row.index[0]
                    self.graph.net.impedance.loc[impedance_index, 'name'] = self.new_val
            elif self.node.type_=='TrafoNode.TrafoNode' and self.name=='name':
                transformer_row = self.graph.net.trafo[self.graph.net.trafo['name']==self.old_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo.loc[transformer_index, 'name'] = self.new_val
            elif self.node.type_=='StdTrafoNode.StdTrafoNode' and self.name=='name':
                transformer_row = self.graph.net.trafo[self.graph.net.trafo['name']==self.old_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo.loc[transformer_index, 'name'] = self.new_val
            elif self.node.type_=='Trafo3wNode.Trafo3wNode' and self.name=='name':
                transformer_row = self.graph.net.trafo3w[self.graph.net.trafo3w['name']==self.old_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo3w.loc[transformer_index, 'name'] = self.new_val
            elif self.node.type_=='StdTrafo3wNode.StdTrafo3wNode' and self.name=='name':
                transformer_row = self.graph.net.trafo3w[self.graph.net.trafo3w['name']==self.old_val]
                if not transformer_row.empty:
                    transformer_index = transformer_row.index[0]
                    self.graph.net.trafo3w.loc[transformer_index, 'name'] = self.new_val
            elif self.node.type_=='GenNode.GenNode' and self.name=='name':
                gen_row = self.graph.net.gen[self.graph.net.gen['name']==self.old_val]
                if not gen_row.empty:
                    gen_index = gen_row.index[0]
                    self.graph.net.gen.loc[gen_index, 'name'] = self.new_val
            elif self.node.type_=='SGenNode.SGenNode' and self.name=='name':
                gen_row = self.graph.net.sgen[self.graph.net.sgen['name']==self.old_val]
                if not gen_row.empty:
                    gen_index = gen_row.index[0]
                    self.graph.net.sgen.loc[gen_index, 'name'] = self.new_val
            elif self.node.type_=='ASGenNode.ASGenNode' and self.name=='name':
                gen_row = self.graph.net.asymmetric_sgen[self.graph.net.asymmetric_sgen['name']==self.old_val]
                if not gen_row.empty:
                    gen_index = gen_row.index[0]
                    self.graph.net.asymmetric_sgen.loc[gen_index, 'name'] = self.new_val
            elif self.node.type_=='ExtGridNode.ExtGridNode' and self.name=='name':
                grid_row = self.graph.net.ext_grid[self.graph.net.ext_grid['name']==self.old_val]
                if not grid_row.empty:
                    grid_index = grid_row.index[0]
                    self.graph.net.ext_grid.loc[grid_index, 'name'] = self.new_val
            elif self.node.type_=='LoadNode.LoadNode' and self.name=='name':
                load_row = self.graph.net.load[self.graph.net.load['name']==self.old_val]
                if not load_row.empty:
                    load_index = load_row.index[0]
                    self.graph.net.load.loc[load_index, 'name'] = self.new_val
            elif self.node.type_=='ALoadNode.ALoadNode' and self.name=='name':
                load_row = self.graph.net.asymmetric_load[self.graph.net.asymmetric_load['name']==self.old_val]
                if not load_row.empty:
                    load_index = load_row.index[0]
                    self.graph.net.asymmetric_load.loc[load_index, 'name'] = self.new_val
            elif self.node.type_=='ShuntNode.ShuntNode' and self.name=='name':
                shunt_row = self.graph.net.shunt[self.graph.net.shunt['name']==self.old_val]
                if not shunt_row.empty:
                    shunt_index = shunt_row.index[0]
                    self.graph.net.shunt.loc[shunt_index, 'name'] = self.new_val
            elif self.node.type_=='MotorNode.MotorNode' and self.name=='name':
                motor_row = self.graph.net.motor[self.graph.net.motor['name']==self.old_val]
                if not motor_row.empty:
                    motor_index = motor_row.index[0]
                    self.graph.net.motor.loc[motor_index, 'name'] = self.new_val
            elif self.node.type_=='WardNode.WardNode' and self.name=='name':
                ward_row = self.graph.net.ward[self.graph.net.ward['name']==self.old_val]
                if not ward_row.empty:
                    ward_index = ward_row.index[0]
                    self.graph.net.ward.loc[ward_index, 'name'] = self.new_val
            elif self.node.type_=='XWardNode.XWardNode' and self.name=='name':
                ward_row = self.graph.net.xward[self.graph.net.xward['name']==self.old_val]
                if not ward_row.empty:
                    ward_index = ward_row.index[0]
                    self.graph.net.xward.loc[ward_index, 'name'] = self.new_val
            elif self.node.type_=='StorageNode.StorageNode' and self.name=='name':
                storage_row = self.graph.net.storage[self.graph.net.storage['name']==self.old_val]
                if not storage_row.empty:
                    storage_index = storage_row.index[0]
                    self.graph.net.storage.loc[storage_index, 'name'] = self.new_val
            elif self.node.type_=='SwitchNode.SwitchNode' and self.name=='name':
                switch_row = self.graph.net.switch[self.graph.net.switch['name']==self.old_val]
                if not switch_row.empty:
                    switch_index = switch_row.index[0]
                    self.graph.net.switch.loc[switch_index, 'name'] = self.new_val
            
            self.disable_case()  # In case of 'disable' change.
                    
    def disable_case(self):
        if self.node.type_=='BusNode.BusNode' and self.name=='disabled':
            bus_index = self.node.get_property('bus_index')
            self.graph.net.bus.loc[bus_index, 'in_service'] ^= True
        elif self.node.type_=='LineNode.LineNode' and self.name=='disabled':
            line_row = self.graph.net.line[self.graph.net.line['name']==self.node.name()]
            if not line_row.empty:
                line_index = line_row.index[0]
                self.graph.net.line.loc[line_index, 'in_service'] ^= True
        elif self.node.type_=='StdLineNode.StdLineNode' and self.name=='disabled':
            line_row = self.graph.net.line[self.graph.net.line['name']==self.node.name()]
            if not line_row.empty:
                line_index = line_row.index[0]
                self.graph.net.line.loc[line_index, 'in_service'] ^= True
        elif self.node.type_=='DCLineNode.DCLineNode' and self.name=='disabled':
            line_row = self.graph.net.dcline[self.graph.net.dcline['name']==self.node.name()]
            if not line_row.empty:
                line_index = line_row.index[0]
                self.graph.net.dcline.loc[line_index, 'in_service'] ^= True
        elif self.node.type_=='ImpedanceNode.ImpedanceNode' and self.name=='disabled':
            impedance_row = self.graph.net.impedance[self.graph.net.impedance['name']==self.node.name()]
            if not impedance_row.empty:
                impedance_index = impedance_row.index[0]
                self.graph.net.impedance.loc[impedance_index, 'in_service'] ^= True
        elif self.node.type_=='TrafoNode.TrafoNode' and self.name=='disabled':
            trafo_row = self.graph.net.trafo[self.graph.net.trafo['name']==self.node.name()]
            if not trafo_row.empty:
                transformer_index = trafo_row.index[0]
                self.graph.net.trafo.loc[transformer_index, 'in_service'] ^= True
        elif self.node.type_=='StdTrafoNode.StdTrafoNode' and self.name=='disabled':
            trafo_row = self.graph.net.trafo[self.graph.net.trafo['name']==self.node.name()]
            if not trafo_row.empty:
                transformer_index = trafo_row.index[0]
                self.graph.net.trafo.loc[transformer_index, 'in_service'] ^= True
        elif self.node.type_=='Trafo3wNode.Trafo3wNode' and self.name=='disabled':
            trafo_row = self.graph.net.trafo3w[self.graph.net.trafo3w['name']==self.node.name()]
            if not trafo_row.empty:
                transformer_index = trafo_row.index[0]
                self.graph.net.trafo3w.loc[transformer_index, 'in_service'] ^= True
        elif self.node.type_=='StdTrafo3wNode.StdTrafo3wNode' and self.name=='disabled':
            trafo_row = self.graph.net.trafo3w[self.graph.net.trafo3w['name']==self.node.name()]
            if not trafo_row.empty:
                transformer_index = trafo_row.index[0]
                self.graph.net.trafo3w.loc[transformer_index, 'in_service'] ^= True
        elif self.node.type_=='GenNode.GenNode' and self.name=='disabled':
            gen_row = self.graph.net.gen[self.graph.net.gen['name']==self.node.name()]
            if not gen_row.empty:
                gen_index = gen_row.index[0]
                self.graph.net.gen.loc[gen_index, 'in_service'] ^= True
        elif self.node.type_=='SGenNode.SGenNode' and self.name=='disabled':
            gen_row = self.graph.net.sgen[self.graph.net.sgen['name']==self.node.name()]
            if not gen_row.empty:
                gen_index = gen_row.index[0]
                self.graph.net.sgen.loc[gen_index, 'in_service'] ^= True
        elif self.node.type_=='ASGenNode.ASGenNode' and self.name=='disabled':
            gen_row = self.graph.net.asymmetric_sgen[self.graph.net.asymmetric_sgen['name']==self.node.name()]
            if not gen_row.empty:
                gen_index = gen_row.index[0]
                self.graph.net.asymmetric_sgen.loc[gen_index, 'in_service'] ^= True
        elif self.node.type_=='ExtGridNode.ExtGridNode' and self.name=='disabled':
            grid_row = self.graph.net.ext_grid[self.graph.net.ext_grid['name']==self.node.name()]
            if not grid_row.empty:
                grid_index = grid_row.index[0]
                self.graph.net.ext_grid.loc[grid_index, 'in_service'] ^= True
        elif self.node.type_=='LoadNode.LoadNode' and self.name=='disabled':
            load_row = self.graph.net.load[self.graph.net.load['name']==self.node.name()]
            if not load_row.empty:
                load_index = load_row.index[0]
                self.graph.net.load.loc[load_index, 'in_service'] ^= True
        elif self.node.type_=='ALoadNode.ALoadNode' and self.name=='disabled':
            load_row = self.graph.net.asymmetric_load[self.graph.net.asymmetric_load['name']==self.node.name()]
            if not load_row.empty:
                load_index = load_row.index[0]
                self.graph.net.asymmetric_load.loc[load_index, 'in_service'] ^= True
        elif self.node.type_=='ShuntNode.ShuntNode' and self.name=='disabled':
            shunt_row = self.graph.net.shunt[self.graph.net.shunt['name']==self.node.name()]
            if not shunt_row.empty:
                shunt_index = shunt_row.index[0]
                self.graph.net.shunt.loc[shunt_index, 'in_service'] ^= True
        elif self.node.type_=='MotorNode.MotorNode' and self.name=='disabled':
            motor_row = self.graph.net.motor[self.graph.net.motor['name']==self.node.name()]
            if not motor_row.empty:
                motor_index = motor_row.index[0]
                self.graph.net.motor.loc[motor_index, 'in_service'] ^= True
        elif self.node.type_=='WardNode.WardNode' and self.name=='disabled':
            ward_row = self.graph.net.ward[self.graph.net.ward['name']==self.node.name()]
            if not ward_row.empty:
                ward_index = ward_row.index[0]
                self.graph.net.ward.loc[ward_index, 'in_service'] ^= True
        elif self.node.type_=='XWardNode.XWardNode' and self.name=='disabled':
            ward_row = self.graph.net.xward[self.graph.net.xward['name']==self.node.name()]
            if not ward_row.empty:
                ward_index = ward_row.index[0]
                self.graph.net.xward.loc[ward_index, 'in_service'] ^= True
        elif self.node.type_=='StorageNode.StorageNode' and self.name=='disabled':
            storage_row = self.graph.net.storage[self.graph.net.storage['name']==self.node.name()]
            if not storage_row.empty:
                storage_index = storage_row.index[0]
                self.graph.net.storage.loc[storage_index, 'in_service'] ^= True


def return_config(app_root_dir):
    """
    Checks if the config file exists and, in that case, returns
    the configparser as a first output.
    If no config file or directory exists, this function creates one
    from a copy of the default config file. It does the same when
    the config file exists, but it doesn't have the proper sections
    and options.
    
    Rertuns the config file path as a second argument.
    
    * app_root_dir: Root directory of the applications
    
    Returns:
    
    - First output: the configparser
    - Second output: the config file path
    """
    config_dir = user_config_dir('electricalsim')
    config_file_path = os.path.join(config_dir, 'config.ini')
    config = configparser.ConfigParser()
    config_default = configparser.ConfigParser()
    config_default.read(os.path.join(app_root_dir, 'config.ini'))
    if not os.path.exists(config_file_path):
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        config = config_default
        with open(config_file_path, 'w') as f:
            config.write(f)
    else:
        config.read(config_file_path)
        for section in config_default.sections():
            if not config.has_section(section):
                config = config_default
                with open(config_file_path, 'w') as f:
                    config.write(f)
                break
            else:
                options_default = sorted(list(config_default[section].keys()))
                options = sorted(list(config[section].keys()))
                if options_default!=options:
                    config = config_default
                    with open(config_file_path, 'w') as f:
                        config.write(f)
                    break
                
    return config, config_file_path


def four_ports_on_buses(node):
    """
    Change port positions in a bus node.
    """
    current_width = node.get_property('width')
    current_height = node.get_property('height')

    con_outs = node.connected_output_nodes()
    output_ports = list(con_outs.keys())

    if output_ports[0].view.pos().x() != output_ports[1].view.pos().x():
        return
    output_port = output_ports[0]
    pos = output_port.view.pos()
    current_x = pos.x()
    current_y = pos.y()
    pos.setY(current_y + current_height/2)
    pos.setX(current_x - current_width/2)
    output_port.view.setPos(pos)

    output_port2 = output_ports[1]
    pos = output_port2.view.pos()
    current_y = pos.y()
    pos.setY(current_y - current_height/4 - PortEnum.SIZE.value/1.8/2)
    output_port2.view.setPos(pos)

    con_ins = node.connected_input_nodes()
    input_ports = list(con_ins.keys())

    input_port = input_ports[0]
    pos = input_port.view.pos()
    current_x = pos.x()
    current_y = pos.y()
    pos.setX(current_x + current_width/2)
    pos.setY(current_y - current_height/4 - current_height/3)
    input_port.view.setPos(pos)

    input_port2 = input_ports[1]
    pos = input_port2.view.pos()
    current_y = pos.y()
    pos.setY(current_y - current_height/4 - PortEnum.SIZE.value/1.8/2)
    input_port2.view.setPos(pos)
