# -*- coding: utf-8 -*-

import os
from PySide6 import QtCore, QtGui, QtWidgets

import numpy as np

from NodeGraphQt6 import BaseNode
from NodeGraphQt6.widgets.node_widgets import NodeBaseWidget

from lib.auxiliary import PropertyChangedCmd, root_dir

icons_dir = os.path.join(root_dir, 'icons')


class ImageWrapper(NodeBaseWidget):
    """
    Wrapper that allows an image widget (label with pixmap) to be added in a node object.
    """
    def __init__(self, parent=None, widget_type=None):
        super(ImageWrapper, self).__init__(parent)

        # set the name for node property.
        self.set_name('image')

        # set the label above the widget.
        # self.set_label('image')

        # set the custom widget.
        if widget_type is None:
            widget_type = QtWidgets.QLabel()
        self.set_custom_widget(widget_type)
        
    def get_value(self):
        widget = self.get_custom_widget()
        return widget.styleSheet()
    
    # def set_value(self, label):
    #     widget = self.get_custom_widget()
    #     widget.setFixedSize(100, 100)
    #     widget.setStyleSheet(label.styleSheet())
        
    def set_value(self, style):
        widget = self.get_custom_widget()
        widget.setFixedSize(100, 100)
        widget.setStyleSheet(style)


class QSpinBoxWrapper(NodeBaseWidget):
    """
    Wrapper that allows a QSpinBox widget to be added in a node object.
    """

    def __init__(self, parent=None, widget_type=None):
        super(QSpinBoxWrapper, self).__init__(parent)

        # set the name for node property.
        self.set_name('tap_pos')

        # set the label above the widget.
        self.set_label('Tap')

        # set the custom widget.
        if widget_type is None:
            widget_type = QtWidgets.QSpinBox()
        self.set_custom_widget(widget_type)
        
    def get_value(self):
        widget = self.get_custom_widget()
        return widget.value()
    
    def set_value(self, value):
        widget = self.get_custom_widget()
        widget.setValue(value)


def draw_triangle_port(painter, rect, info):
    """
    Custom paint function for drawing a Triangle shaped port.

    Args:
        painter (QtGui.QPainter): painter object.
        rect (QtCore.QRectF): port rect used to describe parameters
                              needed to draw.
        info (dict): information describing the ports current state.
            {
                'port_type': 'in',
                'color': (0, 0, 0),
                'border_color': (255, 255, 255),
                'multi_connection': False,
                'connected': False,
                'hovered': False,
            }
    """
    painter.save()

    size = int(rect.height() / 2)
    triangle = QtGui.QPolygonF()
    triangle.append(QtCore.QPointF(-size, size))
    triangle.append(QtCore.QPointF(0.0, -size))
    triangle.append(QtCore.QPointF(size, size))

    transform = QtGui.QTransform()
    transform.translate(rect.center().x(), rect.center().y())
    port_poly = transform.map(triangle)

    # mouse over port color.
    if info['hovered']:
        color = QtGui.QColor(14, 45, 59)
        border_color = QtGui.QColor(136, 255, 35)
    # port connected color.
    elif info['connected']:
        color = QtGui.QColor(195, 60, 60)
        border_color = QtGui.QColor(200, 130, 70)
    # default port color
    else:
        color = QtGui.QColor(*info['color'])
        border_color = QtGui.QColor(*info['border_color'])

    pen = QtGui.QPen(border_color, 1.8)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)

    painter.setPen(pen)
    painter.setBrush(color)
    painter.drawPolygon(port_poly)

    painter.restore()


def draw_square_port(painter, rect, info):
    """
    Custom paint function for drawing a Square shaped port.

    Args:
        painter (QtGui.QPainter): painter object.
        rect (QtCore.QRectF): port rect used to describe parameters
                              needed to draw.
        info (dict): information describing the ports current state.
            {
                'port_type': 'in',
                'color': (0, 0, 0),
                'border_color': (255, 255, 255),
                'multi_connection': False,
                'connected': False,
                'hovered': False,
            }
    """
    painter.save()

    # mouse over port color.
    if info['hovered']:
        color = QtGui.QColor(14, 45, 59)
        border_color = QtGui.QColor(136, 255, 35, 255)
    # port connected color.
    elif info['connected']:
        color = QtGui.QColor(195, 60, 60)
        border_color = QtGui.QColor(200, 130, 70)
    # default port color
    else:
        color = QtGui.QColor(*info['color'])
        border_color = QtGui.QColor(*info['border_color'])

    pen = QtGui.QPen(border_color, 1.8)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)

    painter.setPen(pen)
    painter.setBrush(color)
    painter.drawRect(rect)

    painter.restore()


