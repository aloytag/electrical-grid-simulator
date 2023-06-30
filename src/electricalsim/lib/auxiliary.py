# -*- coding: utf-8 -*-

import os
import configparser

from Qt import QtWidgets
import qtawesome as qta
from pynput.keyboard import Key, Controller
from platformdirs import user_config_dir

directory = os.path.dirname(__file__)
root_dir, _ = os.path.split(directory)


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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def closeEvent(self, event):
        status_msg = self.statusbar.findChild(QtWidgets.QWidget, 'unsaved_message')
        if not status_msg.isVisible():
            event.accept()
            return
        
        event.ignore()
        
        box = QtWidgets.QMessageBox(parent=self)
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setWindowTitle('Exit the application')
        box.setText('Session is unsaved. All the data will be lost when closing the application. '+
                    'Do you want to continue anyway?')
        box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        buttonY = box.button(QtWidgets.QMessageBox.Yes)
        buttonN = box.button(QtWidgets.QMessageBox.No)
        box.setDefaultButton(buttonN)
        box.exec_()
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


class NodeMovedCmd(QtWidgets.QUndoCommand):
    """
    Node moved command. (MODIFIED VERSION)

    Args:
        node (NodeGraphQt.NodeObject): node.
        pos (tuple(float, float)): new node position.
        prev_pos (tuple(float, float)): previous node position.
        graph: ElectricalGraph intance.
    """

    def __init__(self, node, pos, prev_pos, graph):
        QtWidgets.QUndoCommand.__init__(self)
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


class PropertyChangedCmd(QtWidgets.QUndoCommand):
    """
    MODIFIED VERSION.
    
    Node property changed command.

    Args:
        node (NodeGraphQt.NodeObject): node.
        name (str): node property name.
        value (object): node property value.
        graph (ElectricalGraph): graph reference.
    """

    def __init__(self, node, name, value):
        QtWidgets.QUndoCommand.__init__(self)
        
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
    
    Rertuns the confif file path as a second argument.
    
    * app_root_dir: Root directory of the applications
    
    Returns:
    
    - First output: the configparser
    - Second aoutput: the config file path
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