class BaseNode2(BaseNode):
    def __init__(self):
        super().__init__()
        
        extras = ('layout_vert',)
        for prop in extras:
            self.create_property(prop, False)
        
    def set_property(self, name, value, push_undo=True):
        """
        Set the value on the node custom property.

        Args:
            name (str): name of the property.
            value (object): property data (python built in types).
            push_undo (bool): register the command to the undo stack. (default: True)
        """

        # prevent signals from causing a infinite loop.
        if self.get_property(name) == value:
            return

        if self.graph and name == 'name':
            value = self.graph.get_unique_name(value)
            self.NODE_NAME = value

        if self.graph:
            if push_undo:
                undo_stack = self.graph.undo_stack()
                undo_stack.push(PropertyChangedCmd(self, name, value))
            else:
                PropertyChangedCmd(self, name, value).redo()
        else:
            if hasattr(self.view, name):
                setattr(self.view, name, value)
            self.model.set_property(name, value)
        
        self.update()
        
    def set_input(self, index, port, push_undo=True):
        """
        Creates a connection pipe to the targeted output :class:`Port`.

        Args:
            index (int): index of the port.
            port (NodeGraphQt6.Port): port object.
        """
        src_port = self.input(index)
        src_port.connect_to(port, push_undo)
        
    def set_output(self, index, port, push_undo=True):
        """
        Creates a connection pipe to the targeted input :class:`Port`.

        Args:
            index (int): index of the port.
            port (NodeGraphQt6.Port): port object.
        """
        src_port = self.output(index)
        src_port.connect_to(port, push_undo)
    
    def set_tooltip_default(self):
        """
        Set the default tooltip.
        """
        tooltip = f'<b>{self.name()}</b><br>{self.type_}'
        self.view.setToolTip(tooltip)
        
    def update_tooltip(self, net):
        """
        Update the tooltip, adding power flow results (with the last power
        flow calculation).
        
        net: pandapower network
        """
        tooltip = f'<b>{self.name()}</b><br>{self.type_}'  # default tooltip
        
        if self.type_=='BusNode.BusNode' and not net['res_bus'].empty:
            
            index = self.get_property('bus_index')
            df = net['res_bus']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'vm_pu: {0: .5f}'.format(df.at[index, 'vm_pu']) +
                           '<br>va_degree: {0: .2f}'.format(df.at[index, 'va_degree'])
                           )
                
        elif self.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode') and not net['res_line'].empty:
            
            index = self.get_property('line_index')
            df = net['res_line']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'loading_percent: {0: .2f}'.format(df.at[index, 'loading_percent']) + '<br>' +
                           '<br>p_from_mw: {0: .6f}'.format(df.at[index, 'p_from_mw']) +
                           '<br>p_to_mw: {0: .6f}'.format(df.at[index, 'p_to_mw']) + '<br>' +
                           '<br>q_from_mvar: {0: .6f}'.format(df.at[index, 'q_from_mvar']) +
                           '<br>q_to_mvar: {0: .6f}'.format(df.at[index, 'q_to_mvar'])
                           )
                
        elif self.type_=='ImpedanceNode.ImpedanceNode' and not net['res_impedance'].empty:
            
            index = self.get_property('impedance_index')
            df = net['res_impedance']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_from_mw: {0: .6f}'.format(df.at[index, 'p_from_mw']) +
                           '<br>p_to_mw: {0: .6f}'.format(df.at[index, 'p_to_mw']) + '<br>' +
                           '<br>q_from_mvar: {0: .6f}'.format(df.at[index, 'q_from_mvar']) +
                           '<br>q_to_mvar: {0: .6f}'.format(df.at[index, 'q_to_mvar'])
                           )
                
        elif self.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode') and not net['res_trafo'].empty:
            
            index = self.get_property('transformer_index')
            df = net['res_trafo']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'loading_percent: {0: .2f}'.format(df.at[index, 'loading_percent']) + '<br>' +
                           '<br>p_hv_mw: {0: .6f}'.format(df.at[index, 'p_hv_mw']) +
                           '<br>p_lv_mw: {0: .6f}'.format(df.at[index, 'p_lv_mw']) + '<br>' +
                           '<br>q_hv_mvar: {0: .6f}'.format(df.at[index, 'q_hv_mvar']) +
                           '<br>q_lv_mvar: {0: .6f}'.format(df.at[index, 'q_lv_mvar'])
                           )
                
        elif self.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode') and not net['res_trafo3w'].empty:
            
            index = self.get_property('transformer_index')
            df = net['res_trafo3w']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'loading_percent: {0: .2f}'.format(df.at[index, 'loading_percent']) + '<br>' +
                           '<br>p_hv_mw: {0: .6f}'.format(df.at[index, 'p_hv_mw']) +
                           '<br>p_mv_mw: {0: .6f}'.format(df.at[index, 'p_mv_mw']) +
                           '<br>p_lv_mw: {0: .6f}'.format(df.at[index, 'p_lv_mw']) + '<br>' +
                           '<br>q_hv_mvar: {0: .6f}'.format(df.at[index, 'q_hv_mvar']) +
                           '<br>q_mv_mvar: {0: .6f}'.format(df.at[index, 'q_mv_mvar']) +
                           '<br>q_lv_mvar: {0: .6f}'.format(df.at[index, 'q_lv_mvar'])
                           )
                
        elif self.type_=='ExtGridNode.ExtGridNode' and not net['res_ext_grid'].empty:
            
            index = self.get_property('grid_index')
            df = net['res_ext_grid']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
                
        elif self.type_=='GenNode.GenNode' and not net['res_gen'].empty:
            
            index = self.get_property('gen_index')
            df = net['res_gen']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
                
        elif self.type_=='SGenNode.SGenNode' and not net['res_sgen'].empty:
            
            index = self.get_property('gen_index')
            df = net['res_sgen']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
                
        elif self.type_=='MotorNode.MotorNode' and not net['res_motor'].empty:
            
            index = self.get_property('motor_index')
            df = net['res_motor']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
                
        elif self.type_=='ShuntNode.ShuntNode' and not net['res_shunt'].empty:
            
            index = self.get_property('shunt_index')
            df = net['res_shunt']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
                
        elif self.type_=='WardNode.WardNode' and not net['res_ward'].empty:
            
            index = self.get_property('ward_index')
            df = net['res_ward']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
                
        elif self.type_=='XWardNode.XWardNode' and not net['res_xward'].empty:
            
            index = self.get_property('ward_index')
            df = net['res_xward']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
                
        elif self.type_=='StorageNode.StorageNode' and not net['res_storage'].empty:
            
            index = self.get_property('storage_index')
            df = net['res_storage']
            if index is not None and index in df.index:
                tooltip = (tooltip + '<br><br>' +
                           'p_mw: {0: .6f}'.format(df.at[index, 'p_mw']) +
                           '<br>q_mvar: {0: .6f}'.format(df.at[index, 'q_mvar'])
                           )
        
        self.view.setToolTip(tooltip)

    def flip(self):
        """
        Flip the node (change input ports by output ports, and vice versa).
        
        THIS IS A VIRTUAL METHOD.
        """
        pass
    
    def add_image(self, image_name):
        """
        Add an image to the node.
        
        image_name: Image file name from de 'icons' folder.
        """
    
        self.image_widget = ImageWrapper(self.view)
        self.image_widget.set_name('image')
        # icon_path = os.path.join(icons_dir, image_name)
        # style = f"image: url('{icon_path}');"
        style = "image: url(:/" + image_name + ");"
        self.image_widget.set_value(style)
        self.add_custom_widget(self.image_widget, tab=None)
        model = self.model
        self.set_model(model)


# class BusNode(BaseNode2):
#     __identifier__ = 'BusNode'
#     NODE_NAME = 'BusNode'
    
#     def __init__(self):
#         super().__init__()
#         self.input_port = self.add_input(multi_input=True, display_name=False)
#         self.output_port = self.add_output(display_name=False)
#         # self.set_color(157, 157, 157)
#         self.set_color(117, 117, 117)
        
#         self.create_property('bus_index', None)
        
#     def node_switch_connected(self):
#         """
#         Returns a list of SwitchNode connected to the bus.
#         Returns an empty list if no switch is connected.
#         """
#         switches = []
#         inputs_nodes = self.connected_input_nodes()[self.input_port]
#         for node in inputs_nodes:
#             if node.type_=='SwitchNode.SwitchNode':
#                 switches.append(node)
#         outputs_nodes = self.connected_output_nodes()[self.output_port]
#         for node in outputs_nodes:
#             if node.type_=='SwitchNode.SwitchNode':
#                 switches.append(node)
#         return switches
    

class BusNode(BaseNode2):
    __identifier__ = 'BusNode'
    NODE_NAME = 'BusNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(multi_input=True, display_name=False)
        self.output_port = self.add_output(display_name=False)

        self.input_port2 = self.add_input(name='input2', multi_input=True, display_name=False)
        self.output_port2 = self.add_output(name='output2', display_name=False)

        self.set_color(117, 117, 117)
        
        self.create_property('bus_index', None)
        
    def node_switch_connected(self):
        """
        Returns a list of SwitchNode connected to the bus.
        Returns an empty list if no switch is connected.
        """
        switches = []
        in_dict = self.connected_input_nodes()
        inputs_nodes = in_dict[self.input_port] + in_dict[self.input_port2]
        for node in inputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        out_dict = self.connected_output_nodes()
        outputs_nodes = out_dict[self.output_port] + out_dict[self.output_port2]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        return switches

        
class LineNode(BaseNode2):
    __identifier__ = 'LineNode'
    NODE_NAME = 'LineNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='from')
        self.output_port = self.add_output(name='to', multi_output=False)
        self.set_color(81, 0, 255)
        
        self.electrical_properties = ('length_km', 'r_ohm_per_km', 'x_ohm_per_km', 'c_nf_per_km',
                                      'g_us_per_km', 'max_i_ka', 'r0_ohm_per_km',
                                      'parallel', 'df',
                                      'x0_ohm_per_km', 'c0_nf_per_km', 'g0_us_per_km',
                                      'max_loading_percent', 'alpha',
                                      'temperature_degree_celsius', 'endtemp_degree')
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('line_index', None)
            
    def connected_to_network(self):
        """
        Returns True if the line node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected = len(self.connected_output_nodes()[self.output_port])
        
        return inputs_connected * outputs_connected
    
    def node_switch_connected(self):
        """
        Returns a list of SwitchNode connected to the line.
        Returns an empty list if no switch is connected.
        """
        switches = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        return switches


class StdLineNode(BaseNode2):
    __identifier__ = 'StdLineNode'
    NODE_NAME = 'StdLineNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='from')
        self.output_port = self.add_output(name='to', multi_output=False)
        self.set_color(81, 0, 255)
        
        self.electrical_properties = ('length_km', 'std_type',
                                      'parallel', 'df',
                                      'max_loading_percent')
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('line_index', None)
            
    def connected_to_network(self):
        """
        Returns True if the line node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected = len(self.connected_output_nodes()[self.output_port])
        
        return inputs_connected * outputs_connected
    
    def node_switch_connected(self):
        """
        Returns a list of SwitchNode connected to the line.
        Returns an empty list if no switch is connected.
        """
        switches = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        return switches
    
    
class DCLineNode(BaseNode2):
    __identifier__ = 'DCLineNode'
    NODE_NAME = 'DCLineNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='from')
        self.output_port = self.add_output(name='to', multi_output=False)
        self.set_color(81, 0, 255)
        
        self.electrical_properties = ('p_mw', 'loss_percent', 'loss_mw',
                                      'vm_from_pu', 'vm_to_pu', 'max_p_mw',
                                      'min_q_from_mvar', 'min_q_to_mvar',
                                      'max_q_from_mvar', 'max_q_to_mvar')
        
        for name in self.electrical_properties:
            if name!='p_mw':
                self.create_property(name, None)
                
        self.create_property('line_index', None)
            
        # add custom widget to node with "node.view" as the parent.
        self.p_mw_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.p_mw_widget.set_name('p_mw')
        self.p_mw_widget.set_label('P (MW)')
        # self.p_mw_widget.set_custom_widget(QtWidgets.QDoubleSpinBox())
        # self.p_mw_widget.get_custom_widget().valueChanged.connect(self.update_p_mw)
        self.p_mw_widget.get_custom_widget().setDecimals(4)
        self.p_mw_widget.get_custom_widget().setMinimum(0.0001)
        self.p_mw_widget.get_custom_widget().setMaximum(5000.0)
        self.add_custom_widget(self.p_mw_widget, tab=None)  # Adds the 'p_mw' property.
        self.p_mw_widget.get_custom_widget().valueChanged.connect(self.update_p_mw)
        
    def update_p_mw(self, value):
        """
        Updates 'p_mw' property when changing the power transmission widget from the node.
        
        Updates the 'p_mw' parameter on the pandapower network too.
        """
        self.set_property('p_mw', value, push_undo=False)
        
        line_index = self.get_property('line_index')
        if line_index is not None and self.connected_to_network():
            self.graph.net.dcline.loc[line_index, 'p_mw'] = value
            
    def connected_to_network(self):
        """
        Returns True if the line node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected = len(self.connected_output_nodes()[self.output_port])
        
        return inputs_connected * outputs_connected
    
    
class ImpedanceNode(BaseNode2):
    __identifier__ = 'ImpedanceNode'
    NODE_NAME = 'ImpedanceNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='from')
        self.output_port = self.add_output(name='to', multi_output=False)
        self.set_color(0, 184, 184)
        
        self.electrical_properties = ('rft_pu', 'xft_pu', 'sn_mva', 'rtf_pu',
                                      'xtf_pu', 'rft0_pu', 'xft0_pu',
                                      'rtf0_pu', 'xtf0_pu')
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('impedance_index', None)
        self.add_image('impedance.svg')
            
    def connected_to_network(self):
        """
        Returns True if the impedance node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected = len(self.connected_output_nodes()[self.output_port])
        
        return inputs_connected * outputs_connected
    
    
class TrafoNode(BaseNode2):
    __identifier__ = 'TrafoNode'
    NODE_NAME = 'TrafoNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='hv', painter_func=draw_square_port)
        self.output_port = self.add_output(name='lv', multi_output=False)
        self.set_color(0, 140, 0)
        
        self.electrical_properties = ('sn_mva', 'vn_hv_kv', 'vn_lv_kv', 'vkr_percent',
                                      'vk_percent', 'pfe_kw', 'i0_percent', 'shift_degree',
                                      'tap_side', 'tap_neutral', 'tap_max', 'tap_min',
                                      'tap_step_percent', 'tap_step_degree', 'tap_pos',
                                      'tap_phase_shifter', 'vector_group',
                                      'max_loading_percent', 'parallel', 'df',
                                      'vk0_percent', 'vkr0_percent', 'mag0_percent',
                                      'mag0_rx', 'si0_hv_partial', 'oltc', 'xn_ohm')
        for name in self.electrical_properties:
            if name!='tap_pos':
                self.create_property(name, None)
                
        self.create_property('transformer_index', None)
        self.add_image('transformer.svg')
            
        # add custom widget to node with "node.view" as the parent.
        self.tap_pos_widget = QSpinBoxWrapper(self.view)
        self.tap_pos_widget.get_custom_widget().valueChanged.connect(self.update_tap_pos)
        self.add_custom_widget(self.tap_pos_widget, tab=None)  # Adds the 'tap_pos' property.
        
    def update_tap_pos(self, value):
        """
        Updates 'tap_pos' property when changing the tap position widget from the node.
        
        Updates the 'tap_pos' parameter on the pandapower network too.
        """
        # tap_max = self.get_property('tap_max')
        # if tap_max is not None:
        #     self.tap_pos_widget.get_custom_widget().setMaximum(tap_max)
        # tap_min = self.get_property('tap_min')
        # if tap_min is not None:
        #     self.tap_pos_widget.get_custom_widget().setMinimum(tap_min)

        self.set_property('tap_pos', value, push_undo=False)
        
        transformer_index = self.get_property('transformer_index')
        if transformer_index is not None and self.connected_to_network():
            self.graph.net.trafo.loc[transformer_index, 'tap_pos'] = int(value)
            
    def connected_to_network(self):
        """
        Returns True if the transformer node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected = len(self.connected_output_nodes()[self.output_port])
        
        return inputs_connected * outputs_connected
    
    def node_switch_connected(self):
        """
        Returns a list of SwitchNode connected to the trafo.
        Returns an empty list if no switch is connected.
        """
        switches = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        return switches
    

class StdTrafoNode(BaseNode2):
    __identifier__ = 'StdTrafoNode'
    NODE_NAME = 'StdTrafoNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='hv', painter_func=draw_square_port)
        self.output_port = self.add_output(name='lv', multi_output=False)
        self.set_color(0, 140, 0)
        
        self.electrical_properties = ('std_type', 'tap_pos',
                                      'max_loading_percent', 'parallel', 'df',
                                      'vk0_percent', 'vkr0_percent', 'mag0_percent',
                                      'mag0_rx', 'si0_hv_partial', 'xn_ohm',
                                      'tap_min', 'tap_max')
        for name in self.electrical_properties:
            if name!='tap_pos':
                self.create_property(name, None)
                
        self.create_property('transformer_index', None)
        self.add_image('transformer.svg')
            
        # add custom widget to node with "node.view" as the parent.
        self.tap_pos_widget = QSpinBoxWrapper(self.view)
        self.tap_pos_widget.get_custom_widget().valueChanged.connect(self.update_tap_pos)
        self.add_custom_widget(self.tap_pos_widget, tab=None)  # Adds the 'tap_pos' property.
        
    def update_tap_pos(self, value):
        """
        Updates 'tap_pos' property when changing the tap position widget from the node.
        
        Updates the 'tap_pos' parameter on the pandapower network too.
        """
        self.set_property('tap_pos', value, push_undo=False)
        
        transformer_index = self.get_property('transformer_index')
        if transformer_index is not None and self.connected_to_network():
            self.graph.net.trafo.loc[transformer_index, 'tap_pos'] = int(value)
            
    def connected_to_network(self):
        """
        Returns True if the transformer node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected = len(self.connected_output_nodes()[self.output_port])
        
        return inputs_connected * outputs_connected
    
    def node_switch_connected(self):
        """
        Returns a list of SwitchNode connected to the trafo.
        Returns an empty list if no switch is connected.
        """
        switches = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        return switches


class Trafo3wNode(BaseNode2):
    __identifier__ = 'Trafo3wNode'
    NODE_NAME = 'Trafo3wNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='hv', painter_func=draw_square_port)
        self.output_port1 = self.add_output(name='mv', multi_output=False,
                                            painter_func=draw_triangle_port)
        self.output_port2 = self.add_output(name='lv', multi_output=False)
        self.set_color(0, 140, 0)
        
        self.electrical_properties = ('sn_hv_mva', 'sn_mv_mva', 'sn_lv_mva', 'vn_hv_kv',
                                      'vn_mv_kv', 'vn_lv_kv', 'vkr_hv_percent',
                                      'vkr_mv_percent', 'vkr_lv_percent', 'vk_hv_percent',
                                      'vk_mv_percent', 'vk_lv_percent', 'pfe_kw',
                                      'i0_percent', 'shift_mv_degree', 'shift_lv_degree',
                                      'tap_side', 'tap_neutral', 'tap_max', 'tap_min',
                                      'tap_step_percent', 'tap_step_degree', 'tap_pos',
                                      'tap_at_star_point', 'vector_group',
                                      'max_loading_percent', 'vk0_hv_percent',
                                      'vk0_mv_percent', 'vk0_lv_percent', 'vkr0_hv_percent',
                                      'vkr0_mv_percent', 'vkr0_lv_percent')
        for name in self.electrical_properties:
            if name!='tap_pos':
                self.create_property(name, None)
                
        self.create_property('transformer_index', None)
        self.add_image('3w-transformer.svg')
            
        # add custom widget to node with "node.view" as the parent.
        self.tap_pos_widget = QSpinBoxWrapper(self.view)
        self.tap_pos_widget.get_custom_widget().valueChanged.connect(self.update_tap_pos)
        self.add_custom_widget(self.tap_pos_widget, tab=None)  # Adds the 'tap_pos' property.
        
    def update_tap_pos(self, value):
        """
        Updates 'tap_pos' property when changing the tap position widget from the node.
        
        Updates the 'tap_pos' parameter on the pandapower network too.
        """
        self.set_property('tap_pos', value, push_undo=False)
        
        transformer_index = self.get_property('transformer_index')
        if transformer_index is not None and self.connected_to_network():
            self.graph.net.trafo3w.loc[transformer_index, 'tap_pos'] = int(value)
            
    def connected_to_network(self):
        """
        Returns True if the transformer node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected1 = len(self.connected_output_nodes()[self.output_port1])
        outputs_connected2 = len(self.connected_output_nodes()[self.output_port2])
        
        return inputs_connected * outputs_connected1 * outputs_connected2
    
    def node_switch_connected(self):
        """
        Returns a list of SwitchNode connected to the trafo.
        Returns an empty list if no switch is connected.
        """
        switches = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port1]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port2]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        return switches
    

class StdTrafo3wNode(BaseNode2):
    __identifier__ = 'StdTrafo3wNode'
    NODE_NAME = 'StdTrafo3wNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='hv', painter_func=draw_square_port)
        self.output_port1 = self.add_output(name='mv', multi_output=False,
                                            painter_func=draw_triangle_port)
        self.output_port2 = self.add_output(name='lv', multi_output=False)
        self.set_color(0, 140, 0)
        
        self.electrical_properties = ('std_type', 'tap_pos',
                                      'max_loading_percent',
                                      'tap_at_star_point',
                                      'tap_min', 'tap_max')
        for name in self.electrical_properties:
            if name!='tap_pos':
                self.create_property(name, None)
                
        self.create_property('transformer_index', None)
        self.add_image('3w-transformer.svg')
            
        # add custom widget to node with "node.view" as the parent.
        self.tap_pos_widget = QSpinBoxWrapper(self.view)
        self.tap_pos_widget.get_custom_widget().valueChanged.connect(self.update_tap_pos)
        self.add_custom_widget(self.tap_pos_widget, tab=None)  # Adds the 'tap_pos' property.
        
    def update_tap_pos(self, value):
        """
        Updates 'tap_pos' property when changing the tap position widget from the node.
        
        Updates the 'tap_pos' parameter on the pandapower network too.
        """
        self.set_property('tap_pos', value, push_undo=False)
        
        transformer_index = self.get_property('transformer_index')
        if transformer_index is not None and self.connected_to_network():
            self.graph.net.trafo3w.loc[transformer_index, 'tap_pos'] = int(value)
            
    def connected_to_network(self):
        """
        Returns True if the transformer node is connected to the network (to buses).
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected1 = len(self.connected_output_nodes()[self.output_port1])
        outputs_connected2 = len(self.connected_output_nodes()[self.output_port2])
        
        return inputs_connected * outputs_connected1 * outputs_connected2
    
    def node_switch_connected(self):
        """
        Returns a list of SwitchNode connected to the trafo.
        Returns an empty list if no switch is connected.
        """
        switches = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port1]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port2]
        for node in outputs_nodes:
            if node.type_=='SwitchNode.SwitchNode':
                switches.append(node)
        return switches


class GenNode(BaseNode2):
    __identifier__ = 'GenNode'
    NODE_NAME = 'GenNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = None
        self.output_port = self.add_output(name='', multi_output=False)
        self.output_port.port_deletion_allowed = True
        self.set_port_deletion_allowed(True)
        self.set_color(150, 139, 74)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('p_mw', 'vm_pu', 'sn_mva', 'scaling',
                                      'slack_weight', 'vn_kv', 'xdss_pu',
                                      'rdss_ohm', 'cos_phi', 'controllable',
                                      'max_p_mw', 'min_p_mw', 'max_q_mvar',
                                      'min_q_mvar', 'min_vm_pu', 'max_vm_pu')
        for name in self.electrical_properties:
            if name not in ('p_mw', 'scaling', 'vm_pu'):
                self.create_property(name, None)
                
        self.create_property('gen_index', None)
        
        # self.image_widget = ImageWrapper(self.view)
        # pixmap = QtGui.QPixmap(os.path.join(icons_dir, 'generator.svg'))
        # pixmap = pixmap.scaledToWidth(100, QtCore.Qt.SmoothTransformation)
        # self.image_widget.set_value(pixmap)
        # self.add_custom_widget(self.image_widget, tab=None)
        # model = self.model
        # self.set_model(model)
        
        self.add_image('generator.svg')
                
        # add custom widget to node with "node.view" as the parent.
        self.p_mw_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.p_mw_widget.set_name('p_mw')
        self.p_mw_widget.set_label('Pg (MW)')
        
        self.p_mw_widget.get_custom_widget().valueChanged.connect(self.update_p_mw)
        self.p_mw_widget.get_custom_widget().setDecimals(5)
        # max_p = self.get_property('max_p_mw')
        # if max_p is not None:
        #     self.p_mw_widget.get_custom_widget().setMaximum(max_p)
        self.add_custom_widget(self.p_mw_widget, tab=None)  # Adds the 'p_mw' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.scaling_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.scaling_widget.set_name('scaling')
        self.scaling_widget.set_label('Scaling Pg')
        self.scaling_widget.get_custom_widget().valueChanged.connect(self.update_scaling)
        self.scaling_widget.get_custom_widget().setDecimals(3)
        self.scaling_widget.get_custom_widget().setMinimum(0.0)
        self.scaling_widget.get_custom_widget().setMaximum(2.0)
        self.scaling_widget.get_custom_widget().setSingleStep(0.1)
        self.add_custom_widget(self.scaling_widget, tab=None)  # Adds the 'scaling' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.vm_pu_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.vm_pu_widget.set_name('vm_pu')
        self.vm_pu_widget.set_label('Vm (p.u.)')
        self.vm_pu_widget.get_custom_widget().valueChanged.connect(self.update_vm_pu)
        self.vm_pu_widget.get_custom_widget().setDecimals(4)
        # self.vm_pu_widget.get_custom_widget().setMinimum(0.0001)
        # self.vm_pu_widget.get_custom_widget().setMaximum(5000.0)
        self.vm_pu_widget.get_custom_widget().setSingleStep(0.01)
        self.add_custom_widget(self.vm_pu_widget, tab=None)  # Adds the 'vm_pu' property.
        
    def update_p_mw(self, value):
        """
        Updates 'p_mw' property when changing the generated active power from the node widget.
        
        Updates the 'p_mw' parameter on the pandapower network too.
        """
        self.set_property('p_mw', value, push_undo=False)
        
        gen_index = self.get_property('gen_index')
        if gen_index is not None and self.connected_to_network():
            self.graph.net.gen.loc[gen_index, 'p_mw'] = value
            
    def update_scaling(self, value):
        """
        Updates 'scaling' property when changing the generated active power from the node widget.
        
        Updates the 'scaling' parameter on the pandapower network too.
        """
        self.set_property('scaling', value, push_undo=False)
        
        gen_index = self.get_property('gen_index')
        if gen_index is not None and self.connected_to_network():
            self.graph.net.gen.loc[gen_index, 'scaling'] = value
            
    def update_vm_pu(self, value):
        """
        Updates 'vm_pu' property when changing the generated active power from the node widget.
        
        Updates the 'vm_pu' parameter on the pandapower network too.
        """
        self.set_property('vm_pu', value, push_undo=False)
        
        gen_index = self.get_property('gen_index')
        if gen_index is not None and self.connected_to_network():
            self.graph.net.gen.loc[gen_index, 'vm_pu'] = value
    
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if the generator node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class SGenNode(BaseNode2):
    __identifier__ = 'SGenNode'
    NODE_NAME = 'SGenNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = None
        self.output_port = self.add_output(name='', multi_output=False)
        self.output_port.port_deletion_allowed = True
        self.set_port_deletion_allowed(True)
        self.set_color(150, 139, 74)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('p_mw', 'q_mvar', 'sn_mva', 'scaling',
                                      'type', 'k', 'rx', 'max_ik_ka', 'kappa',
                                      'generator_type', 'lrc_pu', 'controllable',
                                      'current_source', 'max_p_mw', 'min_p_mw',
                                      'max_q_mvar', 'min_q_mvar')
        
        for name in self.electrical_properties:
            if name not in ('p_mw', 'q_mvar', 'scaling'):
                self.create_property(name, None)
                
        self.create_property('gen_index', None)
        self.add_image('generator.svg')
                
        # add custom widget to node with "node.view" as the parent.
        self.p_mw_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.p_mw_widget.set_name('p_mw')
        self.p_mw_widget.set_label('Pg (MW)')
        self.p_mw_widget.get_custom_widget().valueChanged.connect(self.update_p_mw)
        self.p_mw_widget.get_custom_widget().setDecimals(5)
        # self.p_mw_widget.get_custom_widget().setMinimum(0.0001)
        # self.p_mw_widget.get_custom_widget().setMaximum(5000.0)
        self.p_mw_widget.get_custom_widget().setSingleStep(1.0)
        self.add_custom_widget(self.p_mw_widget, tab=None)  # Adds the 'p_mw' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.q_mvar_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.q_mvar_widget.set_name('q_mvar')
        self.q_mvar_widget.set_label('Qg (Mvar)')
        self.q_mvar_widget.get_custom_widget().valueChanged.connect(self.update_q_mvar)
        self.q_mvar_widget.get_custom_widget().setDecimals(5)
        # self.q_mvar_widget.get_custom_widget().setMinimum(0.0001)
        # self.q_mvar_widget.get_custom_widget().setMaximum(5000.0)
        self.q_mvar_widget.get_custom_widget().setSingleStep(1.0)
        self.add_custom_widget(self.q_mvar_widget, tab=None)  # Adds the 'q_mvar' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.scaling_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.scaling_widget.set_name('scaling')
        self.scaling_widget.set_label('Scaling')
        self.scaling_widget.get_custom_widget().valueChanged.connect(self.update_scaling)
        self.scaling_widget.get_custom_widget().setDecimals(3)
        self.scaling_widget.get_custom_widget().setMinimum(0.0)
        self.scaling_widget.get_custom_widget().setMaximum(2.0)
        self.scaling_widget.get_custom_widget().setSingleStep(0.1)
        self.add_custom_widget(self.scaling_widget, tab=None)  # Adds the 'scaling' property.
        
    def update_p_mw(self, value):
        """
        Updates 'p_mw' property when changing the generated active power from the node widget.
        
        Updates the 'p_mw' parameter on the pandapower network too.
        """
        self.set_property('p_mw', value, push_undo=False)
        
        gen_index = self.get_property('gen_index')
        if gen_index is not None and self.connected_to_network():
            self.graph.net.sgen.loc[gen_index, 'p_mw'] = np.round(value, 5)
            
    def update_q_mvar(self, value):
        """
        Updates 'q_mvar' property when changing the generated reactive power from the node widget.
        
        Updates the 'q_mvar' parameter on the pandapower network too.
        """
        self.set_property('q_mvar', value, push_undo=False)
        
        gen_index = self.get_property('gen_index')
        if gen_index is not None and self.connected_to_network():
            self.graph.net.sgen.loc[gen_index, 'q_mvar'] = np.round(value, 5)
            
    def update_scaling(self, value):
        """
        Updates 'scaling' property when changing the generated active and reactive power
        from the node widget.
        
        Updates the 'scaling' parameter on the pandapower network too.
        """
        self.set_property('scaling', value, push_undo=False)
        
        gen_index = self.get_property('gen_index')
        if gen_index is not None and self.connected_to_network():
            self.graph.net.sgen.loc[gen_index, 'scaling'] = np.round(value, 5)
            
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
    
    def connected_to_network(self):
        """
        Returns True if the generator node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class ASGenNode(BaseNode2):
    __identifier__ = 'ASGenNode'
    NODE_NAME = 'ASGenNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = None
        self.output_port = self.add_output(name='', multi_output=False)
        self.output_port.port_deletion_allowed = True
        self.set_port_deletion_allowed(True)
        self.set_color(150, 139, 74)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('p_a_mw', 'q_a_mvar', 'sn_mva', 'scaling',
                                      'type', 'p_b_mw', 'q_b_mvar',
                                      'p_c_mw', 'q_c_mvar')
        
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('gen_index', None)
        self.add_image('generator.svg')
    
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if the generator node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class ExtGridNode(BaseNode2):
    __identifier__ = 'ExtGridNode'
    NODE_NAME = 'ExtGridNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = None
        self.output_port = self.add_output(name='', multi_output=False)
        self.output_port.port_deletion_allowed = True
        self.set_port_deletion_allowed(True)
        self.set_color(170, 85, 255)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('vm_pu', 'va_degree', 's_sc_max_mva',
                                      's_sc_min_mva', 'slack_weight', 'rx_max',
                                      'rx_min', 'r0x0_max', 'x0x_max',
                                      'controllable', 'max_p_mw', 'min_p_mw',
                                      'max_q_mvar', 'min_q_mvar',)
        for name in self.electrical_properties:
            if name !='vm_pu':
                self.create_property(name, None)
                
        self.create_property('grid_index', None)
        self.add_image('ext_grid.svg')
        
        # add custom widget to node with "node.view" as the parent.
        self.vm_pu_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.vm_pu_widget.set_name('vm_pu')
        self.vm_pu_widget.set_label('Vm (p.u.)')
        self.vm_pu_widget.get_custom_widget().valueChanged.connect(self.update_vm_pu)
        self.vm_pu_widget.get_custom_widget().setDecimals(4)
        self.vm_pu_widget.get_custom_widget().setMinimum(0.0)
        self.vm_pu_widget.get_custom_widget().setMaximum(2.0)
        self.vm_pu_widget.get_custom_widget().setSingleStep(0.01)
        self.add_custom_widget(self.vm_pu_widget, tab=None)  # Adds the 'vm_pu' property.
            
    def update_vm_pu(self, value):
        """
        Updates 'vm_pu' property when changing the generated active power from the node widget.
        
        Updates the 'vm_pu' parameter on the pandapower network too.
        """
        self.set_property('vm_pu', value, push_undo=False)
        
        grid_index = self.get_property('grid_index')
        if grid_index is not None and self.connected_to_network():
            self.graph.net.ext_grid.loc[grid_index, 'vm_pu'] = value
    
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if the external grid node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class LoadNode(BaseNode2):
    __identifier__ = 'LoadNode'
    NODE_NAME = 'LoadNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.input_port.port_deletion_allowed = True
        self.output_port = None
        self.set_port_deletion_allowed(True)
        self.set_color(248, 93, 153)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('p_mw', 'q_mvar', 'const_z_percent',
                                      'const_i_percent', 'sn_mva', 'scaling',
                                      'type', 'controllable',
                                      'max_p_mw', 'min_p_mw',
                                      'max_q_mvar', 'min_q_mvar')
        
        for name in self.electrical_properties:
            if name not in ('p_mw', 'q_mvar', 'scaling'):
                self.create_property(name, None)
                
        self.create_property('load_index', None)
        # self.create_property('layout_vert', False)
        
        # self.image_widget = ImageWrapper(self.view)
        # pixmap = QtGui.QPixmap(os.path.join(icons_dir, 'demand.svg'))
        # # pixmap = pixmap.scaled(100, 80, QtCore.Qt.KeepAspectRatio)
        # pixmap = pixmap.scaledToWidth(50, QtCore.Qt.SmoothTransformation)
        # self.image_widget.set_value(pixmap)
        # self.add_custom_widget(self.image_widget, tab=None)
        # model = self.model
        # self.set_model(model)
        
        self.image_widget = ImageWrapper(self.view)
        self.image_widget.set_name('image')
        # icon_path = os.path.join(icons_dir, 'demand.svg')
        # style = f"image: url('{icon_path}')"
        style = "image: url(:/demand.svg);"
        self.image_widget.set_value(style)
        self.add_custom_widget(self.image_widget, tab=None)
        model = self.model
        self.set_model(model)
                
        # add custom widget to node with "node.view" as the parent.
        self.p_mw_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.p_mw_widget.set_name('p_mw')
        self.p_mw_widget.set_label('Pd (MW)')
        self.p_mw_widget.get_custom_widget().valueChanged.connect(self.update_p_mw)
        self.p_mw_widget.get_custom_widget().setDecimals(5)
        # self.p_mw_widget.get_custom_widget().setMinimum(0.0001)
        # self.p_mw_widget.get_custom_widget().setMaximum(5000.0)
        self.p_mw_widget.get_custom_widget().setSingleStep(1.0)
        self.add_custom_widget(self.p_mw_widget, tab=None)  # Adds the 'p_mw' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.q_mvar_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.q_mvar_widget.set_name('q_mvar')
        self.q_mvar_widget.set_label('Qd (Mvar)')
        self.q_mvar_widget.get_custom_widget().valueChanged.connect(self.update_q_mvar)
        self.q_mvar_widget.get_custom_widget().setDecimals(5)
        # self.q_mvar_widget.get_custom_widget().setMinimum(0.0001)
        # self.q_mvar_widget.get_custom_widget().setMaximum(5000.0)
        self.q_mvar_widget.get_custom_widget().setSingleStep(1.0)
        self.add_custom_widget(self.q_mvar_widget, tab=None)  # Adds the 'q_mvar' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.scaling_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.scaling_widget.set_name('scaling')
        self.scaling_widget.set_label('Scaling')
        self.scaling_widget.get_custom_widget().valueChanged.connect(self.update_scaling)
        self.scaling_widget.get_custom_widget().setDecimals(3)
        self.scaling_widget.get_custom_widget().setMinimum(0.0)
        self.scaling_widget.get_custom_widget().setMaximum(2.0)
        self.scaling_widget.get_custom_widget().setSingleStep(0.1)
        self.add_custom_widget(self.scaling_widget, tab=None)  # Adds the 'scaling' property.
        
    def update_p_mw(self, value):
        """
        Updates 'p_mw' property when changing the demanded active power from the node widget.
        
        Updates the 'p_mw' parameter on the pandapower network too.
        """
        self.set_property('p_mw', value, push_undo=False)
        
        load_index = self.get_property('load_index')
        if load_index is not None and self.connected_to_network():
            self.graph.net.load.loc[load_index, 'p_mw'] = np.round(value, 5)
            
    def update_q_mvar(self, value):
        """
        Updates 'q_mvar' property when changing the demanded reactive power from the node widget.
        
        Updates the 'q_mvar' parameter on the pandapower network too.
        """
        self.set_property('q_mvar', value, push_undo=False)
        
        load_index = self.get_property('load_index')
        if load_index is not None and self.connected_to_network():
            self.graph.net.load.loc[load_index, 'q_mvar'] = np.round(value, 5)
            
    def update_scaling(self, value):
        """
        Updates 'scaling' property when changing the demanded active and reactive power
        from the node widget.
        
        Updates the 'scaling' parameter on the pandapower network too.
        """
        self.set_property('scaling', value, push_undo=False)
        
        load_index = self.get_property('load_index')
        if load_index is not None and self.connected_to_network():
            self.graph.net.load.loc[load_index, 'scaling'] = np.round(value, 5)
    
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if the load node is connected to the network (to a bus).
        Returns False otherwise.
        """
        # if self.input_port is None:
        #     return len(self.connected_output_nodes()[self.output_ports()[0]])
        # elif self.output_port is None:
        #     return len(self.connected_input_nodes()[self.input_ports()[0]])
        
        # fliped = self.get_property('fliped')
        # if fliped:
        #     return len(self.connected_output_nodes()[self.output_ports()[0]])
        # elif not fliped:
        #     return len(self.connected_input_nodes()[self.input_ports()[0]])
        
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class ALoadNode(BaseNode2):
    __identifier__ = 'ALoadNode'
    NODE_NAME = 'ALoadNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.input_port.port_deletion_allowed = True
        self.output_port = None
        self.set_port_deletion_allowed(True)
        self.set_color(248, 93, 153)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('p_a_mw', 'q_a_mvar', 'sn_mva', 'scaling',
                                      'type', 'p_b_mw', 'q_b_mvar',
                                      'p_c_mw', 'q_c_mvar')
        
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('load_index', None)
        
        # self.image_widget = ImageWrapper(self.view)
        # pixmap = QtGui.QPixmap(os.path.join(icons_dir, 'demand.svg'))
        # # pixmap = pixmap.scaled(100, 80, QtCore.Qt.KeepAspectRatio)
        # pixmap = pixmap.scaledToWidth(50, QtCore.Qt.SmoothTransformation)
        # self.image_widget.set_value(pixmap)
        # self.add_custom_widget(self.image_widget, tab=None)
        # model = self.model
        # self.set_model(model)
        
        self.image_widget = ImageWrapper(self.view)
        self.image_widget.set_name('image')
        icon_path = os.path.join(icons_dir, 'demand.svg')
        style = f"image: url('{icon_path}')"
        self.image_widget.set_value(style)
        self.add_custom_widget(self.image_widget, tab=None)
        model = self.model
        self.set_model(model)
        
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if the asymmetric load node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class ShuntNode(BaseNode2):
    __identifier__ = 'ShuntNode'
    NODE_NAME = 'ShuntNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.input_port.port_deletion_allowed = True
        self.output_port = None
        self.set_port_deletion_allowed(True)
        self.set_color(248, 93, 153)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('p_mw', 'q_mvar', 'vn_kv',
                                      'step', 'max_step')
        
        for name in self.electrical_properties:
            if name not in ('p_mw', 'q_mvar', 'step'):
                self.create_property(name, None)
                
        self.create_property('shunt_index', None)
        self.add_image('shunt.svg')
                
        # add custom widget to node with "node.view" as the parent.
        self.p_mw_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.p_mw_widget.set_name('p_mw')
        self.p_mw_widget.set_label('Pd (MW)')
        self.p_mw_widget.get_custom_widget().valueChanged.connect(self.update_p_mw)
        self.p_mw_widget.get_custom_widget().setDecimals(5)
        # self.p_mw_widget.get_custom_widget().setMinimum(0.0001)
        # self.p_mw_widget.get_custom_widget().setMaximum(5000.0)
        self.p_mw_widget.get_custom_widget().setSingleStep(1.0)
        self.add_custom_widget(self.p_mw_widget, tab=None)  # Adds the 'p_mw' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.q_mvar_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.q_mvar_widget.set_name('q_mvar')
        self.q_mvar_widget.set_label('Qd (Mvar)')
        self.q_mvar_widget.get_custom_widget().valueChanged.connect(self.update_q_mvar)
        self.q_mvar_widget.get_custom_widget().setDecimals(5)
        # self.q_mvar_widget.get_custom_widget().setMinimum(0.0001)
        # self.q_mvar_widget.get_custom_widget().setMaximum(5000.0)
        self.q_mvar_widget.get_custom_widget().setSingleStep(1.0)
        self.add_custom_widget(self.q_mvar_widget, tab=None)  # Adds the 'q_mvar' property.
        
        # add custom widget to node with "node.view" as the parent.
        self.step_widget = QSpinBoxWrapper(self.view, widget_type=QtWidgets.QDoubleSpinBox())
        self.step_widget.set_name('step')
        self.step_widget.set_label('Step')
        # self.step_widget.get_custom_widget().valueChanged.connect(self.update_step)
        self.step_widget.get_custom_widget().setDecimals(0)
        self.step_widget.get_custom_widget().setMinimum(1)
        self.step_widget.get_custom_widget().setMaximum(10)
        self.step_widget.get_custom_widget().setSingleStep(1)
        self.add_custom_widget(self.step_widget, tab=None)  # Adds the 'step' property.
        
        self.step_widget.get_custom_widget().valueChanged.connect(self.update_step)
        
    def update_p_mw(self, value):
        """
        Updates 'p_mw' property when changing the demanded active power from the node widget.
        
        Updates the 'p_mw' parameter on the pandapower network too.
        """
        self.set_property('p_mw', value, push_undo=False)
        
        shunt_index = self.get_property('shunt_index')
        if shunt_index is not None and self.connected_to_network():
            self.graph.net.shunt.loc[shunt_index, 'p_mw'] = np.round(value, 5)
            
    def update_q_mvar(self, value):
        """
        Updates 'q_mvar' property when changing the demanded reactive power from the node widget.
        
        Updates the 'q_mvar' parameter on the pandapower network too.
        """
        self.set_property('q_mvar', value, push_undo=False)
        
        shunt_index = self.get_property('shunt_index')
        if shunt_index is not None and self.connected_to_network():
            self.graph.net.shunt.loc[shunt_index, 'q_mvar'] = np.round(value, 5)
            
    def update_step(self, value):
        """
        Updates 'step' property when changing the demanded active and reactive power
        from the node widget.
        
        Updates the 'step' parameter on the pandapower network too.
        """
        self.set_property('step', value, push_undo=False)
        
        shunt_index = self.get_property('shunt_index')
        if shunt_index is not None and self.connected_to_network():
            self.graph.net.shunt.loc[shunt_index, 'step'] = np.round(value, 5)
            
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
    
    def connected_to_network(self):
        """
        Returns True if the shunt elemente node is connected to the
        network (to a bus). Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class MotorNode(BaseNode2):
    __identifier__ = 'MotorNode'
    NODE_NAME = 'MotorNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.input_port.port_deletion_allowed = True
        self.output_port = None
        self.set_port_deletion_allowed(True)
        self.set_color(255, 170, 0)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('pn_mech_mw', 'cos_phi',
                                      'efficiency_percent',
                                      'loading_percent', 'scaling',
                                      'efficiency_n_percent',
                                      'cos_phi_n', 'lrc_pu',
                                      'rx', 'vn_kv')
        
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('motor_index', None)
        self.add_image('motor.svg')
    
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if motor node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections
    

class WardNode(BaseNode2):
    __identifier__ = 'WardNode'
    NODE_NAME = 'WardNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.input_port.port_deletion_allowed = True
        self.output_port = None
        self.set_port_deletion_allowed(True)
        self.set_color(175, 117, 0)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('ps_mw', 'qs_mvar',
                                      'pz_mw', 'qz_mvar')
        
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('ward_index', None)
        self.add_image('ward.svg')
        
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if ward node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class XWardNode(BaseNode2):
    __identifier__ = 'XWardNode'
    NODE_NAME = 'XWardNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.input_port.port_deletion_allowed = True
        self.output_port = None
        self.set_port_deletion_allowed(True)
        self.set_color(175, 117, 0)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('ps_mw', 'qs_mvar',
                                      'pz_mw', 'qz_mvar',
                                      'r_ohm', 'x_ohm',
                                      'vm_pu', 'slack_weight')
        
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('ward_index', None)
        self.add_image('xward.svg')
        
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if extended ward node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class StorageNode(BaseNode2):
    __identifier__ = 'StorageNode'
    NODE_NAME = 'StorageNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.input_port.port_deletion_allowed = True
        self.output_port = None
        self.set_port_deletion_allowed(True)
        self.set_color(220, 220, 0)
        
        fliped = self.get_property('fliped')
        if fliped is not None:
            self.flip()
        else:
            self.create_property('fliped', False)
        
        self.electrical_properties = ('p_mw', 'q_mvar',
                                      'sn_mva', 'scaling',
                                      'max_e_mwh', 'min_e_mwh',
                                      'soc_percent', 'controllable',
                                      'max_p_mw', 'min_p_mw',
                                      'max_q_mvar', 'min_q_mvar',
                                      'type')
        
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('storage_index', None)
        self.add_image('storage.svg')
        
    def flip(self):
        """
        Flip the node (change the input ports by an output port, or Vice versa).
        """
        try:
            output_port = self.output_ports()[0]
            output_port.clear_connections(push_undo=False)
            self.delete_output(0)
            self.output_port = None
            self.input_port = self.add_input(name='')
            self.input_port.port_deletion_allowed = True
            self.set_property('fliped', False, push_undo=False)
        except IndexError:
            input_port = self.input_ports()[0]
            input_port.clear_connections(push_undo=False)
            self.delete_input(0)
            self.input_port = None
            self.output_port = self.add_output(name='', multi_output=False)
            self.output_port.port_deletion_allowed = True
            self.set_property('fliped', True, push_undo=False)
            
    def connected_to_network(self):
        """
        Returns True if storage node is connected to the network (to a bus).
        Returns False otherwise.
        """
        try:
            connections = len(self.connected_output_nodes()[self.output_ports()[0]])
        except IndexError:
            connections = len(self.connected_input_nodes()[self.input_ports()[0]])
        return connections


class SwitchNode(BaseNode2):
    __identifier__ = 'SwitchNode'
    NODE_NAME = 'SwitchNode'
    
    def __init__(self):
        super().__init__()
        self.input_port = self.add_input(name='')
        self.output_port = self.add_output(name='', multi_output=False)
        # self.set_color(178, 199, 218)
        self.set_color(0, 0, 255)
        
        self.electrical_properties = ('type', 'z_ohm', 'in_ka')
        for name in self.electrical_properties:
            self.create_property(name, None)
            
        self.create_property('switch_index', None)
        self.add_image('switch_closed.svg')
        
        self.add_checkbox('closed', '', 'Closed', True)  # Adds 'closed' property
        widget_checkbox = self.get_widget('closed')
        widget_checkbox.value_changed.connect(self.update_closed)
        size = widget_checkbox.size()
        size.scale(150, 150, QtCore.Qt.KeepAspectRatio)
        widget_checkbox.resize(size)
        widget_checkbox.get_custom_widget().setStyleSheet("QCheckBox::indicator { width: 50px; height: 50px;}")
        # self.update()
        
    def update_closed(self, value):
        """
        Updates de 'closed' property in the pandapower network when the
        node check button is clicked.
        """
        index = self.get_property('switch_index')
        new_value = self.get_property('closed')
        if index in self.graph.net.switch.index:
            self.graph.net.switch.loc[index, 'closed'] = new_value
        if new_value:
            self.set_color(0, 0, 255)
            # icon_path = os.path.join(icons_dir, 'switch_closed.svg')
            style = "image: url(:/switch_closed.svg);"
        else:
            self.set_color(178, 199, 218)
            # icon_path = os.path.join(icons_dir, 'switch_opened.svg')
            style = "image: url(:/switch_opened.svg);"
            
        # style = f"image: url('{icon_path}')"
        self.image_widget.set_value(style)
            
    def connected_to_network(self):
        """
        Returns True if the switch node is connected to the network.
        Returns False otherwise.
        """
        inputs_connected = len(self.connected_input_nodes()[self.input_port])
        outputs_connected = len(self.connected_output_nodes()[self.output_port])
        
        return inputs_connected * outputs_connected
    
    def set_locked(self, value):
        """
        If True, locks the ports and related connections (pipes).
        Unlocks the ports if value is False.
        """
        self.input_port.set_locked(value, connected_ports=False, push_undo=False)
        self.output_port.set_locked(value, connected_ports=False, push_undo=False)
        
    def node_line_connected(self):
        """
        Returns a list of LineNode and StdLineNode connected to the switch.
        Returns an empty list if no line is connected.
        """
        lines = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode'):
                lines.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port]
        for node in outputs_nodes:
            if node.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode'):
                lines.append(node)
        return lines
    
    def node_trafo_connected(self):
        """
        Returns a list of TrafoNode and StdTrafoNode connected to the switch.
        Returns an empty list if no trafo (two-winding) is connected.
        """
        trafos = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode'):
                trafos.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port]
        for node in outputs_nodes:
            if node.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode'):
                trafos.append(node)
        return trafos
    
    def node_trafo3w_connected(self):
        """
        Returns a list of Trafo3wNode and StdTrafo3wNode connected to the switch.
        Returns an empty list if no trafo (three-winding) is connected.
        """
        trafos = []
        inputs_nodes = self.connected_input_nodes()[self.input_port]
        for node in inputs_nodes:
            if node.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode'):
                trafos.append(node)
        outputs_nodes = self.connected_output_nodes()[self.output_port]
        for node in outputs_nodes:
            if node.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode'):
                trafos.append(node)
        return trafos
