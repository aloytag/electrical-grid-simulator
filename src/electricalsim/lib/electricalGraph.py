# -*- coding: utf-8 -*-

import os
import warnings
from math import isnan, nan
import pickle

import numpy as np
from PySide6 import QtGui, QtWidgets, QtCore
import pandapower as pp
# from pandapower.toolbox import drop_from_groups
from pandapower.toolbox import drop_elements

from NodeGraphQt6.base.commands import PortConnectedCmd
from NodeGraphQt6 import NodeGraph, errors, BaseNode
from NodeGraphQt6.constants import PortTypeEnum, PipeLayoutEnum

from lib.main_components import (BusNode, LineNode, StdLineNode, DCLineNode,
                                 ImpedanceNode, TrafoNode, StdTrafoNode,
                                 Trafo3wNode, StdTrafo3wNode, GenNode,
                                 SGenNode, ASGenNode, ExtGridNode,
                                 LoadNode, ALoadNode, ShuntNode, MotorNode,
                                 WardNode, XWardNode, StorageNode,
                                 SwitchNode)
from lib.auxiliary import (NodeMovedCmd, StatusMessageUnsaved,
                           simulate_ESC_key, four_ports_on_buses)  # , show_WIP)
from ui.dialogs import (bus_dialog, choose_line_dialog, line_dialog,
                        stdline_dialog,
                        dcline_dialog, impedance_dialog,
                        choose_transformer_dialog, transformer_dialog,
                        stdtransformer_dialog,
                        transformer3w_dialog, stdtransformer3w_dialog,
                        choose_generator_dialog, gen_dialog,
                        sgen_dialog, asgen_dialog, ext_grid_dialog,
                        choose_load_dialog, load_dialog, aload_dialog,
                        shunt_dialog, motor_dialog, about_dialog,
                        ward_dialog, xward_dialog, storage_dialog,
                        choose_bus_switch_dialog, switch_dialog,
                        network_settings_dialog, Settings_Dialog,
                        connecting_buses_dialog, search_node_dialog)
from extensions.extension_classes import ExtensionWorker


warnings.simplefilter(action='ignore', category=FutureWarning)
directory = os.path.dirname(__file__)
root_directory, _ = os.path.split(directory)
icon_path = os.path.join(root_directory, 'icons', 'app_icon.png')

allowed_connections = (
    {'BusNode.BusNode', 'LineNode.LineNode'},
    {'BusNode.BusNode', 'StdLineNode.StdLineNode'},
    {'BusNode.BusNode', 'DCLineNode.DCLineNode'},
    {'BusNode.BusNode', 'ImpedanceNode.ImpedanceNode'},
    {'BusNode.BusNode', 'TrafoNode.TrafoNode'},
    {'BusNode.BusNode', 'StdTrafoNode.StdTrafoNode'},
    {'BusNode.BusNode', 'Trafo3wNode.Trafo3wNode'},
    {'BusNode.BusNode', 'StdTrafo3wNode.StdTrafo3wNode'},
    {'BusNode.BusNode', 'GenNode.GenNode'},
    {'BusNode.BusNode', 'SGenNode.SGenNode'},
    {'BusNode.BusNode', 'ASGenNode.ASGenNode'},
    {'BusNode.BusNode', 'ExtGridNode.ExtGridNode'},
    {'BusNode.BusNode', 'LoadNode.LoadNode'},
    {'BusNode.BusNode', 'ALoadNode.ALoadNode'},
    {'BusNode.BusNode', 'ShuntNode.ShuntNode'},
    {'BusNode.BusNode', 'MotorNode.MotorNode'},
    {'BusNode.BusNode', 'WardNode.WardNode'},
    {'BusNode.BusNode', 'XWardNode.XWardNode'},
    {'BusNode.BusNode', 'StorageNode.StorageNode'}
        )


class ElectricalGraph(NodeGraph):
    """
    A graph with nodes representing components of an electrical network.
    Includes a pandapower network as an attribute.

    * config: ConfigParser instance with all the settings
    * config_file_path: the path of the config file
    """

    def __init__(self, config, config_file_path, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.config_file_path = config_file_path
        self.set_acyclic(False)
        
        self._viewer.node_name_changed.connect(self._on_node_name_changed2)

        self.register_nodes([BusNode, LineNode, StdLineNode, DCLineNode,
                             ImpedanceNode, TrafoNode, StdTrafoNode,
                             Trafo3wNode, StdTrafo3wNode, GenNode,
                             SGenNode, ASGenNode, ExtGridNode,
                             LoadNode, ALoadNode, ShuntNode, MotorNode,
                             WardNode, XWardNode, StorageNode,
                             SwitchNode])

        settings = self.config['network']
        self.net = pp.create_empty_network(settings['name'],
                                           f_hz=float(settings['f_hz']),
                                           sn_mva=float(settings['sn_mva']))

        theme = self.config['general']['theme']
        if theme=='light':
            self.set_background_color(248, 249, 250)
        if config['general']['grid']=='True' and theme=='light':
            self.set_grid_mode(2)
            self.set_grid_color(236, 236, 236)
        elif config['general']['grid']=='True' and theme!='light':
            self.set_grid_mode(2)
        else:
            self.set_grid_mode(0)

        pipe_style = self.config['general']['pipe_style']
        if pipe_style=='curved':
            self.set_pipe_style(PipeLayoutEnum.CURVED.value)
        elif pipe_style=='straight':
            self.set_pipe_style(PipeLayoutEnum.STRAIGHT.value)
        elif pipe_style=='angle':
            self.set_pipe_style(PipeLayoutEnum.ANGLE.value)


        self.set_context_menu_from_file('./hotkeys/hotkeys.json')
        self.page_changed_on_toolbox = None

        self.node_double_clicked.connect(self.open_options_dialog)
        self._viewer.connection_changed.connect(self.connection_changed)
        self.port_disconnected.connect(self.disconnect_component)

        self.saved_file_path = None  # None if the session was never saved

        self.main_window = kwargs.get('main_window')  # QMainWindow2 reference to the main window
        self.extensions_dict = kwargs.get('extensions_dict', dict())

        # When something in the graph changed:
        self.property_changed.connect(self.session_change_warning)
        self.message_unsaved = StatusMessageUnsaved()
        self.main_window.statusbar.addWidget(self.message_unsaved)
        self.message_unsaved.hide()
        self.set_main_window_title()
        self._viewer.setViewportUpdateMode(QtWidgets.QGraphicsView.BoundingRectViewportUpdate)

    def set_main_window_title(self, file_name=None):
        """
        Change the main window title.

        Args:
            file_name: File name (for saved .egs files)

        Returns: None

        """
        if file_name is None:
            self.main_window.setWindowTitle('Electrical Grid Simulation - Unsaved file')
        else:
            self.main_window.setWindowTitle(f'Electrical Grid Simulation - {file_name}')

    def _on_connection_changed(self, disconnected, connected):
        """
        REPLACED ORIGINAL METHOD IR ORDER TO AVOID UNDO/REDO COMMANDS AFTER CONNECTING OR
        DISCONNECTING PORTS.

        called when a pipe connection has been changed in the viewer.

        Args:
            disconnected (list[list[widgets.port.PortItem]):
                pair list of port view items.
            connected (list[list[widgets.port.PortItem]]):
                pair list of port view items.
        """
        if not (disconnected or connected):
            return

        # label = 'connect node(s)' if connected else 'disconnect node(s)'
        ptypes = {PortTypeEnum.IN.value: 'inputs',
                  PortTypeEnum.OUT.value: 'outputs'}

        # self._undo_stack.beginMacro(label)
        for p1_view, p2_view in disconnected:
            node1 = self._model.nodes[p1_view.node.id]
            node2 = self._model.nodes[p2_view.node.id]
            port1 = getattr(node1, ptypes[p1_view.port_type])()[p1_view.name]
            port2 = getattr(node2, ptypes[p2_view.port_type])()[p2_view.name]
            port1.disconnect_from(port2, push_undo=False)
        for p1_view, p2_view in connected:
            node1 = self._model.nodes[p1_view.node.id]
            node2 = self._model.nodes[p2_view.node.id]
            port1 = getattr(node1, ptypes[p1_view.port_type])()[p1_view.name]
            port2 = getattr(node2, ptypes[p2_view.port_type])()[p2_view.name]
            port1.connect_to(port2, push_undo=False)
        # self._undo_stack.endMacro()

    def _on_connection_sliced(self, ports):
        """
        REPLACED ORIGINAL METHOD.

        slot when connection pipes have been sliced.

        Args:
            ports (list[list[widgets.port.PortItem]]):
                pair list of port connections (in port, out port)
        """
        if not ports:
            return
        ptypes = {PortTypeEnum.IN.value: 'inputs',
                  PortTypeEnum.OUT.value: 'outputs'}
        # self._undo_stack.beginMacro('slice connections')
        for p1_view, p2_view in ports:
            node1 = self._model.nodes[p1_view.node.id]
            node2 = self._model.nodes[p2_view.node.id]
            port1 = getattr(node1, ptypes[p1_view.port_type])()[p1_view.name]
            port2 = getattr(node2, ptypes[p2_view.port_type])()[p2_view.name]
            port1.disconnect_from(port2, push_undo=False)
        # self._undo_stack.endMacro()

        self.connection_changed(ports, [])

    def _on_nodes_moved(self, node_data):
        """
        MODIFIED VERSION IN ORDER TO UPDATE BUS GEODATA ON PANDAPOWER MODEL.

        called when selected nodes in the viewer has changed position.

        Args:
            node_data (dict): {<node_id>: <previous_pos>}
        """
        self._undo_stack.beginMacro('move nodes')
        for id, prev_pos in node_data.items():
            node = self._model.nodes[id]
            self._undo_stack.push(NodeMovedCmd(node, node.pos(), prev_pos, self))  # Adding 'self' as last argument
        self._undo_stack.endMacro()

        self.session_change_warning(tooltip_default=False)
        
    # def _on_nodes_moved(self, node_data):
    #     """
    #     called when selected nodes in the viewer has changed position.

    #     Args:
    #         node_data (dict): {<node_id>: <previous_pos>}
    #     """
    #     self._undo_stack.beginMacro('move nodes')
    #     for id, prev_pos in node_data.items():
    #         node = self._model.nodes[id]
    #         self._undo_stack.push(NodeMovedCmd(node, node.pos(), prev_pos))
    #     self._undo_stack.endMacro()

    def duplicate_nodes(self, nodes):
        """
        MODIFIED VERSION FROM NodeGraph CLASS WITHOUT UNDO

        Create duplicate copy from the list of nodes.

        Args:
            nodes (list[NodeGraphQt6.BaseNode]): list of nodes.
        Returns:
            list[NodeGraphQt6.BaseNode]: list of duplicated node instances.
        """
        if not nodes:
            return

        # self._undo_stack.beginMacro('duplicate nodes')

        self.clear_selection()
        serial = self._serialize(nodes)
        new_nodes = self._deserialize2(serial)
        offset = 50
        # for n_original, n in zip(nodes, new_nodes):
        #     x, y = n.pos()
        #     n.set_pos(x + offset, y + offset)
        #     n.set_property('selected', True)
            # if n_original.get_property('layout_vert') is True:
            #     n.set_layout_direction(1)
            #     self.set_vertical_layout_prop(n)
            #     n_original.set_layout_direction(1)
            # else:
            #     n.set_layout_direction(0)
            #     self.set_horizontal_layout_prop(n)
            #     n_original.set_layout_direction(0)

        # return new_nodes
    
        for n_old, n in zip(nodes, new_nodes):
            x, y = n.pos()
            n.set_pos(x + offset, y + offset)
            n.set_property('selected', True)
            if n_old.type_=='BusNode.BusNode':
                four_ports_on_buses(n_old)
                four_ports_on_buses(n)
        
        # self._undo_stack.endMacro()
        
        return new_nodes
    
    def _serialize(self, nodes):
        """
        MODIFIED VERSION FOR SOLVING LAYOUT BUGS.
        
        serialize nodes to a dict.
        (used internally by the node graph)

        Args:
            nodes (list[NodeGraphQt6.Nodes]): list of node instances.

        Returns:
            dict: serialized data.
        """
        serial_data = {'graph': {}, 'nodes': {}, 'connections': []}
        nodes_data = {}

        # serialize graph session.
        # serial_data['graph']['layout_direction'] = self.layout_direction()
        serial_data['graph']['acyclic'] = self.acyclic()
        serial_data['graph']['pipe_collision'] = self.pipe_collision()
        serial_data['graph']['pipe_slicing'] = self.pipe_slicing()
        serial_data['graph']['pipe_style'] = self.pipe_style()

        # connection constrains.
        serial_data['graph']['accept_connection_types'] = self.model.accept_connection_types
        serial_data['graph']['reject_connection_types'] = self.model.reject_connection_types

        # serialize nodes.
        for n in nodes:
            # update the node model.
            n.update_model()

            node_dict = n.model.to_dict
            nodes_data.update(node_dict)

        for n_id, n_data in nodes_data.items():
            serial_data['nodes'][n_id] = n_data

            # serialize connections
            inputs = n_data.pop('inputs') if n_data.get('inputs') else {}
            outputs = n_data.pop('outputs') if n_data.get('outputs') else {}

            for pname, conn_data in inputs.items():
                for conn_id, prt_names in conn_data.items():
                    for conn_prt in prt_names:
                        pipe = {
                            PortTypeEnum.IN.value: [n_id, pname],
                            PortTypeEnum.OUT.value: [conn_id, conn_prt]
                        }
                        if pipe not in serial_data['connections']:
                            serial_data['connections'].append(pipe)

            for pname, conn_data in outputs.items():
                for conn_id, prt_names in conn_data.items():
                    for conn_prt in prt_names:
                        pipe = {
                            PortTypeEnum.OUT.value: [n_id, pname],
                            PortTypeEnum.IN.value: [conn_id, conn_prt]
                        }
                        if pipe not in serial_data['connections']:
                            serial_data['connections'].append(pipe)

        if not serial_data['connections']:
            serial_data.pop('connections')

        return serial_data

    def _deserialize2(self, data, relative_pos=False, pos=None):
        """
        ALTERNATIVE TO _deserialize() METHOD WITHOUT push_undo

        deserialize node data.
        (used internally by the node graph)

        Args:
            data (dict): node data.
            relative_pos (bool): position node relative to the cursor.
            pos (tuple or list): custom x, y position.

        Returns:
            list[NodeGraphQt6.Nodes]: list of node instances.
        """
        # update node graph properties.
        for attr_name, attr_value in data.get('graph', {}).items():
            # if attr_name == 'layout_direction':
            #     self.set_layout_direction(attr_value)
            if attr_name == 'acyclic':
                self.set_acyclic(attr_value)
            elif attr_name == 'pipe_collision':
                self.set_pipe_collision(attr_value)
            elif attr_name == 'pipe_slicing':
                self.set_pipe_slicing(attr_value)
            elif attr_name == 'pipe_style':
                self.set_pipe_style(attr_value)

            # connection constrains.
            elif attr_name == 'accept_connection_types':
                self.model.accept_connection_types = attr_value
            elif attr_name == 'reject_connection_types':
                self.model.reject_connection_types = attr_value

        # build the nodes.
        nodes = {}
        for n_id, n_data in data.get('nodes', {}).items():
            identifier = n_data['type_']
            node = self._node_factory.create_node_instance(identifier)
            if node:
                node.NODE_NAME = n_data.get('name', node.NODE_NAME)
                # set properties.
                for prop in node.model.properties.keys():
                    if prop in n_data.keys():
                        node.model.set_property(prop, n_data[prop])
                # set custom properties.
                for prop, val in n_data.get('custom', {}).items():
                    node.model.set_property(prop, val)
                    if isinstance(node, BaseNode):
                        if prop in node.view.widgets:
                            node.view.widgets[prop].set_value(val)

                nodes[n_id] = node
                self.add_node(node, n_data.get('pos'), push_undo=False)
                node.set_layout_direction(n_data['layout_direction'])  # Fix

                if n_data.get('port_deletion_allowed', None):
                    node.set_ports({
                        'input_ports': n_data['input_ports'],
                        'output_ports': n_data['output_ports']
                    })

        # build the connections.
        for connection in data.get('connections', []):
            nid, pname = connection.get('in', ('', ''))
            in_node = nodes.get(nid) or self.get_node_by_id(nid)
            if not in_node:
                continue
            in_port = in_node.inputs().get(pname) if in_node else None

            nid, pname = connection.get('out', ('', ''))
            out_node = nodes.get(nid) or self.get_node_by_id(nid)
            if not out_node:
                continue
            out_port = out_node.outputs().get(pname) if out_node else None

            if in_port and out_port:
                # only connect if input port is not connected yet or input port
                # can have multiple connections.
                # important when duplicating nodes.
                allow_connection = any([not in_port.model.connected_ports,
                                        in_port.model.multi_connection])
                if allow_connection:
                    self._undo_stack.push(
                        PortConnectedCmd(in_port, out_port, emit_signal=False)
                    )

                # Run on_input_connected to ensure connections are fully set up
                # after deserialization.
                in_node.on_input_connected(in_port, out_port)

        node_objs = nodes.values()
        if relative_pos:
            self._viewer.move_nodes([n.view for n in node_objs])
            [setattr(n.model, 'pos', n.view.xy_pos) for n in node_objs]
        elif pos:
            self._viewer.move_nodes([n.view for n in node_objs], pos=pos)
            [setattr(n.model, 'pos', n.view.xy_pos) for n in node_objs]

        return node_objs

    def set_tooltip_default(self):
        """
        Set the default tooltip in all the nodes.
        """
        for node in self.all_nodes():
            node.set_tooltip_default()

    def update_tooltips(self):
        """
        Update the tooltips in the nodes.
        """
        for node in self.all_nodes():
            node.update_tooltip(self.net)
        
    def set_horizontal_layout_prop(self, node):
        """
        Set False to the 'layout_vert' property of a node.
        """
        layout_vert = node.get_property('layout_vert')
        if layout_vert is None:
            node.create_property('layout_vert', False)
        else:
            node.set_property('layout_vert', False, push_undo=False)
            
    def set_vertical_layout_prop(self, node):
        """
        Set True to the 'layout_vert' property of a node.
        """
        layout_vert = node.get_property('layout_vert')
        if layout_vert is None:
            node.create_property('layout_vert', True)
        else:
            node.set_property('layout_vert', True, push_undo=False)
    
    def disable_nodes(self, nodes, mode=None):
        """
        MODIFIED VERSION IN ORDER TO SIMULTANOUSLY DISABLE SOME ENABLED NODES
        AND ENABLE SOME DISABLED NODES.

        Set weather to Disable or Enable specified nodes.

        See Also:
            :meth:`NodeObject.set_disabled`

        Args:
            nodes (list[NodeGraphQt6.BaseNode]): list of node instances.
            mode (bool): (optional) disable state of the nodes.
        """
        if not nodes:
            return
        if mode is None:
            mode = [not node.disabled() for node in nodes]
        else:
            mode = [not nodes[0].disabled()] * len(nodes)

        # text = 'disable/enable ({}) nodes'.format(len(nodes))
        # self._undo_stack.beginMacro(text)
        for node, m in zip(nodes, mode):
            if node.type_=='SwitchNode.SwitchNode':
                continue
            node.set_disabled(m)
        # self._undo_stack.endMacro()

    def session_change_warning(self, tooltip_default=True, *args):
        """
        Show that some changes are unsaved in the statusbar.
        
        * tooltip_default: Set the default tooltip.
        """
        if 'fliped' in args:
            self.message_unsaved.show()
            self.set_tooltip_default()
            return
        
        if len(args)>0 and args[0].endswith('index'):
            self.message_unsaved.show()
            self.set_tooltip_default()
            return
        
        if 'layout_vert' in args:
            self.update_tooltips()
            # self.session_change_warning(False)
            # selected = self.selected_nodes()
            # self.clear_selection()
            # for node in selected:
            #     node.set_selected(True)
            # self.main_window.toolBox.setCurrentIndex(0)
            return
        
        # if 'layout_vert' in args:
        #     self.message_unsaved.show()
        #     self.update_tooltips()
        #     # tooltip_default.update()
        #     return
        # elif 'selected' in args:
        #     self.update_tooltips()
        #     # tooltip_default.update()
        #     return
            
        self.message_unsaved.show()
        if isinstance(tooltip_default, bool) and tooltip_default is True:
            self.set_tooltip_default()
        else:
            self.update_tooltips()

    def export_net(self):
        """
        Export the pandapower network using JSON format.
        """
        dir_path = self.config['general']['default_path']
        init_file_path = os.path.join(dir_path, f'{self.net.name}.json')
        full_file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self.main_window,
                                                                  caption='Export Pandapower Network',
                                                                  dir=init_file_path,
                                                                  filter='JSON Files (*.json)')

        if full_file_path:
            pp.to_json(self.net, full_file_path)
        else:
            simulate_ESC_key()

    def save_session(self):
        """
        Save the session to a file using the pickle module (graph and pandapower network data).
        If the file is already created, it is overwritten with the latest changes.
        """
        if self.saved_file_path is not None:
            with open(self.saved_file_path, 'wb') as file:
                data = {'graph_dict': self.serialize_session(),
                        'pandapower_net': pp.to_json(self.net, None)}
                pickle.dump(data, file)

            self.message_unsaved.hide()
        else:
            self.save_session_as()

    def save_session_as(self):
        """
        Save the session to a file using the pickle module (graph and pandapower network data).
        """
        if self.saved_file_path is None:
            dir_path = self.config['general']['default_path']
            init_file_path = os.path.join(dir_path, f'{self.net.name}.egs')
        else:
            init_file_path = self.saved_file_path

        full_file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                                self.main_window,
                                caption='Save Session',
                                dir=init_file_path,
                                filter='EGS Files (*.egs)')
        if full_file_path:
            with open(full_file_path, 'wb') as file:
                data = {'graph_dict': self.serialize_session(),
                        'pandapower_net': pp.to_json(self.net, None)}
                pickle.dump(data, file)

            self.saved_file_path = full_file_path
            self.message_unsaved.hide()
            _, file_name = os.path.split(full_file_path)
            self.set_main_window_title(file_name[:-4])
        else:
            simulate_ESC_key()

    def open_session(self):
        """
        Open session from a file and overwrite the current one (graph and pandapower network).
        """
        if self.saved_file_path is None:
            dir_path = self.config['general']['default_path']
        else:
            dir_path, _ = os.path.split(self.saved_file_path)

        full_file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.main_window,
                                                                  caption='Open Session',
                                                                  dir=dir_path,
                                                                  filter='EGS Files (*.egs)')

        if full_file_path:
            title = 'Warning: Current session will be lost'
            text_content = """The current session will be lost if it is not saved.
                            Do you want to continue anyway?"""
            button_response = QtWidgets.QMessageBox.warning(self.main_window, title, text_content,
                                          buttons=(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No),
                                          defaultButton=QtWidgets.QMessageBox.No)

            if button_response!=QtWidgets.QMessageBox.Yes:
                simulate_ESC_key()
                return

            with open(full_file_path, 'rb') as file:
                data = pickle.load(file)  # data dict
                self.deserialize_session(data['graph_dict'])
                self.net = pp.from_json_string(data['pandapower_net'])
                self.fit_to_selection()
                for node in self.all_nodes():
                    if node.type_=='BusNode.BusNode':
                        four_ports_on_buses(node)

            self.saved_file_path = full_file_path
            self.message_unsaved.hide()
            # self.update_tooltips()
            
            for node in self.all_nodes():
                layout_vert = node.get_property('layout_vert')
                if layout_vert is not None and layout_vert is True and node.type_!='BusNode.BusNode':
                    node.set_layout_direction(1)
                    
                    if self.config['general']['theme']=='light':
                        node.model.set_property('text_color', (0, 0, 0, 255))  # black
                    else:
                        node.model.set_property('text_color', (255, 255, 255, 180))  # default color
                    node.update()
            
            # for node in self.all_nodes():
            #     layout_vert = node.get_property('layout_vert')
            #     if layout_vert is not None and layout_vert is True:
            #         node.set_selected()
            # horizontal_layout(self)
            # vertical_layout(self)
            # self.clear_selection()
            
            if self.main_window.toolBox.currentIndex()==1:
                self.page_changed_on_toolbox(index=1)
                
            

        simulate_ESC_key()

        self.update_widgets_properties()
        self.update_tooltips()

        _, file_name = os.path.split(full_file_path)
        self.set_main_window_title(file_name[:-4])

    def new_session(self):
        """
        Clear the session (graph and pandapower network) and creates a new one.
        """
        title = 'Warning: Current session will be lost'
        text_content = """A new session will clear the current one, and data will be\
                        lost if it was not saved. Do you want to continue anyway?"""
        button_response = QtWidgets.QMessageBox.warning(self.main_window, title, text_content,
                                        buttons=(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No),
                                        defaultButton=QtWidgets.QMessageBox.No)

        if button_response!=QtWidgets.QMessageBox.Yes:
            simulate_ESC_key()
            return

        self.clear_session()
        settings = self.config['network']
        self.net = pp.create_empty_network(settings['name'],
                                           f_hz=float(settings['f_hz']),
                                           sn_mva=float(settings['sn_mva']))
        self.saved_file_path = None
        self.message_unsaved.hide()
        
        if self.main_window.toolBox.currentIndex()==1:
            self.page_changed_on_toolbox(index=1)

        self.set_main_window_title()

    def edit_settings(self):
        """
        Show the dialog to edit settings.
        """
        # show_WIP(self.main_window)
        dataframe_line_stds = pp.available_std_types(self.net, 'line')
        dataframe_trafo_stds = pp.available_std_types(self.net, 'trafo')
        dataframe_trafo3w_stds = pp.available_std_types(self.net, 'trafo3w')
        
        dialog = Settings_Dialog(self.main_window,
                                 self.config,
                                 dataframe_line_stds,
                                 dataframe_trafo_stds,
                                 dataframe_trafo3w_stds)
        self.config = dialog.exec()
        
        pipe_style = self.config['general']['pipe_style']
        if pipe_style=='curved':
            self.set_pipe_style(PipeLayoutEnum.CURVED.value)
        elif pipe_style=='straight':
            self.set_pipe_style(PipeLayoutEnum.STRAIGHT.value)
        elif pipe_style=='angle':
            self.set_pipe_style(PipeLayoutEnum.ANGLE.value)
            
        theme = self.config['general']['theme']
        if theme=='light':
            self.set_background_color(248, 249, 250)
        if self.config['general']['grid']=='True' and theme=='light':
            self.set_grid_mode(2)
            self.set_grid_color(236, 236, 236)
        elif self.config['general']['grid']=='True' and theme!='light':
            self.set_grid_mode(2)
        else:
            self.set_grid_mode(0)
            
        # Save the config file:
        with open(self.config_file_path, 'w') as f:
            self.config.write(f)

    def net_settings(self):
        """
        Open the dialog for setting the basic configuration of the pandapower network:

        * name
        * nominal frequency (f_hz)
        * base power (sn_mva)
        """
        dialog = network_settings_dialog()
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        
        dialog.name.setText(self.net.name)
        dialog.sn_mva.setValue(self.net.sn_mva)
        dialog.f_hz.setValue(self.net.f_hz)
        
        if dialog.exec():
            if (self.net.name!=dialog.name.text() or
                    self.net.sn_mva!=dialog.sn_mva.value() or
                    self.net.f_hz!=dialog.f_hz.value()):
                self.session_change_warning()
                
            self.net.name = dialog.name.text()
            self.net.sn_mva = dialog.sn_mva.value()
            self.net.f_hz = dialog.f_hz.value()
        
    def about(self):
        """
        Open the dialog 'About EGS' with version and authors informarion.
        """
        dialog = about_dialog()
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        dialog.exec()

    def add_bus(self, **kwargs):
        """
        Adds a bus to the network and graph.
        """
        center_coordinates = self.viewer().scene_center()
        node = self.create_node('BusNode.BusNode', name='Bus 0', pos=center_coordinates,
                                push_undo=False)
        # print(node.view.boundingRect().size().toSize())
        name_assigned = node.get_property('name')
        settings = self.config['bus']
        bus_index = pp.create_bus(self.net, vn_kv=float(settings['vn_kv']),
                                  name=name_assigned,
                                  min_vm_pu=float(settings['min_vm_pu']),
                                  max_vm_pu=float(settings['max_vm_pu']),
                                  geodata=center_coordinates)
        # node.create_property('bus_index', bus_index)
        node.set_property('bus_index', bus_index, push_undo=False)
        self.set_horizontal_layout_prop(node)
        # four_ports_on_buses(node)
        self.update_bus_ports()
        # print(self.net.bus)

    def add_line(self, **kwargs):
        """
        Adds a line to the graph (AC or DC line).
        """
        pos = kwargs.get('pos')
        option = kwargs.get('option')

        dialog = choose_line_dialog()
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        if pos is not None or dialog.exec():
            center_coordinates = pos if pos is not None else self.viewer().scene_center()
            if option=='line' or (dialog.radioAC.isChecked() and option is None):  # AC line
                node = self.create_node('LineNode.LineNode', name='Line 0', pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['line']
                for name, value in settings.items():
                    if name=='parallel':
                        node.set_property(name, int(float(value)), push_undo=False)
                    else:
                        node.set_property(name, float(value), push_undo=False)

            elif option=='stdline' or dialog.radioStdAC.isChecked():  # Std AC line
                node = self.create_node('StdLineNode.StdLineNode', name='Std Line 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['stdline']
                for name, value in settings.items():
                    if name=='parallel':
                        node.set_property(name, int(float(value)), push_undo=False)
                    elif name=='std_type':
                        node.set_property(name, value, push_undo=False)
                    else:
                        node.set_property(name, float(value), push_undo=False)

            elif option=='dcline' or dialog.radioDC.isChecked():  # DC line
                node = self.create_node('DCLineNode.DCLineNode', name='DC Line 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['dcline']
                for name, value in settings.items():
                    node.set_property(name, float(value), push_undo=False)

            self.set_horizontal_layout_prop(node)

        if (node_from := kwargs.get('node_from')) is not None and (node_to := kwargs.get('node_to')):
            i_port_from = 0 if kwargs.get('port_from')._name=='output' else 1
            i_port_to = 0 if kwargs.get('port_to')._name=='input' else 1
            node.set_input(0, node_from.output(i_port_from), push_undo=False)  # node.set_input(0, node_from.output(0), push_undo=False)
            node.set_output(0, node_to.input(i_port_to), push_undo=False)  # node.set_output(0, node_to.input(0), push_undo=False)
            return node

        self.update_bus_ports()

    def add_impedance(self, **kwargs):
        """
        Adds an impedance to the graph.
        """
        pos = kwargs.get('pos')

        center_coordinates = pos if pos is not None else self.viewer().scene_center()
        node = self.create_node('ImpedanceNode.ImpedanceNode', name='Impedance 0', pos=center_coordinates,
                                push_undo=False)
        settings = self.config['impedance']
        for name, value in settings.items():
            node.set_property(name, float(value), push_undo=False)
        self.set_horizontal_layout_prop(node)

        if (node_from := kwargs.get('node_from')) is not None and (node_to := kwargs.get('node_to')):
            i_port_from = 0 if kwargs.get('port_from')._name=='output' else 1
            i_port_to = 0 if kwargs.get('port_to')._name=='input' else 1
            node.set_input(0, node_from.output(i_port_from), push_undo=False)
            node.set_output(0, node_to.input(i_port_to), push_undo=False)
            return node
        
        self.update_bus_ports()

    def add_trafo(self, **kwargs):
        """
        Adds a transformer to the graph. Two- or three-winding transformers are available.
        """
        pos = kwargs.get('pos')
        option = kwargs.get('option')

        dialog = choose_transformer_dialog()
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        if pos is not None or dialog.exec():
            center_coordinates = pos if pos is not None else self.viewer().scene_center()
            if option=='trafo' or (dialog.radio2w.isChecked() and option is None):  # 2W-Trafo
                node = self.create_node('TrafoNode.TrafoNode', name='Transformer 0',
                                        pos=center_coordinates, push_undo=False)
                settings = self.config['trafo']

            if option=='stdtrafo' or dialog.radio2w_std.isChecked():  # 2W-StdTrafo
                node = self.create_node('StdTrafoNode.StdTrafoNode', name='Std Trafo 0',
                                        pos=center_coordinates, push_undo=False)
                settings = self.config['stdtrafo']
                stds = pp.available_std_types(self.net, element='trafo')

            elif dialog.radio3w.isChecked():  # 3W-Trafo
                node = self.create_node('Trafo3wNode.Trafo3wNode', name='Transformer 0',
                                        pos=center_coordinates, push_undo=False)
                settings = self.config['trafo3w']

            elif dialog.radio3w_std.isChecked():  # 3W-StdTrafo
                node = self.create_node('StdTrafo3wNode.StdTrafo3wNode', name='Std Trafo 0',
                                        pos=center_coordinates, push_undo=False)
                settings = self.config['stdtrafo3w']
                stds = pp.available_std_types(self.net, element='trafo3w')

            for name, value in settings.items():
                if name in ('tap_side', 'vector_group', 'std_type'):
                    node.set_property(name, value, push_undo=False)
                elif name in ('tap_neutral', 'tap_max', 'tap_min', 'tap_pos', 'parallel'):
                    node.set_property(name, int(value), push_undo=False)
                elif name in ('tap_phase_shifter', 'oltc', '') and value=='True':
                    node.set_property(name, True, push_undo=False)
                elif name in ('tap_phase_shifter', 'oltc', 'tap_at_star_point') and value=='False':
                    node.set_property(name, False, push_undo=False)
                else:
                    node.set_property(name, float(value), push_undo=False)

                if name=='tap_min':
                    node.tap_pos_widget.get_custom_widget().setMinimum(int(value))
                elif name=='tap_max':
                    node.tap_pos_widget.get_custom_widget().setMaximum(int(value))

            if dialog.radio2w_std.isChecked() or dialog.radio3w_std.isChecked():  # StdTrafo
                tap_pos = stds.at[settings['std_type'], 'tap_neutral']
                node.set_property('tap_pos', tap_pos, push_undo=False)

                tap_min = stds.at[settings['std_type'], 'tap_min']
                node.tap_pos_widget.get_custom_widget().setMinimum(int(tap_min))

                tap_max = stds.at[settings['std_type'], 'tap_max']
                node.tap_pos_widget.get_custom_widget().setMaximum(int(tap_max))

            self.set_horizontal_layout_prop(node)

        if (node_from := kwargs.get('node_from')) is not None and (node_to := kwargs.get('node_to')):
            i_port_from = 0 if kwargs.get('port_from')._name=='output' else 1
            i_port_to = 0 if kwargs.get('port_to')._name=='input' else 1
            node.set_input(0, node_from.output(i_port_from), push_undo=False)
            node.set_output(0, node_to.input(i_port_to), push_undo=False)
            return node

        self.update_bus_ports()

    def add_generator(self, **kwargs):
        """
        Adds a generator to the graph: voltage-controlled gen.,
        static gen. or asymmetric static generator.
        """
        dialog = choose_generator_dialog()
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        if dialog.exec():
            center_coordinates = self.viewer().scene_center()

            if dialog.radioGen.isChecked():
                node = self.create_node('GenNode.GenNode', name='Generator 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['gen']
                for name, value in settings.items():
                    if name=='controllable' and value=='True':
                        node.set_property(name, True, push_undo=False)
                    elif name=='controllable' and value=='False':
                        node.set_property(name, False, push_undo=False)
                    else:
                        node.set_property(name, float(value), push_undo=False)

                node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
                node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))

            elif dialog.radioStaticGen.isChecked():
                node = self.create_node('SGenNode.SGenNode', name='Static Gen 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['sgen']
                for name, value in settings.items():
                    if name in ('controllable', 'current_source') and value=='True':
                        node.set_property(name, True, push_undo=False)
                    elif name in ('controllable', 'current_source') and value=='False':
                        node.set_property(name, False, push_undo=False)
                    elif name=='type':
                        node.set_property(name, value, push_undo=False)  # str
                    elif name=='generator_type' and value=='None':
                        node.set_property(name, None, push_undo=False)  # None
                    elif name=='generator_type' and value!='None':
                        node.set_property(name, value, push_undo=False)  # str
                    else:
                        node.set_property(name, float(value), push_undo=False)  # float

                node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
                node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
                node.q_mvar_widget.get_custom_widget().setMinimum(node.get_property('min_q_mvar'))
                node.q_mvar_widget.get_custom_widget().setMaximum(node.get_property('max_q_mvar'))

            elif dialog.radioAStaticGen.isChecked():
                node = self.create_node('ASGenNode.ASGenNode', name='Asymmetric SGen 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['asymmetric_sgen']
                for name, value in settings.items():
                    if name=='type':
                        node.set_property(name, value, push_undo=False)  # str
                    else:
                        node.set_property(name, float(value), push_undo=False)  # float

            self.set_vertical_layout_prop(node)
            node.set_layout_direction(1)
            # node.flip()
            theme = self.config['general']['theme']
            if theme=='light':
                node.model.set_property('text_color', (0, 0, 0, 255))  # black
                node.update()

        self.update_bus_ports()

    def add_external_grid(self, **kwargs):
        """
        Adds an external grid to the graph.
        """
        center_coordinates = self.viewer().scene_center()
        node = self.create_node('ExtGridNode.ExtGridNode', name='Ext Grid 0',
                                pos=center_coordinates,
                                push_undo=False)
        
        settings = self.config['ext_grid']
        for name, value in settings.items():
            if name=='controllable' and value=='True':
                node.set_property(name, True, push_undo=False)  # boolean
            elif name=='controllable' and value=='False':
                node.set_property(name, False, push_undo=False)  # boolean
            else:
                node.set_property(name, float(value), push_undo=False)  # float
        # self.set_horizontal_layout_prop(node)
        
        self.set_vertical_layout_prop(node)
        node.set_layout_direction(1)
        theme = self.config['general']['theme']
        if theme=='light':
            node.model.set_property('text_color', (0, 0, 0, 255))  # black
            node.update()
        
        self.update_bus_ports()

    def add_load(self, **kwargs):
        """
        Adds a load to the graph: load, asymmetric load, shunt element,
        motor, ward or extended ward.
        """
        dialog = choose_load_dialog()
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        if dialog.exec():
            center_coordinates = self.viewer().scene_center()

            if dialog.radioLoad.isChecked():
                node = self.create_node('LoadNode.LoadNode', name='Load 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['load']
                for name, value in settings.items():
                    if name=='controllable' and value=='True':
                        node.set_property(name, True, push_undo=False)  # bool
                    elif name=='controllable' and value=='False':
                        node.set_property(name, False, push_undo=False)  # bool
                    elif name=='type':
                        node.set_property(name, value, push_undo=False)  # str
                    else:
                        node.set_property(name, float(value), push_undo=False)  # float

                node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
                node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
                node.q_mvar_widget.get_custom_widget().setMinimum(node.get_property('min_q_mvar'))
                node.q_mvar_widget.get_custom_widget().setMaximum(node.get_property('max_q_mvar'))

            elif dialog.radioALoad.isChecked():
                node = self.create_node('ALoadNode.ALoadNode',
                                        name='Asymmetric Load 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['asymmetric_load']
                for name, value in settings.items():
                    if name=='type':
                        node.set_property(name, value, push_undo=False)  # str
                    else:
                        node.set_property(name, float(value), push_undo=False)  # float

            elif dialog.radioShunt.isChecked():
                node = self.create_node('ShuntNode.ShuntNode', name='Shunt 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['shunt']
                for name, value in settings.items():
                    if name=='vn_kv' and value=='None':
                        node.set_property(name, None, push_undo=False)  # Nonetype
                    elif name in ('step', 'max_step'):
                        node.set_property(name, int(value), push_undo=False)  # int
                    else:
                        node.set_property(name, float(value), push_undo=False)  # float

                node.step_widget.get_custom_widget().setMaximum(node.get_property('max_step'))

            elif dialog.radioMotor.isChecked():
                node = self.create_node('MotorNode.MotorNode', name='Motor 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['motor']
                for name, value in settings.items():
                    node.set_property(name, float(value), push_undo=False)  # float

            elif dialog.radioWard.isChecked():
                node = self.create_node('WardNode.WardNode', name='Ward 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['ward']
                for name, value in settings.items():
                    node.set_property(name, float(value), push_undo=False)

            elif dialog.radioExtendedWard.isChecked():
                node = self.create_node('XWardNode.XWardNode', name='XWard 0',
                                        pos=center_coordinates,
                                        push_undo=False)
                settings = self.config['xward']
                for name, value in settings.items():
                    node.set_property(name, float(value), push_undo=False)

            self.set_vertical_layout_prop(node)
            node.set_layout_direction(1)
            theme = self.config['general']['theme']
            if theme=='light':
                node.model.set_property('text_color', (0, 0, 0, 255))  # black
                node.update()

        self.update_bus_ports()

    def includes_switch(self, bus, node_bus, element, et, node_element,
                        port_number_element, bus_left, **kwargs):
        """
        Adds a Switch Node and a switch element in the pandapower network.
        
        Similar to 'add_switch', but without dialogs.
        
        Inputs:
                * bus: Bus index to connect de switch
                * node_bus: BusNode that will be connected to the switch
                * element: index of the other component
                * et (element type): 'b' for bus, 'l' for line, 't' for a 2w-trafo
                                     and 't3' for a 3w-trafo
                * node_element: Node that will be connected to the switch.
                * port_number_element: Por number of the element that will be connected
                                       to the switch.
                * bus_left (boolean): True if connection is BUS-SWITCH-ELEMENT
                                      False if connection is ELEMENT-SWITCH-BUS
        """
        pos0 = node_bus.pos()
        pos1 = node_element.pos()
        coordinates = [ (pos0[0] + pos1[0])*0.5, (pos0[1] + pos1[1])*0.5 ]
        node = self.create_node('SwitchNode.SwitchNode', name='Switch 0',
                                pos=coordinates,
                                push_undo=False)
        settings = self.config['switch']
        for name, value in settings.items():
            if name=='closed' and value=='True':
                node.set_property(name, True, push_undo=False)  # boolean
            elif name=='closed' and value=='False':
                node.set_property(name, False, push_undo=False)  # boolean
            elif name=='type':
                node.set_property(name, value, push_undo=False)  # str or None
            else:
                node.set_property(name, float(value), push_undo=False)  # float
                
        # Adding a switch to pandapower network
        switch_index = pp.create_switch(self.net, bus=bus, element=element, et=et,
                            closed=node.get_property('closed'),
                            type=node.get_property('type'),
                            z_ohm=node.get_property('z_ohm'),
                            in_ka=node.get_property('in_ka'),
                            name=node.name())
        try:
            node.create_property('switch_index', switch_index)
        except errors.NodePropertyError:
            node.set_property('switch_index', switch_index, push_undo=False)
        # print(self.net.switch)
        
        
        if et=='b' and (node_from := kwargs.get('node_from')) is not None and (node_to := kwargs.get('node_to')):
            i_port_from = 0 if kwargs.get('port_from')._name=='output' else 1
            i_port_to = 0 if kwargs.get('port_to')._name=='input' else 1
            node.set_input(0, node_from.output(i_port_from), push_undo=False)
            node.set_output(0, node_to.input(i_port_to), push_undo=False)            
        else:
            if et=='b' and pos0[0]<pos1[0]:
                bus_left = True
            elif et=='b' and pos0[0]>=pos1[0]:
                bus_left = False

            if bus_left:
                if (port := kwargs.get('port_from')) is not None:
                    i_port_from = 0 if port.name()=='output' else 1
                else:
                    i_port_from = 0
                node.set_input(0, node_bus.output(i_port_from), push_undo=False)
                node.set_output(0, node_element.input(port_number_element), push_undo=False)
            else:
                if (port := kwargs.get('port_to')) is not None:
                    i_port_to = 0 if port.name()=='input' else 1
                else:
                    i_port_to = 0
                node.set_output(0, node_bus.input(i_port_to), push_undo=False)
                node.set_input(0, node_element.output(port_number_element), push_undo=False)
            
        node.set_locked(True)
        self.set_horizontal_layout_prop(node)
        self.update_bus_ports()
    
    def add_switch(self, **kwargs):
        """
        Adds a switch to the graph.
        """
        selected = self.selected_nodes()
        if len(selected)==1 and (node := selected[0]).type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode'):
            if not node.connected_to_network():
                title = 'Error when adding a switch'
                text_content = 'Line component has to be connected to the network' +\
                    ' before adding the switch.'
                QtWidgets.QMessageBox.critical(self.main_window, title, text_content)
                return
            
            et = 'l'
            element = node.get_property('line_index')
            node_bus0 = node.connected_input_nodes()[node.input_port][0]
            node_bus1 = node.connected_output_nodes()[node.output_port][0]
            
            if node_bus0.type_=='SwitchNode.SwitchNode' and node_bus1.type_=='SwitchNode.SwitchNode':
                title = 'Adding a switch'
                text_content = 'Switches are already connected before and after the selected element.'
                QtWidgets.QMessageBox.critical(self.main_window, title, text_content)
                return
            
            if node_bus0.type_=='BusNode.BusNode' and node_bus1.type_=='SwitchNode.SwitchNode':
                bus = node_bus0.get_property('bus_index')
                for port_, nodes_ in node_bus0.connected_output_nodes().items():
                    for node_ in nodes_:
                        if node_.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode') and node_.get_property('line_index')==element:
                            port_from = port_

                self.includes_switch(bus, node_bus0, element, et, node, 0, bus_left=True,
                                     node_from=node_bus0, node_to=node, port_from=port_from,
                                     port_to=node.input_port)
                return
            
            if node_bus0.type_=='SwitchNode.SwitchNode' and node_bus1.type_=='BusNode.BusNode':
                bus = node_bus1.get_property('bus_index')
                for port_, nodes_ in node_bus1.connected_input_nodes().items():
                    for node_ in nodes_:
                        if node_.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode') and node_.get_property('line_index')==element:
                            port_to = port_
                self.includes_switch(bus, node_bus1, element, et, node, 0, bus_left=False,
                                     node_from=node, node_to=node_bus1, port_from=node.output_port,
                                     port_to=port_to)
                return
            
            index0 = node_bus0.get_property('bus_index')
            name0 = node_bus0.get_property('name')
            txt0 = f'({index0}) {name0}'
            
            index1 = node_bus1.get_property('bus_index')
            name1 = node_bus1.get_property('name')
            txt1 = f'({index1}) {name1}'
            
            dialog = choose_bus_switch_dialog()
            dialog.setWindowIcon(QtGui.QIcon(icon_path))
            dialog.comboBox.addItems((txt0, txt1))
            if dialog.exec():
                selected_bus = dialog.comboBox.currentIndex()
                if selected_bus==0:
                    bus = index0
                    bus_left = True
                    node_bus = node_bus0
                    node_from = node_bus0
                    node_to = node
                    port_to = node.input_port
                    for port_, nodes_ in node_bus0.connected_output_nodes().items():
                        for node_ in nodes_:
                            if node_.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode') and node_.get_property('line_index')==element:
                                port_from = port_
                elif selected_bus==1:
                    bus = index1
                    bus_left = False
                    node_bus = node_bus1
                    node_from = node
                    node_to = node_bus1
                    port_from = node.output_port
                    for port_, nodes_ in node_bus1.connected_input_nodes().items():
                        for node_ in nodes_:
                            if node_.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode') and node_.get_property('line_index')==element:
                                port_to = port_
                self.includes_switch(bus, node_bus, element, et, node, 0, bus_left,
                                     node_from=node_from, node_to=node_to,
                                     port_from=port_from, port_to=port_to)
                        
            return
        
        elif len(selected)==1 and (node := selected[0]).type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode'):
            if not node.connected_to_network():
                title = 'Error when adding a switch'
                text_content = 'Transformer component has to be connected to the network' +\
                    ' before adding the switch.'
                QtWidgets.QMessageBox.critical(self.main_window, title, text_content)
                return
            
            et = 't'
            element = node.get_property('transformer_index')
            node_bus0 = node.connected_input_nodes()[node.input_port][0]
            node_bus1 = node.connected_output_nodes()[node.output_port][0]
            
            if node_bus0.type_=='SwitchNode.SwitchNode' and node_bus1.type_=='SwitchNode.SwitchNode':
                title = 'Adding a switch'
                text_content = 'Switches are already connected before and after the selected element.'
                QtWidgets.QMessageBox.critical(self.main_window, title, text_content)
                return
            
            if node_bus0.type_=='BusNode.BusNode' and node_bus1.type_=='SwitchNode.SwitchNode':
                bus = node_bus0.get_property('bus_index')
                for port_, nodes_ in node_bus0.connected_output_nodes().items():
                    for node_ in nodes_:
                        if node_.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode') and node_.get_property('transformer_index')==element:
                            port_from = port_
                self.includes_switch(bus, node_bus0, element, et, node, 0, bus_left=True,
                                     node_from=node_bus0, node_to=node, port_from=port_from,
                                     port_to=node.input_port)
                return
            
            if node_bus0.type_=='SwitchNode.SwitchNode' and node_bus1.type_=='BusNode.BusNode':
                bus = node_bus1.get_property('bus_index')
                for port_, nodes_ in node_bus1.connected_input_nodes().items():
                    for node_ in nodes_:
                        if node_.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode') and node_.get_property('transformer_index')==element:
                            port_to = port_
                self.includes_switch(bus, node_bus1, element, et, node, 0, bus_left=False,
                                     node_from=node, node_to=node_bus1, port_from=node.output_port,
                                     port_to=port_to)
                return
            
            index0 = node_bus0.get_property('bus_index')
            name0 = node_bus0.get_property('name')
            txt0 = f'({index0}) {name0}'
            
            index1 = node_bus1.get_property('bus_index')
            name1 = node_bus1.get_property('name')
            txt1 = f'({index1}) {name1}'
            
            dialog = choose_bus_switch_dialog()
            dialog.setWindowIcon(QtGui.QIcon(icon_path))
            dialog.comboBox.addItems((txt0, txt1))
            if dialog.exec():
                selected_bus = dialog.comboBox.currentIndex()
                if selected_bus==0:
                    bus = index0
                    bus_left = True
                    node_bus = node_bus0
                    node_from = node_bus0
                    node_to = node
                    port_to = node.input_port
                    for port_, nodes_ in node_bus0.connected_output_nodes().items():
                        for node_ in nodes_:
                            if node_.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode') and node_.get_property('transformer_index')==element:
                                port_from = port_
                elif selected_bus==1:
                    bus = index1
                    bus_left = False
                    node_bus = node_bus1
                    node_from = node
                    node_to = node_bus1
                    port_from = node.output_port
                    for port_, nodes_ in node_bus1.connected_input_nodes().items():
                        for node_ in nodes_:
                            if node_.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode') and node_.get_property('transformer_index')==element:
                                port_to = port_
                self.includes_switch(bus, node_bus, element, et, node, 0, bus_left,
                                     node_from=node_from, node_to=node_to,
                                     port_from=port_from, port_to=port_to)
                        
            return
         
        elif len(selected)==1 and (node := selected[0]).type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode'):
            if not node.connected_to_network():
                title = 'Error when adding a switch'
                text_content = 'Transformer component has to be connected to the network' +\
                    ' before adding the switch.'
                QtWidgets.QMessageBox.critical(self.main_window, title, text_content)
                return
            
            et = 't3'
            element = node.get_property('transformer_index')
            node_bus0 = node.connected_input_nodes()[node.input_port][0]
            node_bus1 = node.connected_output_nodes()[node.output_port1][0]
            node_bus2 = node.connected_output_nodes()[node.output_port2][0]
            
            if node_bus0.type_=='SwitchNode.SwitchNode' and node_bus1.type_=='SwitchNode.SwitchNode' and node_bus2.type_=='SwitchNode.SwitchNode':
                title = 'Adding a switch'
                text_content = 'Switches are already connected.'
                QtWidgets.QMessageBox.critical(self.main_window, title, text_content)
                return
            
            if node_bus0.type_=='BusNode.BusNode' and node_bus1.type_=='SwitchNode.SwitchNode' and node_bus2.type_=='SwitchNode.SwitchNode':
                bus = node_bus0.get_property('bus_index')
                for port_, nodes_ in node_bus0.connected_output_nodes().items():
                    for node_ in nodes_:
                        if node_.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode') and node_.get_property('transformer_index')==element:
                            port_from = port_
                self.includes_switch(bus, node_bus0, element, et, node, 0, bus_left=True,
                                     node_from=node_bus0, node_to=node, port_from=port_from,
                                     port_to=node.input_port)
                return
            
            if node_bus0.type_=='SwitchNode.SwitchNode' and node_bus1.type_=='BusNode.BusNode' and node_bus2.type_=='SwitchNode.SwitchNode':
                bus = node_bus1.get_property('bus_index')
                for port_, nodes_ in node_bus1.connected_input_nodes().items():
                    for node_ in nodes_:
                        if node_.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode') and node_.get_property('transformer_index')==element:
                            port_to = port_
                self.includes_switch(bus, node_bus1, element, et, node, 0, bus_left=False,
                                     node_from=node, node_to=node_bus1, port_from=node.output_port1,
                                     port_to=port_to)
                return
            
            if node_bus0.type_=='SwitchNode.SwitchNode' and node_bus1.type_=='SwitchNode.SwitchNode' and node_bus2.type_=='BusNode.BusNode':
                bus = node_bus2.get_property('bus_index')
                for port_, nodes_ in node_bus2.connected_input_nodes().items():
                    for node_ in nodes_:
                        if node_.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode') and node_.get_property('transformer_index')==element:
                            port_to = port_
                self.includes_switch(bus, node_bus2, element, et, node, 1, bus_left=False,
                                     node_from=node, node_to=node_bus2, port_from=node.output_port2,
                                     port_to=port_to)
                return
            
            combobox_items = []  # init...
            items = []  # init...
            
            index0 = index1 = index2 = None
            if node_bus0.type_=='BusNode.BusNode':
                index0 = node_bus0.get_property('bus_index')
                name0 = node_bus0.get_property('name')
                txt0 = f'({index0}) {name0}'
                combobox_items.append(txt0)
                items.append(node_bus0)
            
            if node_bus1.type_=='BusNode.BusNode':
                index1 = node_bus1.get_property('bus_index')
                name1 = node_bus1.get_property('name')
                txt1 = f'({index1}) {name1}'
                combobox_items.append(txt1)
                items.append(node_bus1)
                
            if node_bus2.type_=='BusNode.BusNode':
                index2 = node_bus2.get_property('bus_index')
                name2 = node_bus2.get_property('name')
                txt2 = f'({index2}) {name2}'
                combobox_items.append(txt2)
                items.append(node_bus2)
            
            dialog = choose_bus_switch_dialog()
            dialog.setWindowIcon(QtGui.QIcon(icon_path))
            dialog.comboBox.addItems(combobox_items)
            if dialog.exec():
                selected_bus = dialog.comboBox.currentIndex()
                selected_txt = combobox_items[selected_bus]
                if index0 is not None and selected_txt.startswith(f'({index0})'):
                    bus = index0
                    bus_left = True
                    node_bus = node_bus0
                    port_number_element = 0
                    node_from = node_bus0
                    node_to = node
                    port_to = node.input_port
                    for port_, nodes_ in node_bus0.connected_output_nodes().items():
                        for node_ in nodes_:
                            if node_.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode') and node_.get_property('transformer_index')==element:
                                port_from = port_
                elif index1 is not None and selected_txt.startswith(f'({index1})'):
                    bus = index1
                    bus_left = False
                    node_bus = node_bus1
                    port_number_element = 0
                    node_from = node
                    node_to = node_bus1
                    port_from = node.output_port1
                    for port_, nodes_ in node_bus1.connected_input_nodes().items():
                        for node_ in nodes_:
                            if node_.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode') and node_.get_property('transformer_index')==element:
                                port_to = port_
                elif index2 is not None and selected_txt.startswith(f'({index2})'):
                    bus = index2
                    bus_left = False
                    node_bus = node_bus2
                    port_number_element = 1
                    node_from = node
                    node_to = node_bus2
                    port_from = node.output_port2
                    for port_, nodes_ in node_bus2.connected_input_nodes().items():
                        for node_ in nodes_:
                            if node_.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode') and node_.get_property('transformer_index')==element:
                                port_to = port_
                self.includes_switch(bus, node_bus, element, et,
                                     node, port_number_element, bus_left,
                                     node_from=node_from, node_to=node_to,
                                     port_from=port_from, port_to=port_to)
                        
            return
            
        elif len(selected)==2 and (node0 := selected[0]).type_=='BusNode.BusNode' and (node1 := selected[1]).type_=='BusNode.BusNode':
            et = 'b'
            element = node1.get_property('bus_index')
            bus = node0.get_property('bus_index')
            self.includes_switch(bus, node0, element, et,
                                 node1, 0, bus_left=True, **kwargs)
        
        else:
            title = 'Error when adding a switch'
            text_content = 'Only one component has to be selected' +\
                ' (AC Line or Transformer), or eventually two buses.'
            QtWidgets.QMessageBox.critical(self.main_window, title, text_content)
            return
    
    def add_storage(self, **kwargs):
        """
        Adds a storage to the graph.
        """
        center_coordinates = self.viewer().scene_center()
        node = self.create_node('StorageNode.StorageNode', name='Storage 0',
                                pos=center_coordinates,
                                push_undo=False)
        settings = self.config['storage']
        for name, value in settings.items():
            if name=='controllable' and value=='True':
                node.set_property(name, True, push_undo=False)  # boolean
            elif name=='controllable' and value=='False':
                node.set_property(name, False, push_undo=False)  # boolean
            elif name=='type':
                node.set_property(name, value, push_undo=False)  # str
            else:
                node.set_property(name, float(value), push_undo=False)  # float
        # self.set_horizontal_layout_prop(node)
        self.set_vertical_layout_prop(node)
        node.set_layout_direction(1)
        theme = self.config['general']['theme']
        if theme=='light':
            node.model.set_property('text_color', (0, 0, 0, 255))  # black
            node.update()
        
        self.update_bus_ports()

    def disconnect_component(self, port0, port1):
        """
        Removes the corresponding pandapower component if one of its
        ports is disconnected.
        """
        if port0.node().type_=='GenNode.GenNode':
            self.remove_gen(port0.node())
            
        if port1.node().type_=='GenNode.GenNode':
            self.remove_gen(port1.node())
            
        if port0.node().type_=='SGenNode.SGenNode':
            self.remove_sgen(port0.node())
            
        if port1.node().type_=='SGenNode.SGenNode':
            self.remove_sgen(port1.node())
            
        if port0.node().type_=='ASGenNode.ASGenNode':
            self.remove_asgen(port0.node())
            
        if port1.node().type_=='ASGenNode.ASGenNode':
            self.remove_asgen(port1.node())
            
        if port0.node().type_=='ExtGridNode.ExtGridNode':
            self.remove_ext_grid(port0.node())
            
        if port1.node().type_=='ExtGridNode.ExtGridNode':
            self.remove_ext_grid(port1.node())
            
        if port0.node().type_=='LoadNode.LoadNode':
            self.remove_load(port0.node())
            
        if port1.node().type_=='LoadNode.LoadNode':
            self.remove_load(port1.node())
            
        if port0.node().type_=='ALoadNode.ALoadNode':
            self.remove_aload(port0.node())
            
        if port1.node().type_=='ALoadNode.ALoadNode':
            self.remove_aload(port1.node())
            
        if port0.node().type_=='ShuntNode.ShuntNode':
            self.remove_shunt(port0.node())
            
        if port1.node().type_=='ShuntNode.ShuntNode':
            self.remove_shunt(port1.node())
            
        if port0.node().type_=='MotorNode.MotorNode':
            self.remove_motor(port0.node())
            
        if port1.node().type_=='MotorNode.MotorNode':
            self.remove_motor(port1.node())
            
        if port0.node().type_=='WardNode.WardNode':
            self.remove_ward(port0.node())
            
        if port1.node().type_=='WardNode.WardNode':
            self.remove_ward(port1.node())
            
        if port0.node().type_=='XWardNode.XWardNode':
            self.remove_xward(port0.node())
            
        if port1.node().type_=='XWardNode.XWardNode':
            self.remove_xward(port1.node())
            
        if port0.node().type_=='StorageNode.StorageNode':
            self.remove_storage(port0.node())
            
        if port1.node().type_=='StorageNode.StorageNode':
            self.remove_storage(port1.node())
    
    def connection_changed(self, disconnected, connected):
        """
        Checks connection restrictions and updates pandapower network when nodes
        are connected or disconnected.

        disconnected: List of recently diconnected pipes.
        connected: List of recently connected pipes.
        """
        self.session_change_warning()
        for pipe in disconnected:
            # print('Disconnected:', pipe)
            for port in pipe:
                node = self.get_node_by_name(port.node.name)
                if node.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode'):
                    self.remove_line(node)
                elif node.type_=='DCLineNode.DCLineNode':
                    self.remove_dcline(node)
                elif node.type_=='ImpedanceNode.ImpedanceNode':
                    self.remove_impedance(node)
                elif node.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode'):
                    self.remove_trafo(node)
                elif node.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode'):
                    self.remove_trafo3w(node)
                elif node.type_=='GenNode.GenNode':
                    self.remove_gen(node)
                elif node.type_=='SGenNode.SGenNode':
                    self.remove_sgen(node)
                elif node.type_=='ASGenNode.ASGenNode':
                    self.remove_asgen(node)
                elif node.type_=='ExtGridNode.ExtGridNode':
                    self.remove_ext_grid(node)
                elif node.type_=='LoadNode.LoadNode':
                    self.remove_load(node)
                elif node.type_=='ALoadNode.ALoadNode':
                    self.remove_aload(node)
                elif node.type_=='ShuntNode.ShuntNode':
                    self.remove_shunt(node)
                elif node.type_=='MotorNode.MotorNode':
                    self.remove_motor(node)
                elif node.type_=='WardNode.WardNode':
                    self.remove_ward(node)
                elif node.type_=='XWardNode.XWardNode':
                    self.remove_xward(node)
                elif node.type_=='StorageNode.StorageNode':
                    self.remove_storage(node)
                elif node.type_=='SwitchNode.SwitchNode':
                    self.remove_switch(node)

        for pipe in connected:
            # print('Connected:', pipe)
            port0 = pipe[0]
            if port0.port_type == PortTypeEnum.OUT.value:
                port_from = pipe[0]
                port_to = pipe[1]
            else:
                port_from = pipe[1]
                port_to = pipe[0]

            node_from = self.get_node_by_name(port_from.node.name)
            node_to = self.get_node_by_name(port_to.node.name)

            # If 2 buses gets connected...
            if node_from.type_=='BusNode.BusNode' and node_to.type_=='BusNode.BusNode':
                # port_from.disconnect_from(port_to)
                # self._on_connection_changed(disconnected=[pipe], connected=[])
                dialog = connecting_buses_dialog()
                dialog.setWindowIcon(QtGui.QIcon(icon_path))
                main_win_rect = self.main_window.geometry()
                dialog.setParent(self.main_window)
                dialog.move(main_win_rect.center() - dialog.rect().center())  # centering in the main window
                self._on_connection_changed(disconnected=[pipe], connected=[])

                def dialog_closed(result, node_from=node_from, node_to=node_to,
                                  port_from=port_from, port_to=port_to):
                    if not result:
                        return

                    if dialog.option in ('line', 'stdline', 'dcline'):
                        pos0 = node_from.pos()
                        pos1 = node_to.pos()
                        pos = [(pos0[0] + pos1[0]) * 0.5, (pos0[1] + pos1[1]) * 0.5]
                        node_from = self.add_line(pos=pos, option=dialog.option,
                                                node_from=node_from,
                                                node_to=node_to,
                                                port_from=port_from,
                                                port_to=port_to)
                    elif dialog.option in ('trafo', 'stdtrafo'):
                        pos0 = node_from.pos()
                        pos1 = node_to.pos()
                        pos = [(pos0[0] + pos1[0]) * 0.5, (pos0[1] + pos1[1]) * 0.5]
                        node_from = self.add_trafo(pos=pos, option=dialog.option,
                                                node_from=node_from,
                                                node_to=node_to,
                                                port_from=port_from,
                                                port_to=port_to)
                    elif dialog.option=='impedance':
                        pos0 = node_from.pos()
                        pos1 = node_to.pos()
                        pos = [(pos0[0] + pos1[0]) * 0.5, (pos0[1] + pos1[1]) * 0.5]
                        node_from = self.add_impedance(pos=pos,
                                                    node_from=node_from,
                                                    node_to=node_to,
                                                    port_from=port_from,
                                                    port_to=port_to)
                    elif dialog.option=='switch':
                        self.clear_selection()
                        node_from.set_selected(True)
                        node_to.set_selected(True)
                        self.add_switch(node_from=node_from,
                                        node_to=node_to,
                                        port_from=port_from,
                                        port_to=port_to)

                dialog.finished.connect(dialog_closed)
                dialog.open()

            if {node_from.type_, node_to.type_} not in allowed_connections:
                # port_from.disconnect_from(port_to)
                self._on_connection_changed(disconnected=[pipe], connected=[])
                return

            # Adding line to pandapower network
            if node_from.type_=='LineNode.LineNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_from = n.get_property('bus_index')
                    bus_index_to = node_to.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        line_index = pp.create_line_from_parameters(self.net, from_bus=bus_index_from,
                                                to_bus=bus_index_to,
                                                length_km=node_from.get_property('length_km'),
                                                r_ohm_per_km=node_from.get_property('r_ohm_per_km'),
                                                parallel=node_from.get_property('parallel'),
                                                df=node_from.get_property('df'),
                                                x_ohm_per_km=node_from.get_property('x_ohm_per_km'),
                                                c_nf_per_km=node_from.get_property('c_nf_per_km'),
                                                max_i_ka=node_from.get_property('max_i_ka'),
                                                name=node_from.name(),
                                                in_service=not node_from.disabled(),
                                                g_us_per_km=node_from.get_property('g_us_per_km'),
                                                r0_ohm_per_km=node_from.get_property('r0_ohm_per_km'),
                                                x0_ohm_per_km=node_from.get_property('x0_ohm_per_km'),
                                                c0_nf_per_km=node_from.get_property('c0_nf_per_km'),
                                                g0_us_per_km=node_from.get_property('g0_us_per_km'),
                                                max_loading_percent=node_from.get_property('max_loading_percent'),
                                                alpha=node_from.get_property('alpha'),
                                                temperature_degree_celsius=node_from.get_property('temperature_degree_celsius'),
                                                endtemp_degree=node_from.get_property('endtemp_degree'))
                        try:
                            node_from.create_property('line_index', line_index)
                        except errors.NodePropertyError:
                            node_from.set_property('line_index', line_index, push_undo=False)
                        # print(self.net.line)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='LineNode.LineNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==1:
                    list_of_connected_nodes = list(outputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_to = n.get_property('bus_index')
                    bus_index_from = node_from.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        line_index = pp.create_line_from_parameters(self.net, from_bus=bus_index_from,
                                                to_bus=bus_index_to,
                                                length_km=node_to.get_property('length_km'),
                                                parallel=node_to.get_property('parallel'),
                                                df=node_to.get_property('df'),
                                                r_ohm_per_km=node_to.get_property('r_ohm_per_km'),
                                                x_ohm_per_km=node_to.get_property('x_ohm_per_km'),
                                                c_nf_per_km=node_to.get_property('c_nf_per_km'),
                                                max_i_ka=node_to.get_property('max_i_ka'),
                                                name=node_to.name(),
                                                in_service=not node_to.disabled(),
                                                g_us_per_km=node_to.get_property('g_us_per_km'),
                                                r0_ohm_per_km=node_to.get_property('r0_ohm_per_km'),
                                                x0_ohm_per_km=node_to.get_property('x0_ohm_per_km'),
                                                c0_nf_per_km=node_to.get_property('c0_nf_per_km'),
                                                g0_us_per_km=node_to.get_property('g0_us_per_km'),
                                                max_loading_percent=node_to.get_property('max_loading_percent'),
                                                alpha=node_to.get_property('alpha'),
                                                temperature_degree_celsius=node_to.get_property('temperature_degree_celsius'),
                                                endtemp_degree=node_to.get_property('endtemp_degree'))
                        try:
                            node_to.create_property('line_index', line_index)
                        except errors.NodePropertyError:
                            node_to.set_property('line_index', line_index, push_undo=False)
                        # print(self.net.line)


            # Adding standard line to pandapower network
            if node_from.type_=='StdLineNode.StdLineNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_from = n.get_property('bus_index')
                    bus_index_to = node_to.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        line_index = pp.create_line(self.net, from_bus=bus_index_from,
                                        to_bus=bus_index_to,
                                        length_km=node_from.get_property('length_km'),
                                        std_type=node_from.get_property('std_type'),
                                        name=node_from.name(),
                                        in_service=not node_from.disabled(),
                                        parallel=node_from.get_property('parallel'),
                                        df=node_from.get_property('df'),
                                        max_loading_percent=node_from.get_property('max_loading_percent'))
                        try:
                            node_from.create_property('line_index', line_index)
                        except errors.NodePropertyError:
                            node_from.set_property('line_index', line_index, push_undo=False)
                        # print(self.net.line)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='StdLineNode.StdLineNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==1:
                    list_of_connected_nodes = list(outputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_to = n.get_property('bus_index')
                    bus_index_from = node_from.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        line_index = pp.create_line(self.net, from_bus=bus_index_from,
                                        to_bus=bus_index_to,
                                        length_km=node_to.get_property('length_km'),
                                        std_type=node_to.get_property('std_type'),
                                        name=node_to.name(),
                                        in_service=not node_to.disabled(),
                                        parallel=node_to.get_property('parallel'),
                                        df=node_to.get_property('df'),
                                        max_loading_percent=node_to.get_property('max_loading_percent'))
                        try:
                            node_to.create_property('line_index', line_index)
                        except errors.NodePropertyError:
                            node_to.set_property('line_index', line_index, push_undo=False)
                        # print(self.net.line)


            # Adding DC line to pandapower network
            if node_from.type_=='DCLineNode.DCLineNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_from = n.get_property('bus_index')
                    bus_index_to = node_to.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        line_index = pp.create_dcline(self.net, from_bus=bus_index_from,
                                        to_bus=bus_index_to,
                                        p_mw=node_from.get_property('p_mw'),
                                        loss_percent=node_from.get_property('loss_percent'),
                                        loss_mw=node_from.get_property('loss_mw'),
                                        vm_from_pu=node_from.get_property('vm_from_pu'),
                                        vm_to_pu=node_from.get_property('vm_to_pu'),
                                        name=node_from.name(),
                                        in_service=not node_from.disabled(),
                                        max_p_mw=node_from.get_property('max_p_mw'),
                                        min_q_from_mvar=node_from.get_property('min_q_from_mvar'),
                                        min_q_to_mvar=node_from.get_property('min_q_to_mvar'),
                                        max_q_from_mvar=node_from.get_property('max_q_from_mvar'),
                                        max_q_to_mvar=node_from.get_property('max_q_to_mvar'))
                        try:
                            node_from.create_property('line_index', line_index)
                        except errors.NodePropertyError:
                            node_from.set_property('line_index', line_index, push_undo=False)
                        # print(self.net.dcline)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='DCLineNode.DCLineNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==1:
                    list_of_connected_nodes = list(outputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_to = n.get_property('bus_index')
                    bus_index_from = node_from.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        line_index = pp.create_dcline(self.net, from_bus=bus_index_from,
                                        to_bus=bus_index_to,
                                        p_mw=node_to.get_property('p_mw'),
                                        loss_percent=node_to.get_property('loss_percent'),
                                        loss_mw=node_to.get_property('loss_mw'),
                                        vm_from_pu=node_to.get_property('vm_from_pu'),
                                        vm_to_pu=node_to.get_property('vm_to_pu'),
                                        name=node_to.name(),
                                        in_service=not node_to.disabled(),
                                        max_p_mw=node_to.get_property('max_p_mw'),
                                        min_q_from_mvar=node_to.get_property('min_q_from_mvar'),
                                        min_q_to_mvar=node_to.get_property('min_q_to_mvar'),
                                        max_q_from_mvar=node_to.get_property('max_q_from_mvar'),
                                        max_q_to_mvar=node_to.get_property('max_q_to_mvar'))
                        try:
                            node_to.create_property('line_index', line_index)
                        except errors.NodePropertyError:
                            node_to.set_property('line_index', line_index, push_undo=False)
                        # print(self.net.dcline)


            # Adding impedance to pandapower network
            if node_from.type_=='ImpedanceNode.ImpedanceNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_from = n.get_property('bus_index')
                    bus_index_to = node_to.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        impedance_index = pp.create_impedance(self.net, from_bus=bus_index_from,
                                                to_bus=bus_index_to,
                                                rft_pu=node_from.get_property('rft_pu'),
                                                xft_pu=node_from.get_property('xft_pu'),
                                                sn_mva=node_from.get_property('sn_mva'),
                                                rtf_pu=node_from.get_property('rtf_pu'),
                                                xtf_pu=node_from.get_property('xtf_pu'),
                                                name=node_from.name(),
                                                in_service=not node_from.disabled(),
                                                rft0_pu=node_from.get_property('rft0_pu'),
                                                xft0_pu=node_from.get_property('xft0_pu'),
                                                rtf0_pu=node_from.get_property('rtf0_pu'),
                                                xtf0_pu=node_from.get_property('xtf0_pu'))
                        try:
                            node_from.create_property('impedance_index', impedance_index)
                        except errors.NodePropertyError:
                            node_from.set_property('impedance_index', impedance_index, push_undo=False)
                        # print(self.net.impedance)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='ImpedanceNode.ImpedanceNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==1:
                    list_of_connected_nodes = list(outputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_to = n.get_property('bus_index')
                    bus_index_from = node_from.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        impedance_index = pp.create_impedance(self.net, from_bus=bus_index_from,
                                                to_bus=bus_index_to,
                                                rft_pu=node_to.get_property('rft_pu'),
                                                xft_pu=node_to.get_property('xft_pu'),
                                                sn_mva=node_to.get_property('sn_mva'),
                                                rtf_pu=node_to.get_property('rtf_pu'),
                                                xtf_pu=node_to.get_property('xtf_pu'),
                                                name=node_to.name(),
                                                in_service=not node_to.disabled(),
                                                rft0_pu=node_to.get_property('rft0_pu'),
                                                xft0_pu=node_to.get_property('xft0_pu'),
                                                rtf0_pu=node_to.get_property('rtf0_pu'),
                                                xtf0_pu=node_to.get_property('xtf0_pu'))
                        try:
                            node_to.create_property('impedance_index', impedance_index)
                        except errors.NodePropertyError:
                            node_to.set_property('impedance_index', impedance_index, push_undo=False)
                        # print(self.net.impedance)


            # Adding 2w-transformer to pandapower network
            if node_from.type_=='TrafoNode.TrafoNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_from = n.get_property('bus_index')
                    bus_index_to = node_to.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        transformer_index = pp.create_transformer_from_parameters(self.net,
                                                hv_bus=bus_index_from,
                                                lv_bus=bus_index_to,
                                                sn_mva=node_from.get_property('sn_mva'),
                                                vn_hv_kv=node_from.get_property('vn_hv_kv'),
                                                vn_lv_kv=node_from.get_property('vn_lv_kv'),
                                                vkr_percent=node_from.get_property('vkr_percent'),
                                                vk_percent=node_from.get_property('vk_percent'),
                                                pfe_kw=node_from.get_property('pfe_kw'),
                                                i0_percent=node_from.get_property('i0_percent'),
                                                shift_degree=node_from.get_property('shift_degree'),
                                                tap_side=node_from.get_property('tap_side'),
                                                tap_neutral=node_from.get_property('tap_neutral'),
                                                tap_max=node_from.get_property('tap_max'),
                                                tap_min=node_from.get_property('tap_min'),
                                                tap_step_percent=node_from.get_property('tap_step_percent'),
                                                tap_step_degree=node_from.get_property('tap_step_degree'),
                                                tap_pos=node_from.get_property('tap_pos'),
                                                tap_phase_shifter=node_from.get_property('tap_phase_shifter'),
                                                in_service=not node_from.disabled(),
                                                name=node_from.name(),
                                                vector_group=node_from.get_property('vector_group'),
                                                max_loading_percent=node_from.get_property('max_loading_percent'),
                                                parallel=node_from.get_property('parallel'),
                                                df=node_from.get_property('df'),
                                                vk0_percent=node_from.get_property('vk0_percent'),
                                                vkr0_percent=node_from.get_property('vkr0_percent'),
                                                mag0_percent=node_from.get_property('mag0_percent'),
                                                mag0_rx=node_from.get_property('mag0_rx'),
                                                si0_hv_partial=node_from.get_property('si0_hv_partial'),
                                                oltc=node_from.get_property('oltc'),
                                                xn_ohm=node_from.get_property('xn_ohm'))
                        try:
                            node_from.create_property('transformer_index', transformer_index)
                        except errors.NodePropertyError:
                            node_from.set_property('transformer_index', transformer_index, push_undo=False)
                        # print(self.net.trafo)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='TrafoNode.TrafoNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==1:
                    list_of_connected_nodes = list(outputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_to = n.get_property('bus_index')
                    bus_index_from = node_from.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        transformer_index = pp.create_transformer_from_parameters(self.net,
                                                hv_bus=bus_index_from,
                                                lv_bus=bus_index_to,
                                                sn_mva=node_to.get_property('sn_mva'),
                                                vn_hv_kv=node_to.get_property('vn_hv_kv'),
                                                vn_lv_kv=node_to.get_property('vn_lv_kv'),
                                                vkr_percent=node_to.get_property('vkr_percent'),
                                                vk_percent=node_to.get_property('vk_percent'),
                                                pfe_kw=node_to.get_property('pfe_kw'),
                                                i0_percent=node_to.get_property('i0_percent'),
                                                shift_degree=node_to.get_property('shift_degree'),
                                                tap_side=node_to.get_property('tap_side'),
                                                tap_neutral=node_to.get_property('tap_neutral'),
                                                tap_max=node_to.get_property('tap_max'),
                                                tap_min=node_to.get_property('tap_min'),
                                                tap_step_percent=node_to.get_property('tap_step_percent'),
                                                tap_step_degree=node_to.get_property('tap_step_degree'),
                                                tap_pos=node_to.get_property('tap_pos'),
                                                tap_phase_shifter=node_to.get_property('tap_phase_shifter'),
                                                in_service=not node_to.disabled(),
                                                name=node_to.name(),
                                                vector_group=node_to.get_property('vector_group'),
                                                max_loading_percent=node_to.get_property('max_loading_percent'),
                                                parallel=node_to.get_property('parallel'),
                                                df=node_to.get_property('df'),
                                                vk0_percent=node_to.get_property('vk0_percent'),
                                                vkr0_percent=node_to.get_property('vkr0_percent'),
                                                mag0_percent=node_to.get_property('mag0_percent'),
                                                mag0_rx=node_to.get_property('mag0_rx'),
                                                si0_hv_partial=node_to.get_property('si0_hv_partial'),
                                                oltc=node_to.get_property('oltc'),
                                                xn_ohm=node_to.get_property('xn_ohm'))
                        try:
                            node_to.create_property('transformer_index', transformer_index)
                        except errors.NodePropertyError:
                            node_to.set_property('transformer_index', transformer_index, push_undo=False)
                        # print(self.net.trafo)


            # Adding standard standard 2w-transformer to pandapower network
            if node_from.type_=='StdTrafoNode.StdTrafoNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_from = n.get_property('bus_index')
                    bus_index_to = node_to.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        transformer_index = pp.create_transformer(self.net,
                                                hv_bus=bus_index_from,
                                                lv_bus=bus_index_to,
                                                std_type=node_from.get_property('std_type'),
                                                tap_pos=node_from.get_property('tap_pos'),
                                                in_service=not node_from.disabled(),
                                                name=node_from.name(),
                                                max_loading_percent=node_from.get_property('max_loading_percent'),
                                                parallel=node_from.get_property('parallel'),
                                                df=node_from.get_property('df'),
                                                vk0_percent=node_from.get_property('vk0_percent'),
                                                vkr0_percent=node_from.get_property('vkr0_percent'),
                                                mag0_percent=node_from.get_property('mag0_percent'),
                                                mag0_rx=node_from.get_property('mag0_rx'),
                                                si0_hv_partial=node_from.get_property('si0_hv_partial'),
                                                xn_ohm=node_from.get_property('xn_ohm'))
                        try:
                            node_from.create_property('transformer_index', transformer_index)
                        except errors.NodePropertyError:
                            node_from.set_property('transformer_index', transformer_index)
                        # print(self.net.trafo)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='StdTrafoNode.StdTrafoNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==1:
                    list_of_connected_nodes = list(outputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    bus_index_to = n.get_property('bus_index')
                    bus_index_from = node_from.get_property('bus_index')
                    if type_=='BusNode.BusNode':
                        transformer_index = pp.create_transformer(self.net,
                                                hv_bus=bus_index_from,
                                                lv_bus=bus_index_to,
                                                std_type=node_to.get_property('std_type'),
                                                tap_pos=node_to.get_property('tap_pos'),
                                                in_service=not node_to.disabled(),
                                                name=node_to.name(),
                                                max_loading_percent=node_to.get_property('max_loading_percent'),
                                                parallel=node_to.get_property('parallel'),
                                                df=node_to.get_property('df'),
                                                vk0_percent=node_to.get_property('vk0_percent'),
                                                vkr0_percent=node_to.get_property('vkr0_percent'),
                                                mag0_percent=node_to.get_property('mag0_percent'),
                                                mag0_rx=node_to.get_property('mag0_rx'),
                                                si0_hv_partial=node_to.get_property('si0_hv_partial'),
                                                xn_ohm=node_to.get_property('xn_ohm'))
                        try:
                            node_to.create_property('transformer_index', transformer_index)
                        except errors.NodePropertyError:
                            node_to.set_property('transformer_index', transformer_index)
                        # print(self.net.trafo)


            # Adding 3w-transformer to pandapower network
            if node_from.type_=='Trafo3wNode.Trafo3wNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    if type_=='BusNode.BusNode' and node_from.connected_to_network():
                        outputs_connected = node_from.connected_output_nodes()
                        list_of_output_connected_nodes_mv = list(outputs_connected.values())[0]
                        list_of_output_connected_nodes_lv = list(outputs_connected.values())[1]
                        bus_index_hv = n.get_property('bus_index')
                        bus_index_mv = list_of_output_connected_nodes_mv[0].get_property('bus_index')
                        bus_index_lv = list_of_output_connected_nodes_lv[0].get_property('bus_index')
                        transformer_index = pp.create_transformer3w_from_parameters(self.net,
                                                hv_bus=bus_index_hv,
                                                mv_bus=bus_index_mv,
                                                lv_bus=bus_index_lv,
                                                sn_hv_mva=node_from.get_property('sn_hv_mva'),
                                                sn_mv_mva=node_from.get_property('sn_mv_mva'),
                                                sn_lv_mva=node_from.get_property('sn_lv_mva'),
                                                vn_hv_kv=node_from.get_property('vn_hv_kv'),
                                                vn_mv_kv=node_from.get_property('vn_hv_kv'),
                                                vn_lv_kv=node_from.get_property('vn_lv_kv'),
                                                vkr_hv_percent=node_from.get_property('vkr_hv_percent'),
                                                vkr_mv_percent=node_from.get_property('vkr_mv_percent'),
                                                vkr_lv_percent=node_from.get_property('vkr_lv_percent'),
                                                vk_hv_percent=node_from.get_property('vk_hv_percent'),
                                                vk_mv_percent=node_from.get_property('vk_mv_percent'),
                                                vk_lv_percent=node_from.get_property('vk_lv_percent'),
                                                pfe_kw=node_from.get_property('pfe_kw'),
                                                i0_percent=node_from.get_property('i0_percent'),
                                                shift_mv_degree=node_from.get_property('shift_mv_degree'),
                                                shift_lv_degree=node_from.get_property('shift_lv_degree'),
                                                tap_side=node_from.get_property('tap_side'),
                                                tap_neutral=node_from.get_property('tap_neutral'),
                                                tap_max=node_from.get_property('tap_max'),
                                                tap_min=node_from.get_property('tap_min'),
                                                tap_step_percent=node_from.get_property('tap_step_percent'),
                                                tap_step_degree=node_from.get_property('tap_step_degree'),
                                                tap_pos=node_from.get_property('tap_pos'),
                                                tap_at_star_point=(True if node_from.get_property('tap_at_star_point')=='True'
                                                                   else False),
                                                in_service=not node_from.disabled(),
                                                name=node_from.name(),
                                                vector_group=node_from.get_property('vector_group'),
                                                max_loading_percent=node_from.get_property('max_loading_percent'),
                                                vk0_hv_percent=node_from.get_property('vk0_hv_percent'),
                                                vk0_mv_percent=node_from.get_property('vk0_mv_percent'),
                                                vk0_lv_percent=node_from.get_property('vk0_lv_percent'),
                                                vkr0_hv_percent=node_from.get_property('vkr0_hv_percent'),
                                                vkr0_mv_percent=node_from.get_property('vkr0_mv_percent'),
                                                vkr0_lv_percent=node_from.get_property('vkr0_lv_percent'))
                        try:
                            node_from.create_property('transformer_index', transformer_index)
                        except errors.NodePropertyError:
                            node_from.set_property('transformer_index', transformer_index, push_undo=False)
                        # print(self.net.trafo3w)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='Trafo3wNode.Trafo3wNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==2:
                    if not node_to.connected_to_network():
                        return
                    list_of_output_connected_nodes_mv = list(outputs_connected.values())[0]
                    list_of_output_connected_nodes_lv = list(outputs_connected.values())[1]

                    bus_index_hv = node_from.get_property('bus_index')
                    bus_index_mv = list_of_output_connected_nodes_mv[0].get_property('bus_index')
                    bus_index_lv = list_of_output_connected_nodes_lv[0].get_property('bus_index')
                    transformer_index = pp.create_transformer3w_from_parameters(self.net,
                                            hv_bus=bus_index_hv,
                                            mv_bus=bus_index_mv,
                                            lv_bus=bus_index_lv,
                                            sn_hv_mva=node_to.get_property('sn_hv_mva'),
                                            sn_mv_mva=node_to.get_property('sn_mv_mva'),
                                            sn_lv_mva=node_to.get_property('sn_lv_mva'),
                                            vn_hv_kv=node_to.get_property('vn_hv_kv'),
                                            vn_mv_kv=node_to.get_property('vn_hv_kv'),
                                            vn_lv_kv=node_to.get_property('vn_lv_kv'),
                                            vkr_hv_percent=node_to.get_property('vkr_hv_percent'),
                                            vkr_mv_percent=node_to.get_property('vkr_mv_percent'),
                                            vkr_lv_percent=node_to.get_property('vkr_lv_percent'),
                                            vk_hv_percent=node_to.get_property('vk_hv_percent'),
                                            vk_mv_percent=node_to.get_property('vk_mv_percent'),
                                            vk_lv_percent=node_to.get_property('vk_lv_percent'),
                                            pfe_kw=node_to.get_property('pfe_kw'),
                                            i0_percent=node_to.get_property('i0_percent'),
                                            shift_mv_degree=node_to.get_property('shift_mv_degree'),
                                            shift_lv_degree=node_to.get_property('shift_lv_degree'),
                                            tap_side=node_to.get_property('tap_side'),
                                            tap_neutral=node_to.get_property('tap_neutral'),
                                            tap_max=node_to.get_property('tap_max'),
                                            tap_min=node_to.get_property('tap_min'),
                                            tap_step_percent=node_to.get_property('tap_step_percent'),
                                            tap_step_degree=node_to.get_property('tap_step_degree'),
                                            tap_pos=node_to.get_property('tap_pos'),
                                            tap_at_star_point=(True if node_to.get_property('tap_at_star_point')=='True'
                                                               else False),
                                            in_service=not node_to.disabled(),
                                            name=node_to.name(),
                                            vector_group=node_to.get_property('vector_group'),
                                            max_loading_percent=node_to.get_property('max_loading_percent'),
                                            vk0_hv_percent=node_to.get_property('vk0_hv_percent'),
                                            vk0_mv_percent=node_to.get_property('vk0_mv_percent'),
                                            vk0_lv_percent=node_to.get_property('vk0_lv_percent'),
                                            vkr0_hv_percent=node_to.get_property('vkr0_hv_percent'),
                                            vkr0_mv_percent=node_to.get_property('vkr0_mv_percent'),
                                            vkr0_lv_percent=node_to.get_property('vkr0_lv_percent'))
                    try:
                        node_to.create_property('transformer_index', transformer_index)
                    except errors.NodePropertyError:
                        node_to.set_property('transformer_index', transformer_index, push_undo=False)
                    # print(self.net.trafo3w)


            # Adding standard 3w-transformer to pandapower network
            if node_from.type_=='StdTrafo3wNode.StdTrafo3wNode' and node_to.type_=='BusNode.BusNode':
                inputs_connected = node_from.connected_input_nodes()
                # print(inputs_connected)
                if len(inputs_connected)==1:
                    list_of_connected_nodes = list(inputs_connected.values())[0]
                    if not list_of_connected_nodes:
                        return
                    n = list_of_connected_nodes[0]
                    type_ = n.type_
                    if type_=='BusNode.BusNode' and node_from.connected_to_network():
                        outputs_connected = node_from.connected_output_nodes()
                        list_of_output_connected_nodes_mv = list(outputs_connected.values())[0]
                        list_of_output_connected_nodes_lv = list(outputs_connected.values())[1]
                        bus_index_hv = n.get_property('bus_index')
                        bus_index_mv = list_of_output_connected_nodes_mv[0].get_property('bus_index')
                        bus_index_lv = list_of_output_connected_nodes_lv[0].get_property('bus_index')
                        transformer_index = pp.create_transformer3w(self.net,
                                                hv_bus=bus_index_hv,
                                                mv_bus=bus_index_mv,
                                                lv_bus=bus_index_lv,
                                                std_type=node_from.get_property('std_type'),
                                                tap_pos=node_from.get_property('tap_pos'),
                                                tap_at_star_point=(True if node_from.get_property('tap_at_star_point')=='True'
                                                                   else False),
                                                in_service=not node_from.disabled(),
                                                name=node_from.name(),
                                                max_loading_percent=node_from.get_property('max_loading_percent'))
                        try:
                            node_from.create_property('transformer_index', transformer_index)
                        except errors.NodePropertyError:
                            node_from.set_property('transformer_index', transformer_index, push_undo=False)
                        # print(self.net.trafo3w)

            elif node_from.type_=='BusNode.BusNode' and node_to.type_=='StdTrafo3wNode.StdTrafo3wNode':
                outputs_connected = node_to.connected_output_nodes()
                if len(outputs_connected)==2:
                    if not node_to.connected_to_network():
                        return
                    list_of_output_connected_nodes_mv = list(outputs_connected.values())[0]
                    list_of_output_connected_nodes_lv = list(outputs_connected.values())[1]

                    bus_index_hv = node_from.get_property('bus_index')
                    bus_index_mv = list_of_output_connected_nodes_mv[0].get_property('bus_index')
                    bus_index_lv = list_of_output_connected_nodes_lv[0].get_property('bus_index')
                    transformer_index = pp.create_transformer3w(self.net,
                                            hv_bus=bus_index_hv,
                                            mv_bus=bus_index_mv,
                                            lv_bus=bus_index_lv,
                                            std_type=node_to.get_property('std_type'),
                                            tap_pos=node_to.get_property('tap_pos'),
                                            tap_at_star_point=(True if node_to.get_property('tap_at_star_point')=='True'
                                                                else False),
                                            in_service=not node_to.disabled(),
                                            name=node_to.name(),
                                            max_loading_percent=node_to.get_property('max_loading_percent'))
                    try:
                        node_to.create_property('transformer_index', transformer_index)
                    except errors.NodePropertyError:
                        node_to.set_property('transformer_index', transformer_index, push_undo=False)
                    # print(self.net.trafo3w)


            # Adding a generator to pandapower network
            if node_to.type_=='GenNode.GenNode' and node_from.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_from.type_=='GenNode.GenNode' and node_to.type_=='BusNode.BusNode':
                bus = node_to.get_property('bus_index')
                gen_index = pp.create_gen(self.net, bus=bus,
                                          p_mw=node_from.get_property('p_mw'),
                                          vm_pu=node_from.get_property('vm_pu'),
                                          sn_mva=node_from.get_property('sn_mva'),
                                          scaling=node_from.get_property('scaling'),
                                          slack_weight=node_from.get_property('slack_weight'),
                                          vn_kv=node_from.get_property('vn_kv'),
                                          xdss_pu=node_from.get_property('xdss_pu'),
                                          rdss_ohm=node_from.get_property('rdss_ohm'),
                                          cos_phi=node_from.get_property('cos_phi'),
                                          controllable=node_from.get_property('controllable'),
                                          name=node_from.name(),
                                          in_service=not node_from.disabled(),
                                          max_p_mw=node_from.get_property('max_p_mw'),
                                          min_p_mw=node_from.get_property('min_p_mw'),
                                          max_q_mvar=node_from.get_property('max_q_mvar'),
                                          min_q_mvar=node_from.get_property('min_q_mvar'),
                                          min_vm_pu=node_from.get_property('min_vm_pu'),
                                          max_vm_pu=node_from.get_property('max_vm_pu'))
                try:
                    node_from.create_property('gen_index', gen_index)
                except errors.NodePropertyError:
                    node_from.set_property('gen_index', gen_index, push_undo=False)


            # Adding a static generator to pandapower network
            if node_to.type_=='SGenNode.SGenNode' and node_from.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_from.type_=='SGenNode.SGenNode' and node_to.type_=='BusNode.BusNode':
                # print(node_from.connected_output_nodes())
                bus = node_to.get_property('bus_index')
                gen_type = node_from.get_property('generator_type')
                gen_index = pp.create_sgen(self.net, bus=bus,
                                           p_mw=node_from.get_property('p_mw'),
                                           q_mvar=node_from.get_property('q_mvar'),
                                           sn_mva=node_from.get_property('sn_mva'),
                                           scaling=node_from.get_property('scaling'),
                                           type=node_from.get_property('type'),
                                           kappa=node_from.get_property('k'),
                                           rx=node_from.get_property('rx'),
                                           generator_type=(None if gen_type=='None' else gen_type),
                                           lrc_pu=node_from.get_property('lrc_pu'),
                                           max_ik_ka=node_from.get_property('max_ik_ka'),
                                           controllable=node_from.get_property('controllable'),
                                           name=node_from.name(),
                                           in_service=not node_from.disabled(),
                                           max_p_mw=node_from.get_property('max_p_mw'),
                                           min_p_mw=node_from.get_property('min_p_mw'),
                                           max_q_mvar=node_from.get_property('max_q_mvar'),
                                           min_q_mvar=node_from.get_property('min_q_mvar'),
                                           current_source=node_from.get_property('current_source'),
                                           max_vm_pu=node_from.get_property('max_vm_pu'))
                try:
                    node_from.create_property('gen_index', gen_index)
                except errors.NodePropertyError:
                    node_from.set_property('gen_index', gen_index, push_undo=False)
                # print(self.net.sgen)


            # Adding an asymmetric static generator to pandapower network
            if node_to.type_=='ASGenNode.ASGenNode' and node_from.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_from.type_=='ASGenNode.ASGenNode' and node_to.type_=='BusNode.BusNode':
                # print(node_from.connected_output_nodes())
                bus = node_to.get_property('bus_index')
                gen_index = pp.create_asymmetric_sgen(self.net, bus=bus,
                                        p_a_mw=node_from.get_property('p_a_mw'),
                                        q_a_mvar=node_from.get_property('q_a_mvar'),
                                        p_b_mw=node_from.get_property('p_b_mw'),
                                        q_b_mvar=node_from.get_property('q_b_mvar'),
                                        p_c_mw=node_from.get_property('p_c_mw'),
                                        q_c_mvar=node_from.get_property('q_c_mvar'),
                                        sn_mva=node_from.get_property('sn_mva'),
                                        scaling=node_from.get_property('scaling'),
                                        type=node_from.get_property('type'),
                                        name=node_from.name(),
                                        in_service=not node_from.disabled())
                try:
                    node_from.create_property('gen_index', gen_index)
                except errors.NodePropertyError:
                    node_from.set_property('gen_index', gen_index, push_undo=False)
                # print(self.net.asymmetric_sgen)


            # Adding an external grid to pandapower network
            if node_to.type_=='ExtGridNode.ExtGridNode' and node_from.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_from.type_=='ExtGridNode.ExtGridNode' and node_to.type_=='BusNode.BusNode':
                # print(node_from.connected_output_nodes())
                bus = node_to.get_property('bus_index')
                grid_index = pp.create_ext_grid(self.net, bus=bus,
                                vm_pu=node_from.get_property('vm_pu'),
                                va_degree=node_from.get_property('va_degree'),
                                s_sc_max_mva=node_from.get_property('s_sc_max_mva'),
                                s_sc_min_mva=node_from.get_property('s_sc_min_mva'),
                                slack_weight=node_from.get_property('slack_weight'),
                                rx_max=node_from.get_property('rx_max'),
                                rx_min=node_from.get_property('rx_min'),
                                r0x0_max=node_from.get_property('r0x0_max'),
                                x0x_max=node_from.get_property('x0x_max'),
                                controllable=node_from.get_property('controllable'),
                                name=node_from.name(),
                                in_service=not node_from.disabled(),
                                max_p_mw=node_from.get_property('max_p_mw'),
                                min_p_mw=node_from.get_property('min_p_mw'),
                                max_q_mvar=node_from.get_property('max_q_mvar'),
                                min_q_mvar=node_from.get_property('min_q_mvar'))
                try:
                    node_from.create_property('grid_index', grid_index)
                except errors.NodePropertyError:
                    node_from.set_property('grid_index', grid_index, push_undo=False)
                # print(self.net.ext_grid)


            # Adding a symmetric load to pandapower network
            if node_from.type_=='LoadNode.LoadNode' and node_to.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_to.type_=='LoadNode.LoadNode' and node_from.type_=='BusNode.BusNode':
                # print(node_to.connected_input_nodes())
                bus = node_from.get_property('bus_index')
                load_index = pp.create_load(self.net, bus=bus,
                                p_mw=node_to.get_property('p_mw'),
                                q_mvar=node_to.get_property('q_mvar'),
                                const_z_percent=node_to.get_property('const_z_percent'),
                                const_i_percent=node_to.get_property('const_i_percent'),
                                sn_mva=node_to.get_property('sn_mva'),
                                scaling=node_to.get_property('scaling'),
                                type=node_to.get_property('type'),
                                controllable=node_to.get_property('controllable'),
                                name=node_to.name(),
                                in_service=not node_to.disabled(),
                                max_p_mw=node_to.get_property('max_p_mw'),
                                min_p_mw=node_to.get_property('min_p_mw'),
                                max_q_mvar=node_to.get_property('max_q_mvar'),
                                min_q_mvar=node_to.get_property('min_q_mvar'))
                try:
                    node_to.create_property('load_index', load_index)
                except errors.NodePropertyError:
                    node_to.set_property('load_index', load_index, push_undo=False)
                # print(self.net.load)


            # Adding an asymmetric load to pandapower network
            if node_from.type_=='ALoadNode.ALoadNode' and node_to.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_to.type_=='ALoadNode.ALoadNode' and node_from.type_=='BusNode.BusNode':
                # print(node_to.connected_input_nodes())
                bus = node_from.get_property('bus_index')
                load_index = pp.create_asymmetric_load(self.net, bus=bus,
                                p_a_mw=node_to.get_property('p_a_mw'),
                                q_a_mvar=node_to.get_property('q_a_mvar'),
                                p_b_mw=node_to.get_property('p_b_mw'),
                                q_b_mvar=node_to.get_property('q_b_mvar'),
                                p_c_mw=node_to.get_property('p_c_mw'),
                                q_c_mvar=node_to.get_property('q_c_mvar'),
                                sn_mva=node_to.get_property('sn_mva'),
                                scaling=node_to.get_property('scaling'),
                                type=node_to.get_property('type'),
                                name=node_to.name(),
                                in_service=not node_to.disabled())
                try:
                    node_to.create_property('load_index', load_index)
                except errors.NodePropertyError:
                    node_to.set_property('load_index', load_index, push_undo=False)
                # print(self.net.asymmetric_load)


            # Adding a shunt element to pandapower network
            if node_from.type_=='ShuntNode.ShuntNode' and node_to.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_to.type_=='ShuntNode.ShuntNode' and node_from.type_=='BusNode.BusNode':
                # print(node_to.connected_input_nodes())
                bus = node_from.get_property('bus_index')
                shunt_index = pp.create_shunt(self.net, bus=bus,
                                p_mw=node_to.get_property('p_mw'),
                                q_mvar=node_to.get_property('q_mvar'),
                                vn_kv=node_to.get_property('vn_kv'),
                                step=node_to.get_property('step'),
                                max_step=node_to.get_property('max_step'),
                                name=node_to.name(),
                                in_service=not node_to.disabled())
                try:
                    node_to.create_property('shunt_index', shunt_index)
                except errors.NodePropertyError:
                    node_to.set_property('shunt_index', shunt_index, push_undo=False)
                # print(self.net.shunt)


            # Adding a motor to pandapower network
            if node_from.type_=='MotorNode.MotorNode' and node_to.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_to.type_=='MotorNode.MotorNode' and node_from.type_=='BusNode.BusNode':
                # print(node_to.connected_input_nodes())
                bus = node_from.get_property('bus_index')
                motor_index = pp.create_motor(self.net, bus=bus,
                                pn_mech_mw=node_to.get_property('pn_mech_mw'),
                                cos_phi=node_to.get_property('cos_phi'),
                                efficiency_percent=node_to.get_property('efficiency_percent'),
                                scaling=node_to.get_property('scaling'),
                                efficiency_n_percent=node_to.get_property('efficiency_n_percent'),
                                cos_phi_n=node_to.get_property('cos_phi_n'),
                                vn_kv=node_to.get_property('vn_kv'),
                                lrc_pu=node_to.get_property('lrc_pu'),
                                rx=node_to.get_property('rx'),
                                name=node_to.name(),
                                in_service=not node_to.disabled())
                try:
                    node_to.create_property('motor_index', motor_index)
                except errors.NodePropertyError:
                    node_to.set_property('motor_index', motor_index, push_undo=False)
                # print(self.net.motor)


            # Adding a ward to pandapower network
            if node_from.type_=='WardNode.WardNode' and node_to.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_to.type_=='WardNode.WardNode' and node_from.type_=='BusNode.BusNode':
                # print(node_to.connected_input_nodes())
                bus = node_from.get_property('bus_index')
                ward_index = pp.create_ward(self.net, bus=bus,
                                ps_mw=node_to.get_property('ps_mw'),
                                qs_mvar=node_to.get_property('qs_mvar'),
                                pz_mw=node_to.get_property('pz_mw'),
                                qz_mvar=node_to.get_property('qz_mvar'),
                                name=node_to.name(),
                                in_service=not node_to.disabled())
                try:
                    node_to.create_property('ward_index', ward_index)
                except errors.NodePropertyError:
                    node_to.set_property('ward_index', ward_index, push_undo=False)
                # print(self.net.ward)


            # Adding an extended ward to pandapower network
            if node_from.type_=='XWardNode.XWardNode' and node_to.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_to.type_=='XWardNode.XWardNode' and node_from.type_=='BusNode.BusNode':
                # print(node_to.connected_input_nodes())
                bus = node_from.get_property('bus_index')
                ward_index = pp.create_xward(self.net, bus=bus,
                                ps_mw=node_to.get_property('ps_mw'),
                                qs_mvar=node_to.get_property('qs_mvar'),
                                pz_mw=node_to.get_property('pz_mw'),
                                qz_mvar=node_to.get_property('qz_mvar'),
                                r_ohm=node_to.get_property('r_ohm'),
                                x_ohm=node_to.get_property('x_ohm'),
                                vm_pu=node_to.get_property('vm_pu'),
                                slack_weight=node_to.get_property('slack_weight'),
                                name=node_to.name(),
                                in_service=not node_to.disabled())
                try:
                    node_to.create_property('ward_index', ward_index)
                except errors.NodePropertyError:
                    node_to.set_property('ward_index', ward_index, push_undo=False)
                # print(self.net.xward)

            
            # Adding a storage to pandapower network
            if node_from.type_=='StorageNode.StorageNode' and node_to.type_=='BusNode.BusNode':
                node_from_copy = node_from
                node_to_copy = node_to
                node_from = node_to_copy
                node_to = node_from_copy
            if node_to.type_=='StorageNode.StorageNode' and node_from.type_=='BusNode.BusNode':
                # print(node_to.connected_input_nodes())
                bus = node_from.get_property('bus_index')
                storage_index = pp.create_storage(self.net, bus=bus,
                                    p_mw=node_to.get_property('p_mw'),
                                    q_mvar=node_to.get_property('q_mvar'),
                                    sn_mva=node_to.get_property('sn_mva'),
                                    scaling=node_to.get_property('scaling'),
                                    max_e_mwh=node_to.get_property('max_e_mwh'),
                                    min_e_mwh=node_to.get_property('min_e_mwh'),
                                    soc_percent=node_to.get_property('soc_percent'),
                                    max_p_mw=node_to.get_property('max_p_mw'),
                                    min_p_mw=node_to.get_property('min_p_mw'),
                                    max_q_mvar=node_to.get_property('max_q_mvar'),
                                    min_q_mvar=node_to.get_property('min_q_mvar'),
                                    controllable=node_to.get_property('controllable'),
                                    type=node_to.get_property('type'),
                                    name=node_to.name(),
                                    in_service=not node_to.disabled())
                try:
                    node_to.create_property('storage_index', storage_index)
                except errors.NodePropertyError:
                    node_to.set_property('storage_index', storage_index, push_undo=False)
                # print(self.net.storage)
            
    def open_options_dialog(self, node):
        """
        Executed function when a node is double clicked.
        """
        if node.type_=='BusNode.BusNode':
            self.bus_options(node)
        elif node.type_=='LineNode.LineNode':
            self.line_options(node)
        elif node.type_=='StdLineNode.StdLineNode':
            self.stdline_options(node)
        elif node.type_=='DCLineNode.DCLineNode':
            self.dcline_options(node)
        elif node.type_=='ImpedanceNode.ImpedanceNode':
            self.impedance_options(node)
        elif node.type_=='TrafoNode.TrafoNode':
            self.transformer_options(node)
        elif node.type_=='StdTrafoNode.StdTrafoNode':
            self.stdtransformer_options(node)
        elif node.type_=='Trafo3wNode.Trafo3wNode':
            self.transformer3w_options(node)
        elif node.type_=='StdTrafo3wNode.StdTrafo3wNode':
            self.stdtransformer3w_options(node)
        elif node.type_=='GenNode.GenNode':
            self.gen_options(node)
        elif node.type_=='SGenNode.SGenNode':
            self.sgen_options(node)
        elif node.type_=='ASGenNode.ASGenNode':
            self.asgen_options(node)
        elif node.type_=='ExtGridNode.ExtGridNode':
            self.ext_grid_options(node)
        elif node.type_=='LoadNode.LoadNode':
            self.load_options(node)
        elif node.type_=='ALoadNode.ALoadNode':
            self.aload_options(node)
        elif node.type_=='ShuntNode.ShuntNode':
            self.shunt_options(node)
        elif node.type_=='MotorNode.MotorNode':
            self.motor_options(node)
        elif node.type_=='WardNode.WardNode':
            self.ward_options(node)
        elif node.type_=='XWardNode.XWardNode':
            self.xward_options(node)
        elif node.type_=='StorageNode.StorageNode':
            self.storage_options(node)
        elif node.type_=='SwitchNode.SwitchNode':
            self.switch_options(node)

    def bus_options(self, node):
        """
        Executed function when a Bus node is double clicked.
        """
        bus_index = node.get_property('bus_index')
        if bus_index is not None:
            dialog = bus_dialog()
            dialog.setWindowTitle(node.get_property('name'))
            dialog.setWindowIcon(QtGui.QIcon(icon_path))
            dialog.vn_kv.setValue(self.net.bus.loc[bus_index, 'vn_kv'])
            dialog.max_vm_pu.setValue(self.net.bus.loc[bus_index, 'max_vm_pu'])
            dialog.min_vm_pu.setValue(self.net.bus.loc[bus_index, 'min_vm_pu'])

            if dialog.exec():
                self.net.bus.loc[bus_index, 'vn_kv'] = np.round(dialog.vn_kv.value(), 2)
                self.net.bus.loc[bus_index, 'max_vm_pu'] = np.round(dialog.max_vm_pu.value(), 2)
                self.net.bus.loc[bus_index, 'min_vm_pu'] = np.round(dialog.min_vm_pu.value(), 2)

                self.session_change_warning()

    def line_options(self, node):
        """
        Executed function when a Line node is double clicked.
        """
        dialog = line_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        dialog.length_km.setValue(node.get_property('length_km'))
        dialog.parallel.setValue(node.get_property('parallel'))
        dialog.df.setValue(node.get_property('df'))
        dialog.r_ohm_per_km.setValue(node.get_property('r_ohm_per_km'))
        dialog.x_ohm_per_km.setValue(node.get_property('x_ohm_per_km'))
        dialog.c_nf_per_km.setValue(node.get_property('c_nf_per_km'))
        dialog.g_us_per_km.setValue(node.get_property('g_us_per_km'))
        dialog.max_i_ka.setValue(node.get_property('max_i_ka'))
        dialog.r0_ohm_per_km.setValue(node.get_property('r0_ohm_per_km'))
        dialog.x0_ohm_per_km.setValue(node.get_property('x0_ohm_per_km'))
        dialog.c0_nf_per_km.setValue(node.get_property('c0_nf_per_km'))
        dialog.g0_us_per_km.setValue(node.get_property('g0_us_per_km'))
        dialog.max_loading_percent.setValue(node.get_property('max_loading_percent'))
        dialog.alpha.setValue(node.get_property('alpha'))
        dialog.temperature_degree_celsius.setValue(node.get_property('temperature_degree_celsius'))
        dialog.endtemp_degree.setValue(node.get_property('endtemp_degree'))

        if dialog.exec():
            node.set_property('length_km', dialog.length_km.value(), push_undo=False)
            node.set_property('parallel', int(dialog.parallel.value()), push_undo=False)
            node.set_property('df', dialog.df.value(), push_undo=False)
            node.set_property('r_ohm_per_km', dialog.r_ohm_per_km.value(), push_undo=False)
            node.set_property('x_ohm_per_km', dialog.x_ohm_per_km.value(), push_undo=False)
            node.set_property('c_nf_per_km', dialog.c_nf_per_km.value(), push_undo=False)
            node.set_property('g_us_per_km', dialog.g_us_per_km.value(), push_undo=False)
            node.set_property('max_i_ka', dialog.max_i_ka.value(), push_undo=False)
            node.set_property('r0_ohm_per_km', dialog.r0_ohm_per_km.value(), push_undo=False)
            node.set_property('x0_ohm_per_km', dialog.x0_ohm_per_km.value(), push_undo=False)
            node.set_property('c0_nf_per_km', dialog.c0_nf_per_km.value(), push_undo=False)
            node.set_property('g0_us_per_km', dialog.g0_us_per_km.value(), push_undo=False)
            node.set_property('max_loading_percent', dialog.max_loading_percent.value(), push_undo=False)
            node.set_property('alpha', dialog.alpha.value(), push_undo=False)
            node.set_property('temperature_degree_celsius', dialog.temperature_degree_celsius.value(), push_undo=False)
            node.set_property('endtemp_degree', dialog.endtemp_degree.value(), push_undo=False)

            line_index = node.get_property('line_index')
            if line_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    if name=='parallel':
                        self.net.line.loc[line_index, name] = int(node.get_property(name))
                    else:
                        self.net.line.loc[line_index, name] = np.round(node.get_property(name), 4)

            self.session_change_warning()

    def stdline_options(self, node):
        """
        Executed function when a Standard Line node is double clicked.
        """
        table = pp.available_std_types(self.net, 'line')
        selected_std = node.get_property('std_type')

        dialog = stdline_dialog(table, selected_std)
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        dialog.length_km.setValue(node.get_property('length_km'))
        dialog.parallel.setValue(node.get_property('parallel'))
        dialog.df.setValue(node.get_property('df'))
        dialog.max_loading_percent.setValue(node.get_property('max_loading_percent'))

        if dialog.exec():
            node.set_property('length_km', dialog.length_km.value(), push_undo=False)
            node.set_property('parallel', int(dialog.parallel.value()), push_undo=False)
            node.set_property('df', dialog.df.value(), push_undo=False)
            node.set_property('max_loading_percent', dialog.max_loading_percent.value(), push_undo=False)
            node.set_property('std_type', dialog.std_type.currentText(), push_undo=False)

            line_index = node.get_property('line_index')
            if line_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    if name=='parallel':
                        self.net.line.loc[line_index, name] = int(node.get_property(name))
                    elif name=='std_type':
                        pp.change_std_type(self.net, line_index,
                                           name=node.get_property(name),
                                           element='line')
                    else:
                        self.net.line.loc[line_index, name] = np.round(node.get_property(name), 2)

            self.session_change_warning()

    def dcline_options(self, node):
        """
        Executed function when a DC Line node is double clicked.
        """
        dialog = dcline_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        dialog.p_mw.setValue(node.get_property('p_mw'))
        dialog.loss_percent.setValue(node.get_property('loss_percent'))
        dialog.loss_mw.setValue(node.get_property('loss_mw'))
        dialog.vm_from_pu.setValue(node.get_property('vm_from_pu'))
        dialog.vm_to_pu.setValue(node.get_property('vm_to_pu'))
        dialog.max_p_mw.setValue(node.get_property('max_p_mw'))
        dialog.min_q_from_mvar.setValue(node.get_property('min_q_from_mvar'))
        dialog.min_q_to_mvar.setValue(node.get_property('min_q_to_mvar'))
        dialog.max_q_from_mvar.setValue(node.get_property('max_q_from_mvar'))
        dialog.max_q_to_mvar.setValue(node.get_property('max_q_to_mvar'))

        if dialog.exec():
            node.set_property('p_mw', dialog.p_mw.value(), push_undo=False)
            node.set_property('loss_percent', dialog.loss_percent.value(), push_undo=False)
            node.set_property('loss_mw', dialog.loss_mw.value(), push_undo=False)
            node.set_property('vm_from_pu', dialog.vm_from_pu.value(), push_undo=False)
            node.set_property('vm_to_pu', dialog.vm_to_pu.value(), push_undo=False)
            node.set_property('max_p_mw', dialog.max_p_mw.value(), push_undo=False)
            node.set_property('min_q_from_mvar', dialog.min_q_from_mvar.value(), push_undo=False)
            node.set_property('min_q_to_mvar', dialog.min_q_to_mvar.value(), push_undo=False)
            node.set_property('max_q_from_mvar', dialog.max_q_from_mvar.value(), push_undo=False)
            node.set_property('max_q_to_mvar', dialog.max_q_to_mvar.value(), push_undo=False)

            line_index = node.get_property('line_index')
            if line_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.dcline.loc[line_index, name] = np.round(node.get_property(name), 4)

            self.session_change_warning()

    def impedance_options(self, node):
        """
        Executed function when an Impedance node is double clicked.
        """
        dialog = impedance_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        rft_pu = node.get_property('rft_pu')
        xft_pu = node.get_property('xft_pu')
        rtf_pu = node.get_property('rtf_pu')
        xtf_pu = node.get_property('xtf_pu')
        if rft_pu==rtf_pu and xft_pu==xtf_pu:
            dialog.check1.setChecked(True)
        else:
            dialog.check1.setChecked(False)

        rft0_pu = node.get_property('rft0_pu')
        xft0_pu = node.get_property('xft0_pu')
        rtf0_pu = node.get_property('rtf0_pu')
        xtf0_pu = node.get_property('xtf0_pu')
        if rft0_pu==rtf0_pu and xft0_pu==xtf0_pu:
            dialog.check2.setChecked(True)
        else:
            dialog.check2.setChecked(False)

        dialog.rft_pu.setValue(rft_pu)
        dialog.xft_pu.setValue(xft_pu)
        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.rtf_pu.setValue(rtf_pu)
        dialog.xtf_pu.setValue(xtf_pu)
        dialog.rft0_pu.setValue(rft0_pu)
        dialog.xft0_pu.setValue(xft0_pu)
        dialog.rtf0_pu.setValue(rtf0_pu)
        dialog.xtf0_pu.setValue(xtf0_pu)

        if dialog.exec():
            node.set_property('rft_pu', dialog.rft_pu.value(), push_undo=False)
            node.set_property('xft_pu', dialog.xft_pu.value(), push_undo=False)
            node.set_property('sn_mva', dialog.sn_mva.value(), push_undo=False)
            node.set_property('rtf_pu', dialog.rtf_pu.value(), push_undo=False)
            node.set_property('xtf_pu', dialog.xtf_pu.value(), push_undo=False)
            node.set_property('rft0_pu', dialog.rft0_pu.value(), push_undo=False)
            node.set_property('xft0_pu', dialog.xft0_pu.value(), push_undo=False)
            node.set_property('rtf0_pu', dialog.rtf0_pu.value(), push_undo=False)
            node.set_property('xtf0_pu', dialog.xtf0_pu.value(), push_undo=False)

            impedance_index = node.get_property('impedance_index')
            if impedance_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.impedance.loc[impedance_index, name] = np.round(node.get_property(name), 5)

            self.session_change_warning()

    def transformer_options(self, node):
        """
        Executed function when a two-winding transformer node is double clicked.
        """
        dialog = transformer_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.vn_hv_kv.setValue(node.get_property('vn_hv_kv'))
        dialog.vn_lv_kv.setValue(node.get_property('vn_lv_kv'))
        dialog.vkr_percent.setValue(node.get_property('vkr_percent'))
        dialog.vk_percent.setValue(node.get_property('vk_percent'))
        dialog.pfe_kw.setValue(node.get_property('pfe_kw'))
        dialog.i0_percent.setValue(node.get_property('i0_percent'))
        dialog.shift_degree.setValue(node.get_property('shift_degree'))
        tap_side = node.get_property('tap_side')
        if tap_side=='hv':
            dialog.tap_side.setCurrentIndex(0)
        elif tap_side=='lv':
            dialog.tap_side.setCurrentIndex(1)
        dialog.tap_neutral.setValue(node.get_property('tap_neutral'))
        dialog.tap_max.setValue(node.get_property('tap_max'))
        dialog.tap_min.setValue(node.get_property('tap_min'))
        dialog.tap_neutral.setMinimum(node.get_property('tap_min'))
        dialog.tap_neutral.setMaximum(node.get_property('tap_max'))
        dialog.tap_step_percent.setValue(node.get_property('tap_step_percent'))
        dialog.tap_step_degree.setValue(node.get_property('tap_step_degree'))
        dialog.tap_pos.setValue(node.get_property('tap_pos'))
        dialog.tap_pos_display.setText(str(node.get_property('tap_pos')))
        dialog.tap_pos.setMinimum(node.get_property('tap_min'))
        dialog.tap_pos.setMaximum(node.get_property('tap_max'))

        dialog.tap_phase_shifter.setChecked(node.get_property('tap_phase_shifter'))

        vector_group = node.get_property('vector_group')
        all_vector_groups = ('Dyn', 'Yyn', 'Yzn', 'YNyn')
        dialog.vector_group.setCurrentIndex(all_vector_groups.index(vector_group))
        dialog.max_loading_percent.setValue(node.get_property('max_loading_percent'))
        dialog.parallel.setValue(node.get_property('parallel'))
        dialog.df.setValue(node.get_property('df'))
        dialog.vk0_percent.setValue(node.get_property('vk0_percent'))
        dialog.vkr0_percent.setValue(node.get_property('vkr0_percent'))

        dialog.mag0_percent.setValue(node.get_property('mag0_percent'))
        dialog.mag0_rx.setValue(node.get_property('mag0_rx'))
        dialog.si0_hv_partial.setValue(node.get_property('si0_hv_partial'))
        dialog.xn_ohm.setValue(node.get_property('xn_ohm'))

        dialog.oltc.setChecked(node.get_property('oltc'))

        if dialog.exec():
            node.set_property('sn_mva', dialog.sn_mva.value(), push_undo=False)
            node.set_property('vn_hv_kv', dialog.vn_hv_kv.value(), push_undo=False)
            node.set_property('vn_lv_kv', dialog.vn_lv_kv.value(), push_undo=False)
            node.set_property('vkr_percent', dialog.vkr_percent.value(), push_undo=False)
            node.set_property('vk_percent', dialog.vk_percent.value(), push_undo=False)
            node.set_property('pfe_kw', dialog.pfe_kw.value(), push_undo=False)
            node.set_property('i0_percent', dialog.i0_percent.value(), push_undo=False)
            node.set_property('shift_degree', dialog.shift_degree.value(), push_undo=False)

            tap_side = dialog.tap_side.currentIndex()
            tap_side_options = ('hv', 'lv')
            node.set_property('tap_side', tap_side_options[tap_side], push_undo=False)

            node.set_property('tap_neutral', dialog.tap_neutral.value(), push_undo=False)
            node.set_property('tap_min', dialog.tap_min.value(), push_undo=False)
            node.set_property('tap_max', dialog.tap_max.value(), push_undo=False)
            node.set_property('tap_step_percent', dialog.tap_step_percent.value(), push_undo=False)
            node.set_property('tap_step_degree', dialog.tap_step_degree.value(), push_undo=False)
            node.set_property('tap_pos', dialog.tap_pos.value(), push_undo=False)
            tap_phase_shifter = True if dialog.tap_phase_shifter.isChecked() else False
            node.set_property('tap_phase_shifter', tap_phase_shifter, push_undo=False)
            node.set_property('vector_group', all_vector_groups[dialog.vector_group.currentIndex()], push_undo=False)
            node.set_property('max_loading_percent', dialog.max_loading_percent.value(), push_undo=False)
            node.set_property('parallel', dialog.parallel.value(), push_undo=False)
            node.set_property('df', dialog.df.value(), push_undo=False)
            node.set_property('vk0_percent', dialog.vk0_percent.value(), push_undo=False)
            node.set_property('vkr0_percent', dialog.vkr0_percent.value(), push_undo=False)
            node.set_property('mag0_percent', dialog.mag0_percent.value(), push_undo=False)
            node.set_property('mag0_rx', dialog.mag0_rx.value(), push_undo=False)
            node.set_property('si0_hv_partial', dialog.si0_hv_partial.value(), push_undo=False)
            node.set_property('xn_ohm', dialog.xn_ohm.value(), push_undo=False)
            oltc = True if dialog.oltc.isChecked() else False
            node.set_property('oltc', oltc, push_undo=False)

            node.tap_pos_widget.get_custom_widget().setMinimum(int(dialog.tap_min.value()))
            node.tap_pos_widget.get_custom_widget().setMaximum(int(dialog.tap_max.value()))
            node.tap_pos_widget.get_custom_widget().setValue(int(dialog.tap_pos.value()))

            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    if name in ('tap_pos', 'tap_max', 'tap_min', 'tap_neutral', 'parallel'):  # int
                        self.net.trafo.loc[transformer_index, name] = int(node.get_property(name))
                    elif name in ('tap_side', 'vector_group'):  # str
                        self.net.trafo.loc[transformer_index, name] = node.get_property(name)
                    elif name in ('oltc', 'tap_phase_shifter'):  # bool
                        self.net.trafo.loc[transformer_index, name] = (True if node.get_property(name)=='True'
                                                                       else False)
                    else:  # float
                        self.net.trafo.loc[transformer_index, name] = np.round(node.get_property(name), 5)

            self.session_change_warning()

    def stdtransformer_options(self, node):
        """
        Executed function when a Standard 2W-Transformer node is double clicked.
        """
        table = pp.available_std_types(self.net, 'trafo')
        selected_std = node.get_property('std_type')

        dialog = stdtransformer_dialog(table, selected_std)
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        dialog.vk0_percent.setValue(node.get_property('vk0_percent'))
        dialog.vkr0_percent.setValue(node.get_property('vkr0_percent'))
        dialog.mag0_percent.setValue(node.get_property('mag0_percent'))
        dialog.mag0_rx.setValue(node.get_property('mag0_rx'))
        dialog.si0_hv_partial.setValue(node.get_property('si0_hv_partial'))
        dialog.xn_ohm.setValue(node.get_property('xn_ohm'))
        dialog.parallel.setValue(node.get_property('parallel'))
        dialog.df.setValue(node.get_property('df'))
        dialog.max_loading_percent.setValue(node.get_property('max_loading_percent'))
        dialog.tap_pos.setValue(node.get_property('tap_pos'))
        dialog.tap_pos_display.setText(str(node.get_property('tap_pos')))
        dialog.tap_pos.setMinimum(table.at[selected_std, 'tap_min'])
        dialog.tap_pos.setMaximum(table.at[selected_std, 'tap_max'])

        if dialog.exec():
            node.set_property('vk0_percent', dialog.vk0_percent.value(), push_undo=False)
            node.set_property('vkr0_percent', dialog.vkr0_percent.value(), push_undo=False)
            node.set_property('mag0_percent', dialog.mag0_percent.value(), push_undo=False)
            node.set_property('mag0_rx', dialog.mag0_rx.value(), push_undo=False)
            node.set_property('si0_hv_partial', dialog.si0_hv_partial.value(), push_undo=False)
            node.set_property('xn_ohm', dialog.xn_ohm.value(), push_undo=False)
            node.set_property('parallel', int(dialog.parallel.value()), push_undo=False)
            node.set_property('df', dialog.df.value(), push_undo=False)
            node.set_property('max_loading_percent', dialog.max_loading_percent.value(), push_undo=False)
            node.set_property('std_type', dialog.std_type.currentText(), push_undo=False)
            node.set_property('tap_pos', dialog.tap_pos.value(), push_undo=False)
            node.set_property('tap_min', int(dialog.tap_pos.minimum()), push_undo=False)
            node.set_property('tap_max', int(dialog.tap_pos.maximum()), push_undo=False)


            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    if name in ('parallel', 'tap_pos'):
                        self.net.trafo.loc[transformer_index, name] = int(node.get_property(name))
                    elif name=='std_type':
                        pp.change_std_type(self.net, transformer_index,
                                           name=node.get_property(name),
                                           element='trafo')
                    else:
                        self.net.trafo.loc[transformer_index, name] = np.round(node.get_property(name), 5)

            selected_std = dialog.std_type.currentText()
            tap_pos_widget = node.tap_pos_widget.get_custom_widget()
            
            tap_pos_widget.setMinimum(int(dialog.tap_pos.minimum()))
            tap_pos_widget.setMaximum(int(dialog.tap_pos.maximum()))
            tap_pos_widget.setValue(int(dialog.tap_pos.value()))
            
            self.session_change_warning()

    def transformer3w_options(self, node):
        """
        Executed function when a three-winding transformer node is double clicked.
        """
        dialog = transformer3w_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.sn_hv_mva.setValue(node.get_property('sn_hv_mva'))
        dialog.sn_mv_mva.setValue(node.get_property('sn_mv_mva'))
        dialog.sn_lv_mva.setValue(node.get_property('sn_lv_mva'))
        dialog.vn_hv_kv.setValue(node.get_property('vn_hv_kv'))
        dialog.vn_mv_kv.setValue(node.get_property('vn_mv_kv'))
        dialog.vn_lv_kv.setValue(node.get_property('vn_lv_kv'))
        dialog.vkr_hv_percent.setValue(node.get_property('vkr_hv_percent'))
        dialog.vkr_mv_percent.setValue(node.get_property('vkr_mv_percent'))
        dialog.vkr_lv_percent.setValue(node.get_property('vkr_lv_percent'))
        dialog.vk_hv_percent.setValue(node.get_property('vk_hv_percent'))
        dialog.vk_mv_percent.setValue(node.get_property('vk_mv_percent'))
        dialog.vk_lv_percent.setValue(node.get_property('vk_lv_percent'))
        dialog.pfe_kw.setValue(node.get_property('pfe_kw'))
        dialog.i0_percent.setValue(node.get_property('i0_percent'))
        dialog.shift_mv_degree.setValue(node.get_property('shift_mv_degree'))
        dialog.shift_lv_degree.setValue(node.get_property('shift_lv_degree'))
        tap_side = node.get_property('tap_side')
        if tap_side=='hv':
            dialog.tap_side.setCurrentIndex(0)
        elif tap_side=='mv':
            dialog.tap_side.setCurrentIndex(1)
        elif tap_side=='lv':
            dialog.tap_side.setCurrentIndex(2)
        dialog.tap_neutral.setValue(node.get_property('tap_neutral'))
        dialog.tap_max.setValue(node.get_property('tap_max'))
        dialog.tap_min.setValue(node.get_property('tap_min'))
        dialog.tap_neutral.setMinimum(node.get_property('tap_min'))
        dialog.tap_neutral.setMaximum(node.get_property('tap_max'))
        dialog.tap_step_percent.setValue(node.get_property('tap_step_percent'))
        dialog.tap_step_degree.setValue(node.get_property('tap_step_degree'))
        dialog.tap_pos.setValue(node.get_property('tap_pos'))
        dialog.tap_pos_display.setText(str(node.get_property('tap_pos')))
        dialog.tap_pos.setMinimum(node.get_property('tap_min'))
        dialog.tap_pos.setMaximum(node.get_property('tap_max'))

        dialog.tap_at_star_point.setChecked(True if node.get_property('tap_at_star_point')=='True' else False)

        vector_group = node.get_property('vector_group')
        all_vector_groups = ('Ddd', 'Ddy', 'Dyd', 'Dyy', 'Ydd', 'Ydy', 'Yyd',
                             'Yyy', 'YNyd', 'YNdy', 'Yynd', 'Ydyn', 'YNynd',
                             'YNdyn', 'YNdd', 'YNyy')
        dialog.vector_group.setCurrentIndex(all_vector_groups.index(vector_group))
        dialog.max_loading_percent.setValue(node.get_property('max_loading_percent'))
        dialog.vk0_hv_percent.setValue(node.get_property('vk0_hv_percent'))
        dialog.vk0_mv_percent.setValue(node.get_property('vk0_mv_percent'))
        dialog.vk0_lv_percent.setValue(node.get_property('vk0_lv_percent'))
        dialog.vkr0_hv_percent.setValue(node.get_property('vkr0_hv_percent'))
        dialog.vkr0_mv_percent.setValue(node.get_property('vkr0_mv_percent'))
        dialog.vkr0_lv_percent.setValue(node.get_property('vkr0_lv_percent'))

        if dialog.exec():
            node.set_property('sn_hv_mva', dialog.sn_hv_mva.value(), push_undo=False)
            node.set_property('sn_mv_mva', dialog.sn_mv_mva.value(), push_undo=False)
            node.set_property('sn_lv_mva', dialog.sn_lv_mva.value(), push_undo=False)
            node.set_property('vn_hv_kv', dialog.vn_hv_kv.value(), push_undo=False)
            node.set_property('vn_mv_kv', dialog.vn_mv_kv.value(), push_undo=False)
            node.set_property('vn_lv_kv', dialog.vn_lv_kv.value(), push_undo=False)
            node.set_property('vkr_hv_percent', dialog.vkr_hv_percent.value(), push_undo=False)
            node.set_property('vkr_mv_percent', dialog.vkr_mv_percent.value(), push_undo=False)
            node.set_property('vkr_lv_percent', dialog.vkr_lv_percent.value(), push_undo=False)
            node.set_property('vk_hv_percent', dialog.vk_hv_percent.value(), push_undo=False)
            node.set_property('vk_mv_percent', dialog.vk_mv_percent.value(), push_undo=False)
            node.set_property('vk_lv_percent', dialog.vk_lv_percent.value(), push_undo=False)
            node.set_property('pfe_kw', dialog.pfe_kw.value(), push_undo=False)
            node.set_property('i0_percent', dialog.i0_percent.value(), push_undo=False)
            node.set_property('shift_mv_degree', dialog.shift_mv_degree.value(), push_undo=False)
            node.set_property('shift_lv_degree', dialog.shift_lv_degree.value(), push_undo=False)

            tap_side = dialog.tap_side.currentIndex()
            tap_side_options = ('hv', 'mv', 'lv')
            node.set_property('tap_side', tap_side_options[tap_side], push_undo=False)

            node.set_property('tap_neutral', dialog.tap_neutral.value(), push_undo=False)
            node.set_property('tap_min', dialog.tap_min.value(), push_undo=False)
            node.set_property('tap_max', dialog.tap_max.value(), push_undo=False)
            node.set_property('tap_step_percent', dialog.tap_step_percent.value(), push_undo=False)
            node.set_property('tap_step_degree', dialog.tap_step_degree.value(), push_undo=False)
            node.set_property('tap_pos', dialog.tap_pos.value(), push_undo=False)
            tap_at_star_point = 'True' if dialog.tap_at_star_point.isChecked() else 'False'
            node.set_property('tap_at_star_point', tap_at_star_point, push_undo=False)
            node.set_property('vector_group', all_vector_groups[dialog.vector_group.currentIndex()], push_undo=False)
            node.set_property('max_loading_percent', dialog.max_loading_percent.value(), push_undo=False)
            node.set_property('vk0_hv_percent', dialog.vk0_hv_percent.value(), push_undo=False)
            node.set_property('vk0_mv_percent', dialog.vk0_mv_percent.value(), push_undo=False)
            node.set_property('vk0_lv_percent', dialog.vk0_lv_percent.value(), push_undo=False)
            node.set_property('vkr0_hv_percent', dialog.vkr0_hv_percent.value(), push_undo=False)
            node.set_property('vkr0_mv_percent', dialog.vkr0_mv_percent.value(), push_undo=False)
            node.set_property('vkr0_lv_percent', dialog.vkr0_lv_percent.value(), push_undo=False)

            node.tap_pos_widget.get_custom_widget().setMinimum(int(dialog.tap_min.value()))
            node.tap_pos_widget.get_custom_widget().setMaximum(int(dialog.tap_max.value()))

            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    if name in ('tap_pos', 'tap_max', 'tap_min', 'tap_neutral'):  # int
                        self.net.trafo3w.loc[transformer_index, name] = int(node.get_property(name))
                    elif name in ('tap_side', 'vector_group'):  # str
                        self.net.trafo3w.loc[transformer_index, name] = node.get_property(name)
                    elif name=='tap_at_star_point':  # bool
                        self.net.trafo3w.loc[transformer_index, name] = (True if node.get_property(name)=='True'
                                                                       else False)
                    else:  # float
                        self.net.trafo3w.loc[transformer_index, name] = np.round(node.get_property(name), 5)

            self.session_change_warning()

    def stdtransformer3w_options(self, node):
        """
        Executed function when a Standard 3W-Transformer node is double clicked.
        """
        table = pp.available_std_types(self.net, 'trafo3w')
        selected_std = node.get_property('std_type')

        dialog = stdtransformer3w_dialog(table, selected_std)
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        dialog.max_loading_percent.setValue(node.get_property('max_loading_percent'))
        dialog.tap_pos.setValue(node.get_property('tap_pos'))
        dialog.tap_pos_display.setText(str(node.get_property('tap_pos')))
        dialog.tap_pos.setMinimum(table.at[selected_std, 'tap_min'])
        dialog.tap_pos.setMaximum(table.at[selected_std, 'tap_max'])
        
        dialog.tap_at_star_point.setChecked(True if node.get_property('tap_at_star_point')=='True' else False)

        if dialog.exec():
            node.set_property('max_loading_percent', dialog.max_loading_percent.value(), push_undo=False)
            node.set_property('std_type', dialog.std_type.currentText(), push_undo=False)
            node.set_property('tap_pos', dialog.tap_pos.value(), push_undo=False)
            node.set_property('tap_min', int(dialog.tap_pos.minimum()), push_undo=False)
            node.set_property('tap_max', int(dialog.tap_pos.maximum()), push_undo=False)

            tap_at_star_point = 'True' if dialog.tap_at_star_point.isChecked() else 'False'
            node.set_property('tap_at_star_point', tap_at_star_point, push_undo=False)

            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    if name=='tap_pos':
                        self.net.trafo3w.loc[transformer_index, name] = int(node.get_property(name))
                    elif name=='std_type':
                        pp.change_std_type(self.net, transformer_index,
                                           name=node.get_property(name),
                                           element='trafo3w')
                    elif name=='max_loading_percent':
                        self.net.trafo3w.loc[transformer_index, name] = np.round(node.get_property(name), 3)
                    elif name=='tap_at_star_point' and node.get_property(name)=='True':
                        self.net.trafo3w.loc[transformer_index, name] = True
                    elif name=='tap_at_star_point' and node.get_property(name)=='False':
                        self.net.trafo3w.loc[transformer_index, name] = False

            selected_std = dialog.std_type.currentText()
            tap_pos_widget = node.tap_pos_widget.get_custom_widget()
            
            tap_pos_widget.setMinimum(int(dialog.tap_pos.minimum()))
            tap_pos_widget.setMaximum(int(dialog.tap_pos.maximum()))
            tap_pos_widget.setValue(int(dialog.tap_pos.value()))
            
            self.session_change_warning()

    def gen_options(self, node):
        """
        Executed function when a Generator node is double clicked.
        """
        dialog = gen_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.scaling.setValue(node.get_property('scaling'))
        dialog.slack_weight.setValue(node.get_property('slack_weight'))
        dialog.vn_kv.setValue(node.get_property('vn_kv'))
        dialog.xdss_pu.setValue(node.get_property('xdss_pu'))
        dialog.rdss_ohm.setValue(node.get_property('rdss_ohm'))
        dialog.cos_phi.setValue(node.get_property('cos_phi'))
        dialog.controllable.setChecked(node.get_property('controllable'))
        dialog.max_p_mw.setValue(node.get_property('max_p_mw'))
        dialog.min_p_mw.setValue(node.get_property('min_p_mw'))
        dialog.max_q_mvar.setValue(node.get_property('max_q_mvar'))
        dialog.min_q_mvar.setValue(node.get_property('min_q_mvar'))
        dialog.max_vm_pu.setValue(node.get_property('max_vm_pu'))
        dialog.min_vm_pu.setValue(node.get_property('min_vm_pu'))

        dialog.vm_pu.setMinimum(node.get_property('min_vm_pu'))
        dialog.vm_pu.setMaximum(node.get_property('max_vm_pu'))
        dialog.p_mw.setMinimum(node.get_property('min_p_mw'))
        dialog.p_mw.setMaximum(node.get_property('max_p_mw'))

        dialog.p_mw.setValue(node.get_property('p_mw'))
        dialog.vm_pu.setValue(node.get_property('vm_pu'))

        if dialog.exec():
            node.set_property('p_mw', np.round(dialog.p_mw.value(), 5), push_undo=False)
            node.set_property('vm_pu', np.round(dialog.vm_pu.value(), 5), push_undo=False)
            node.set_property('sn_mva', np.round(dialog.sn_mva.value(), 5), push_undo=False)
            node.set_property('scaling', np.round(dialog.scaling.value(), 5), push_undo=False)
            node.set_property('slack_weight', np.round(dialog.slack_weight.value(), 5), push_undo=False)
            node.set_property('vn_kv', np.round(dialog.vn_kv.value(), 5), push_undo=False)
            node.set_property('xdss_pu', np.round(dialog.xdss_pu.value(), 5), push_undo=False)
            node.set_property('rdss_ohm', np.round(dialog.rdss_ohm.value(), 5), push_undo=False)
            node.set_property('cos_phi', np.round(dialog.cos_phi.value(), 5), push_undo=False)
            node.set_property('max_p_mw', np.round(dialog.max_p_mw.value(), 5), push_undo=False)
            node.set_property('min_p_mw', np.round(dialog.min_p_mw.value(), 5), push_undo=False)
            node.set_property('max_q_mvar', np.round(dialog.max_q_mvar.value(), 5), push_undo=False)
            node.set_property('min_q_mvar', np.round(dialog.min_q_mvar.value(), 5), push_undo=False)
            node.set_property('max_vm_pu', np.round(dialog.max_vm_pu.value(), 5), push_undo=False)
            node.set_property('min_vm_pu', np.round(dialog.min_vm_pu.value(), 5), push_undo=False)
            node.set_property('controllable', dialog.controllable.isChecked(), push_undo=False)

            node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
            node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
            node.vm_pu_widget.get_custom_widget().setMinimum(node.get_property('min_vm_pu'))
            node.vm_pu_widget.get_custom_widget().setMaximum(node.get_property('max_vm_pu'))
            node.vm_pu_widget.get_custom_widget().setValue(node.get_property('vm_pu'))

            gen_index = node.get_property('gen_index')
            if gen_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.gen.loc[gen_index, name] = node.get_property(name)

            self.session_change_warning()

    def sgen_options(self, node):
        """
        Executed function when a Static Generator node is double clicked.
        """
        dialog = sgen_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.scaling.setValue(node.get_property('scaling'))

        types = ('wye', 'delta')
        type_index = types.index(node.get_property('type'))
        dialog.type.setCurrentIndex(type_index)

        k = node.get_property('k')
        if isnan(k):
            dialog.k_check.setChecked(False)
        else:
            dialog.k_check.setChecked(True)
            dialog.k.setValue(k)

        rx = node.get_property('rx')
        if isnan(rx):
            dialog.rx_check.setChecked(False)
        else:
            dialog.rx_check.setChecked(True)
            dialog.rx.setValue(rx)

        generator_types = (None, 'current_source', 'async', 'async_doubly_fed')
        gentype_index = generator_types.index(node.get_property('generator_type'))
        dialog.generator_type.setCurrentIndex(gentype_index)

        lrc_pu = node.get_property('lrc_pu')
        if isnan(lrc_pu):
            dialog.lrc_pu_check.setChecked(False)
        else:
            dialog.lrc_pu_check.setChecked(True)
            dialog.lrc_pu.setValue(lrc_pu)

        max_ik_ka = node.get_property('max_ik_ka')
        if isnan(max_ik_ka):
            dialog.max_ik_ka_check.setChecked(False)
        else:
            dialog.max_ik_ka_check.setChecked(True)
            dialog.max_ik_ka.setValue(max_ik_ka)

        kappa = node.get_property('kappa')
        if isnan(kappa):
            dialog.kappa_check.setChecked(False)
        else:
            dialog.kappa_check.setChecked(True)
            dialog.kappa.setValue(kappa)

        dialog.current_source.setChecked(node.get_property('current_source'))
        dialog.controllable.setChecked(node.get_property('controllable'))
        dialog.max_p_mw.setValue(node.get_property('max_p_mw'))
        dialog.min_p_mw.setValue(node.get_property('min_p_mw'))
        dialog.max_q_mvar.setValue(node.get_property('max_q_mvar'))
        dialog.min_q_mvar.setValue(node.get_property('min_q_mvar'))

        dialog.p_mw.setMinimum(node.get_property('min_p_mw'))
        dialog.p_mw.setMaximum(node.get_property('max_p_mw'))
        dialog.q_mvar.setMinimum(node.get_property('min_q_mvar'))
        dialog.q_mvar.setMaximum(node.get_property('max_q_mvar'))

        dialog.p_mw.setValue(node.get_property('p_mw'))
        dialog.q_mvar.setValue(node.get_property('q_mvar'))

        if dialog.exec():
            node.set_property('p_mw', np.round(dialog.p_mw.value(), 5), push_undo=False)
            node.set_property('q_mvar', np.round(dialog.q_mvar.value(), 5), push_undo=False)
            node.set_property('sn_mva', np.round(dialog.sn_mva.value(), 5), push_undo=False)
            node.set_property('scaling', np.round(dialog.scaling.value(), 5), push_undo=False)
            node.set_property('type', dialog.type.currentText(), push_undo=False)

            if dialog.k_check.isChecked():
                node.set_property('k', np.round(dialog.k.value(), 5), push_undo=False)
            else:
                node.set_property('k', nan, push_undo=False)

            if dialog.rx_check.isChecked():
                node.set_property('rx', np.round(dialog.rx.value(), 5), push_undo=False)
            else:
                node.set_property('rx', nan, push_undo=False)

            generator_types = (None, 'current_source', 'async', 'async_doubly_fed')
            node.set_property('generator_type',
                              generator_types[dialog.generator_type.currentIndex()],
                              push_undo=False)

            if dialog.lrc_pu_check.isChecked():
                node.set_property('lrc_pu', np.round(dialog.lrc_pu.value(), 5), push_undo=False)
            else:
                node.set_property('lrc_pu', nan, push_undo=False)

            if dialog.max_ik_ka_check.isChecked():
                node.set_property('max_ik_ka',
                                  np.round(dialog.max_ik_ka.value(), 5), push_undo=False)
            else:
                node.set_property('max_ik_ka', nan, push_undo=False)

            if dialog.kappa_check.isChecked():
                node.set_property('kappa',
                                  np.round(dialog.kappa.value(), 5), push_undo=False)
            else:
                node.set_property('kappa', nan, push_undo=False)

            node.set_property('max_p_mw', np.round(dialog.max_p_mw.value(), 5), push_undo=False)
            node.set_property('min_p_mw', np.round(dialog.min_p_mw.value(), 5), push_undo=False)
            node.set_property('max_q_mvar', np.round(dialog.max_q_mvar.value(), 5), push_undo=False)
            node.set_property('min_q_mvar', np.round(dialog.min_q_mvar.value(), 5), push_undo=False)

            node.set_property('controllable', dialog.controllable.isChecked(), push_undo=False)
            node.set_property('current_source', dialog.current_source.isChecked(), push_undo=False)

            node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
            node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
            node.q_mvar_widget.get_custom_widget().setMinimum(node.get_property('min_q_mvar'))
            node.q_mvar_widget.get_custom_widget().setMaximum(node.get_property('max_q_mvar'))
            node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

            gen_index = node.get_property('gen_index')
            if gen_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.sgen.loc[gen_index, name] = node.get_property(name)

            self.session_change_warning()

    def asgen_options(self, node):
        """
        Executed function when an Asymmetric Static Generator node is double clicked.
        """
        dialog = asgen_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.p_a_mw.setValue(node.get_property('p_a_mw'))
        dialog.q_a_mvar.setValue(node.get_property('q_a_mvar'))
        dialog.p_b_mw.setValue(node.get_property('p_b_mw'))
        dialog.q_b_mvar.setValue(node.get_property('q_b_mvar'))
        dialog.p_c_mw.setValue(node.get_property('p_c_mw'))
        dialog.q_c_mvar.setValue(node.get_property('q_c_mvar'))
        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.scaling.setValue(node.get_property('scaling'))

        types = ('wye', 'delta')
        type_index = types.index(node.get_property('type'))
        dialog.type.setCurrentIndex(type_index)

        if dialog.exec():
            node.set_property('p_a_mw', np.round(dialog.p_a_mw.value(), 5), push_undo=False)
            node.set_property('q_a_mvar', np.round(dialog.q_a_mvar.value(), 5), push_undo=False)
            node.set_property('p_b_mw', np.round(dialog.p_b_mw.value(), 5), push_undo=False)
            node.set_property('q_b_mvar', np.round(dialog.q_b_mvar.value(), 5), push_undo=False)
            node.set_property('p_c_mw', np.round(dialog.p_c_mw.value(), 5), push_undo=False)
            node.set_property('q_c_mvar', np.round(dialog.q_c_mvar.value(), 5), push_undo=False)
            node.set_property('sn_mva', np.round(dialog.sn_mva.value(), 5), push_undo=False)
            node.set_property('scaling', np.round(dialog.scaling.value(), 5), push_undo=False)
            node.set_property('type', dialog.type.currentText(), push_undo=False)

            gen_index = node.get_property('gen_index')
            if gen_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.asymmetric_sgen.loc[gen_index, name] = node.get_property(name)

            self.session_change_warning()

    def ext_grid_options(self, node):
        """
        Executed function when an External Grid node is double clicked.
        """
        dialog = ext_grid_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.vm_pu.setValue(node.get_property('vm_pu'))
        dialog.va_degree.setValue(node.get_property('va_degree'))
        dialog.slack_weight.setValue(node.get_property('slack_weight'))
        dialog.controllable.setChecked(node.get_property('controllable'))
        dialog.max_p_mw.setValue(node.get_property('max_p_mw'))
        dialog.min_p_mw.setValue(node.get_property('min_p_mw'))
        dialog.max_q_mvar.setValue(node.get_property('max_q_mvar'))
        dialog.min_q_mvar.setValue(node.get_property('min_q_mvar'))

        s_sc_max_mva = node.get_property('s_sc_max_mva')
        if isnan(s_sc_max_mva):
            dialog.s_sc_max_mva_check.setChecked(False)
        else:
            dialog.s_sc_max_mva_check.setChecked(True)
            dialog.s_sc_max_mva.setValue(s_sc_max_mva)

        s_sc_min_mva = node.get_property('s_sc_min_mva')
        if isnan(s_sc_min_mva):
            dialog.s_sc_min_mva_check.setChecked(False)
        else:
            dialog.s_sc_min_mva_check.setChecked(True)
            dialog.s_sc_min_mva.setValue(s_sc_min_mva)

        rx_max = node.get_property('rx_max')
        if isnan(rx_max):
            dialog.rx_max_check.setChecked(False)
        else:
            dialog.rx_max_check.setChecked(True)
            dialog.rx_max.setValue(rx_max)

        rx_min = node.get_property('rx_min')
        if isnan(rx_min):
            dialog.rx_min_check.setChecked(False)
        else:
            dialog.rx_min_check.setChecked(True)
            dialog.rx_min.setValue(rx_min)

        r0x0_max = node.get_property('r0x0_max')
        if isnan(r0x0_max):
            dialog.r0x0_max_check.setChecked(False)
        else:
            dialog.r0x0_max_check.setChecked(True)
            dialog.r0x0_max.setValue(r0x0_max)

        x0x_max = node.get_property('x0x_max')
        if isnan(x0x_max):
            dialog.x0x_max_check.setChecked(False)
        else:
            dialog.x0x_max_check.setChecked(True)
            dialog.x0x_max.setValue(x0x_max)

        if dialog.exec():
            node.set_property('vm_pu', np.round(dialog.vm_pu.value(), 5), push_undo=False)
            node.set_property('va_degree', np.round(dialog.va_degree.value(), 5), push_undo=False)
            node.set_property('slack_weight', np.round(dialog.slack_weight.value(), 5), push_undo=False)
            node.set_property('max_p_mw', np.round(dialog.max_p_mw.value(), 5), push_undo=False)
            node.set_property('min_p_mw', np.round(dialog.min_p_mw.value(), 5), push_undo=False)
            node.set_property('max_q_mvar', np.round(dialog.max_q_mvar.value(), 5), push_undo=False)
            node.set_property('min_q_mvar', np.round(dialog.min_q_mvar.value(), 5), push_undo=False)
            node.set_property('controllable', dialog.controllable.isChecked(), push_undo=False)

            if dialog.s_sc_max_mva_check.isChecked():
                node.set_property('s_sc_max_mva', np.round(dialog.s_sc_max_mva.value(), 5),
                                  push_undo=False)
            else:
                node.set_property('s_sc_max_mva', nan, push_undo=False)

            if dialog.s_sc_min_mva_check.isChecked():
                node.set_property('s_sc_min_mva', np.round(dialog.s_sc_min_mva.value(), 5),
                                  push_undo=False)
            else:
                node.set_property('s_sc_min_mva', nan, push_undo=False)

            if dialog.rx_max_check.isChecked():
                node.set_property('rx_max', np.round(dialog.rx_max.value(), 5), push_undo=False)
            else:
                node.set_property('rx_max', nan, push_undo=False)

            if dialog.rx_min_check.isChecked():
                node.set_property('rx_min', np.round(dialog.rx_min.value(), 5), push_undo=False)
            else:
                node.set_property('rx_min', nan, push_undo=False)

            if dialog.r0x0_max_check.isChecked():
                node.set_property('r0x0_max', np.round(dialog.r0x0_max.value(), 5), push_undo=False)
            else:
                node.set_property('r0x0_max', nan, push_undo=False)

            if dialog.x0x_max_check.isChecked():
                node.set_property('x0x_max',
                                  np.round(dialog.x0x_max.value(), 5), push_undo=False)
            else:
                node.set_property('x0x_max', nan, push_undo=False)

            grid_index = node.get_property('grid_index')
            if grid_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.ext_grid.loc[grid_index, name] = node.get_property(name)

            self.session_change_warning()

    def load_options(self, node):
        """
        Executed function when a Symmetric Load node is double clicked.
        """
        dialog = load_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.scaling.setValue(node.get_property('scaling'))
        dialog.const_z_percent.setValue(node.get_property('const_z_percent'))
        dialog.const_i_percent.setValue(node.get_property('const_i_percent'))

        types = ('wye', 'delta')
        type_index = types.index(node.get_property('type'))
        dialog.type.setCurrentIndex(type_index)

        dialog.controllable.setChecked(node.get_property('controllable'))
        dialog.max_p_mw.setValue(node.get_property('max_p_mw'))
        dialog.min_p_mw.setValue(node.get_property('min_p_mw'))
        dialog.max_q_mvar.setValue(node.get_property('max_q_mvar'))
        dialog.min_q_mvar.setValue(node.get_property('min_q_mvar'))

        dialog.p_mw.setMinimum(node.get_property('min_p_mw'))
        dialog.p_mw.setMaximum(node.get_property('max_p_mw'))
        dialog.q_mvar.setMinimum(node.get_property('min_q_mvar'))
        dialog.q_mvar.setMaximum(node.get_property('max_q_mvar'))

        dialog.p_mw.setValue(node.get_property('p_mw'))
        dialog.q_mvar.setValue(node.get_property('q_mvar'))

        if dialog.exec():
            node.set_property('p_mw', np.round(dialog.p_mw.value(), 5), push_undo=False)
            node.set_property('q_mvar', np.round(dialog.q_mvar.value(), 5), push_undo=False)
            node.set_property('sn_mva', np.round(dialog.sn_mva.value(), 5), push_undo=False)
            node.set_property('scaling', np.round(dialog.scaling.value(), 5), push_undo=False)
            node.set_property('const_z_percent', np.round(dialog.const_z_percent.value(), 5), push_undo=False)
            node.set_property('const_i_percent', np.round(dialog.const_i_percent.value(), 5), push_undo=False)
            node.set_property('type', dialog.type.currentText(), push_undo=False)

            node.set_property('max_p_mw', np.round(dialog.max_p_mw.value(), 5), push_undo=False)
            node.set_property('min_p_mw', np.round(dialog.min_p_mw.value(), 5), push_undo=False)
            node.set_property('max_q_mvar', np.round(dialog.max_q_mvar.value(), 5), push_undo=False)
            node.set_property('min_q_mvar', np.round(dialog.min_q_mvar.value(), 5), push_undo=False)

            node.set_property('controllable', dialog.controllable.isChecked(), push_undo=False)

            node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
            node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
            node.q_mvar_widget.get_custom_widget().setMinimum(node.get_property('min_q_mvar'))
            node.q_mvar_widget.get_custom_widget().setMaximum(node.get_property('max_q_mvar'))
            node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

            load_index = node.get_property('load_index')
            if load_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.load.loc[load_index, name] = node.get_property(name)

            self.session_change_warning()

    def aload_options(self, node):
        """
        Executed function when an Asymmetric Load node is double clicked.
        """
        dialog = aload_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.p_a_mw.setValue(node.get_property('p_a_mw'))
        dialog.q_a_mvar.setValue(node.get_property('q_a_mvar'))
        dialog.p_b_mw.setValue(node.get_property('p_b_mw'))
        dialog.q_b_mvar.setValue(node.get_property('q_b_mvar'))
        dialog.p_c_mw.setValue(node.get_property('p_c_mw'))
        dialog.q_c_mvar.setValue(node.get_property('q_c_mvar'))
        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.scaling.setValue(node.get_property('scaling'))

        types = ('wye', 'delta')
        type_index = types.index(node.get_property('type'))
        dialog.type.setCurrentIndex(type_index)

        if dialog.exec():
            node.set_property('p_a_mw', np.round(dialog.p_a_mw.value(), 5), push_undo=False)
            node.set_property('q_a_mvar', np.round(dialog.q_a_mvar.value(), 5), push_undo=False)
            node.set_property('p_b_mw', np.round(dialog.p_b_mw.value(), 5), push_undo=False)
            node.set_property('q_b_mvar', np.round(dialog.q_b_mvar.value(), 5), push_undo=False)
            node.set_property('p_c_mw', np.round(dialog.p_c_mw.value(), 5), push_undo=False)
            node.set_property('q_c_mvar', np.round(dialog.q_c_mvar.value(), 5), push_undo=False)
            node.set_property('sn_mva', np.round(dialog.sn_mva.value(), 5), push_undo=False)
            node.set_property('scaling', np.round(dialog.scaling.value(), 5), push_undo=False)
            node.set_property('type', dialog.type.currentText(), push_undo=False)

            load_index = node.get_property('load_index')
            if load_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.asymmetric_load.loc[load_index, name] = node.get_property(name)

            self.session_change_warning()

    def shunt_options(self, node):
        """
        Executed function when a Shunt Element node is double clicked.
        """
        dialog = shunt_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.step.setValue(node.get_property('step'))
        dialog.max_step.setValue(node.get_property('max_step'))
        dialog.step.setMaximum(node.get_property('max_step'))

        vn_kv = node.get_property('vn_kv')
        if vn_kv is None:
            dialog.vn_kv_check.setChecked(False)
        else:
            dialog.vn_kv_check.setChecked(True)
            dialog.vn_kv.setValue(vn_kv)

        dialog.p_mw.setValue(node.get_property('p_mw'))
        dialog.q_mvar.setValue(node.get_property('q_mvar'))

        if dialog.exec():
            node.set_property('p_mw', np.round(dialog.p_mw.value(), 5), push_undo=False)
            node.set_property('q_mvar', np.round(dialog.q_mvar.value(), 5), push_undo=False)
            node.set_property('step', int(dialog.step.value()), push_undo=False)
            node.set_property('max_step', int(dialog.max_step.value()), push_undo=False)

            if dialog.vn_kv_check.isChecked():
                node.set_property('vn_kv', np.round(dialog.vn_kv.value(), 5), push_undo=False)
            else:
                node.set_property('vn_kv', None, push_undo=False)

            node.step_widget.get_custom_widget().setMaximum(node.get_property('max_step'))

            shunt_index = node.get_property('shunt_index')
            if shunt_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.shunt.loc[shunt_index, name] = node.get_property(name)

            self.session_change_warning()

    def motor_options(self, node):
        """
        Executed function when a Motor node is double clicked.
        """
        dialog = motor_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.pn_mech_mw.setValue(node.get_property('pn_mech_mw'))
        dialog.cos_phi.setValue(node.get_property('cos_phi'))
        dialog.efficiency_percent.setValue(node.get_property('efficiency_percent'))
        dialog.loading_percent.setValue(node.get_property('loading_percent'))
        dialog.scaling.setValue(node.get_property('scaling'))
        dialog.efficiency_n_percent.setValue(node.get_property('efficiency_n_percent'))

        cos_phi_n = node.get_property('cos_phi_n')
        if isnan(cos_phi_n):
            dialog.cos_phi_n_check.setChecked(False)
        else:
            dialog.cos_phi_n_check.setChecked(True)
            dialog.cos_phi_n.setValue(cos_phi_n)

        lrc_pu = node.get_property('lrc_pu')
        if isnan(lrc_pu):
            dialog.lrc_pu_check.setChecked(False)
        else:
            dialog.lrc_pu_check.setChecked(True)
            dialog.lrc_pu.setValue(lrc_pu)

        rx = node.get_property('rx')
        if isnan(rx):
            dialog.rx_check.setChecked(False)
        else:
            dialog.rx_check.setChecked(True)
            dialog.rx.setValue(rx)

        vn_kv = node.get_property('vn_kv')
        if isnan(vn_kv):
            dialog.vn_kv_check.setChecked(False)
        else:
            dialog.vn_kv_check.setChecked(True)
            dialog.vn_kv.setValue(vn_kv)

        if dialog.exec():
            node.set_property('pn_mech_mw', np.round(dialog.pn_mech_mw.value(), 5), push_undo=False)
            node.set_property('cos_phi', np.round(dialog.cos_phi.value(), 5), push_undo=False)
            node.set_property('efficiency_percent', np.round(dialog.efficiency_percent.value(), 5), push_undo=False)
            node.set_property('loading_percent', np.round(dialog.loading_percent.value(), 5), push_undo=False)
            node.set_property('scaling', np.round(dialog.scaling.value(), 5), push_undo=False)
            node.set_property('efficiency_n_percent', np.round(dialog.efficiency_n_percent.value(), 5), push_undo=False)

            if dialog.cos_phi_n_check.isChecked():
                node.set_property('cos_phi_n',
                                  np.round(dialog.cos_phi_n.value(), 5), push_undo=False)
            else:
                node.set_property('cos_phi_n', nan, push_undo=False)

            if dialog.lrc_pu_check.isChecked():
                node.set_property('lrc_pu',
                                  np.round(dialog.lrc_pu.value(), 5), push_undo=False)
            else:
                node.set_property('lrc_pu', nan, push_undo=False)

            if dialog.rx_check.isChecked():
                node.set_property('rx',
                                  np.round(dialog.rx.value(), 5), push_undo=False)
            else:
                node.set_property('rx', nan, push_undo=False)

            if dialog.vn_kv_check.isChecked():
                node.set_property('vn_kv',
                                  np.round(dialog.vn_kv.value(), 5), push_undo=False)
            else:
                node.set_property('vn_kv', nan, push_undo=False)

            motor_index = node.get_property('motor_index')
            if motor_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.motor.loc[motor_index, name] = node.get_property(name)

            self.session_change_warning()

    def ward_options(self, node):
        """
        Executed function when a Ward node is double clicked.
        """
        dialog = ward_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.ps_mw.setValue(node.get_property('ps_mw'))
        dialog.qs_mvar.setValue(node.get_property('qs_mvar'))
        dialog.pz_mw.setValue(node.get_property('pz_mw'))
        dialog.qz_mvar.setValue(node.get_property('qz_mvar'))

        if dialog.exec():
            node.set_property('ps_mw', np.round(dialog.ps_mw.value(), 5), push_undo=False)
            node.set_property('qs_mvar', np.round(dialog.qs_mvar.value(), 5), push_undo=False)
            node.set_property('pz_mw', np.round(dialog.pz_mw.value(), 5), push_undo=False)
            node.set_property('qz_mvar', np.round(dialog.qz_mvar.value(), 5), push_undo=False)

            ward_index = node.get_property('ward_index')
            if ward_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.ward.loc[ward_index, name] = node.get_property(name)

            self.session_change_warning()

    def xward_options(self, node):
        """
        Executed function when an Extended Ward node is double clicked.
        """
        dialog = xward_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))

        dialog.ps_mw.setValue(node.get_property('ps_mw'))
        dialog.qs_mvar.setValue(node.get_property('qs_mvar'))
        dialog.pz_mw.setValue(node.get_property('pz_mw'))
        dialog.qz_mvar.setValue(node.get_property('qz_mvar'))
        dialog.r_ohm.setValue(node.get_property('r_ohm'))
        dialog.x_ohm.setValue(node.get_property('x_ohm'))
        dialog.vm_pu.setValue(node.get_property('vm_pu'))
        dialog.slack_weight.setValue(node.get_property('slack_weight'))

        if dialog.exec():
            node.set_property('ps_mw', np.round(dialog.ps_mw.value(), 5), push_undo=False)
            node.set_property('qs_mvar', np.round(dialog.qs_mvar.value(), 5), push_undo=False)
            node.set_property('pz_mw', np.round(dialog.pz_mw.value(), 5), push_undo=False)
            node.set_property('qz_mvar', np.round(dialog.qz_mvar.value(), 5), push_undo=False)
            node.set_property('r_ohm', np.round(dialog.r_ohm.value(), 5), push_undo=False)
            node.set_property('x_ohm', np.round(dialog.x_ohm.value(), 5), push_undo=False)
            node.set_property('vm_pu', np.round(dialog.vm_pu.value(), 5), push_undo=False)
            node.set_property('slack_weight', np.round(dialog.slack_weight.value(), 5), push_undo=False)
            
            ward_index = node.get_property('ward_index')
            if ward_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.xward.loc[ward_index, name] = node.get_property(name)

            self.session_change_warning()
            
    def storage_options(self, node):
        """
        Executed function when a Storage node is double clicked.
        """
        dialog = storage_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        
        dialog.controllable.setChecked(node.get_property('controllable'))
        dialog.sn_mva.setValue(node.get_property('sn_mva'))
        dialog.scaling.setValue(node.get_property('scaling'))
        dialog.max_e_mwh.setValue(node.get_property('max_e_mwh'))
        dialog.min_e_mwh.setValue(node.get_property('min_e_mwh'))
        dialog.soc_percent.setValue(node.get_property('soc_percent'))
        dialog.max_p_mw.setValue(node.get_property('max_p_mw'))
        dialog.min_p_mw.setValue(node.get_property('min_p_mw'))
        dialog.max_q_mvar.setValue(node.get_property('max_q_mvar'))
        dialog.min_q_mvar.setValue(node.get_property('min_q_mvar'))
        
        dialog.p_mw.setMinimum(node.get_property('min_p_mw'))
        dialog.p_mw.setMaximum(node.get_property('max_p_mw'))
        dialog.q_mvar.setMinimum(node.get_property('min_q_mvar'))
        dialog.q_mvar.setMaximum(node.get_property('max_q_mvar'))

        dialog.p_mw.setValue(node.get_property('p_mw'))
        dialog.q_mvar.setValue(node.get_property('q_mvar'))
        
        dialog.type.setText(node.get_property('type'))
        
        if dialog.exec():
            node.set_property('p_mw', np.round(dialog.p_mw.value(), 6), push_undo=False)
            node.set_property('q_mvar', np.round(dialog.q_mvar.value(), 6), push_undo=False)
            node.set_property('sn_mva', np.round(dialog.sn_mva.value(), 6), push_undo=False)
            node.set_property('scaling', np.round(dialog.scaling.value(), 5), push_undo=False)
            node.set_property('max_e_mwh', np.round(dialog.max_e_mwh.value(), 6), push_undo=False)
            node.set_property('min_e_mwh', np.round(dialog.min_e_mwh.value(), 6), push_undo=False)
            node.set_property('soc_percent', np.round(dialog.soc_percent.value(), 5), push_undo=False)
            node.set_property('max_p_mw', np.round(dialog.max_p_mw.value(), 6), push_undo=False)
            node.set_property('min_p_mw', np.round(dialog.min_p_mw.value(), 6), push_undo=False)
            node.set_property('max_q_mvar', np.round(dialog.max_q_mvar.value(), 6), push_undo=False)
            node.set_property('min_q_mvar', np.round(dialog.min_q_mvar.value(), 6), push_undo=False)
            node.set_property('controllable', dialog.controllable.isChecked(), push_undo=False)
            node.set_property('type', dialog.type.text(), push_undo=False)
            
            storage_index = node.get_property('storage_index')
            if storage_index is not None and node.connected_to_network():
                for name in node.electrical_properties:
                    self.net.storage.loc[storage_index, name] = node.get_property(name)

            self.session_change_warning()
    
    def switch_options(self, node):
        """
        Executed function when a Switch node is double clicked.
        """
        dialog = switch_dialog()
        dialog.setWindowTitle(node.get_property('name'))
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        
        dialog.closed.setChecked(node.get_property('closed'))
        
        types = ('None', 'LS', 'CB', 'LBS', 'DS')
        pos_type = types.index(node.get_property('type'))
        dialog.type.setCurrentIndex(pos_type)
        
        in_ka = node.get_property('in_ka')
        if isnan(in_ka):
            dialog.in_ka_check.setChecked(False)
        else:
            dialog.in_ka_check.setChecked(True)
            dialog.in_ka.setValue(in_ka)
        
        dialog.z_ohm.setValue(node.get_property('z_ohm'))
        
        if dialog.exec():
            node.set_property('closed', dialog.closed.isChecked(), push_undo=False)
            
            pos_type = dialog.type.currentIndex()
            node.set_property('type', types[pos_type], push_undo=False)
            
            if dialog.in_ka_check.isChecked():
                node.set_property('in_ka', np.round(dialog.in_ka.value(), 6), push_undo=False)
            else:
                node.set_property('in_ka', float('NaN'), push_undo=False)
            
            node.set_property('z_ohm', np.round(dialog.z_ohm.value(), 6), push_undo=False)
            
            switch_index = node.get_property('switch_index')
            if switch_index is not None:
                for name in node.electrical_properties:
                    self.net.switch.loc[switch_index, name] = node.get_property(name)

            self.session_change_warning()
            
    def _on_node_name_changed2(self, node_id, name):
        """
        Executed when a node name is changed.
        """
        node = self.get_node_by_id(node_id)
        node.set_property('name', name)
        node.update_tooltip(self.net)
        type_ = node.get_property('type_')
        if type_=='BusNode.BusNode':
            bus_index = node.get_property('bus_index')
            self.net.bus.loc[bus_index, 'name'] = name
            four_ports_on_buses(node)
        elif type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode'):
            line_index = node.get_property('line_index')
            if line_index is not None:
                self.net.line.loc[line_index, 'name'] = name
        elif type_=='DCLineNode.DCLineNode':
            line_index = node.get_property('line_index')
            if line_index is not None:
                self.net.dcline.loc[line_index, 'name'] = name
        elif type_=='ImpedanceNode.ImpedanceNode':
            impedance_index = node.get_property('impedance_index')
            if impedance_index is not None:
                self.net.impedance.loc[impedance_index, 'name'] = name
        elif type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode'):
            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None:
                self.net.trafo.loc[transformer_index, 'name'] = name
        elif type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode'):
            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None:
                self.net.trafo3w.loc[transformer_index, 'name'] = name
        elif type_=='GenNode.GenNode':
            gen_index = node.get_property('gen_index')
            if gen_index is not None:
                self.net.gen.loc[gen_index, 'name'] = name
        elif type_=='SGenNode.SGenNode':
            gen_index = node.get_property('gen_index')
            if gen_index is not None:
                self.net.gen.loc[gen_index, 'name'] = name
        elif type_=='ASGenNode.ASGenNode':
            gen_index = node.get_property('gen_index')
            if gen_index is not None:
                self.net.asymmetric_sgen.loc[gen_index, 'name'] = name
        elif type_=='ExtGridNode.ExtGridNode':
            grid_index = node.get_property('grid_index')
            if grid_index is not None:
                self.net.ext_grid.loc[grid_index, 'name'] = name
        elif type_=='LoadNode.LoadNode':
            load_index = node.get_property('load_index')
            if load_index is not None:
                self.net.load.loc[load_index, 'name'] = name
        elif type_=='ALoadNode.ALoadNode':
            load_index = node.get_property('load_index')
            if load_index is not None:
                self.net.asymmetric_load.loc[load_index, 'name'] = name
        elif type_=='ShuntNode.ShuntNode':
            shunt_index = node.get_property('shunt_index')
            if shunt_index is not None:
                self.net.shunt.loc[shunt_index, 'name'] = name
        elif type_=='MotorNode.MotorNode':
            motor_index = node.get_property('motor_index')
            if motor_index is not None:
                self.net.motor.loc[motor_index, 'name'] = name
        elif type_=='WardNode.WardNode':
            ward_index = node.get_property('ward_index')
            if ward_index is not None:
                self.net.ward.loc[ward_index, 'name'] = name
        elif type_=='XWardNode.XWardNode':
            ward_index = node.get_property('ward_index')
            if ward_index is not None:
                self.net.xward.loc[ward_index, 'name'] = name
        elif type_=='StorageNode.StorageNode':
            storage_index = node.get_property('storage_index')
            if storage_index is not None:
                self.net.storage.loc[storage_index, 'name'] = name
        elif type_=='SwitchNode.SwitchNode':
            switch_index = node.get_property('switch_index')
            if switch_index is not None:
                self.net.switch.loc[switch_index, 'name'] = name
        
    def remove_bus(self, node):
        """
        Remove a bus from the pandapower network when its corresponding
        node in the graph is removed.
        """
        for sw in node.node_switch_connected():
            self.remove_switch(sw, directly_removed=False)
            self.delete_nodes([sw], push_undo=False)
        
        bus_index = node.get_property('bus_index')
        if bus_index in self.net.bus.index:
            pp.drop_buses(self.net, [bus_index])

    def remove_line(self, node, directly_removed=True):
        """
        Remove a line from the pandapower network when its corresponding
        node in the graph is removed.
        """
        if directly_removed:
            for sw in node.node_switch_connected():
                self.remove_switch(sw, directly_removed=False)
                self.delete_nodes([sw], push_undo=False)
        
        line_name = node.get_property('name')
        line_row = self.net.line[self.net.line['name']==line_name]
        if not line_row.empty:
            line_index = line_row.index[0]
            if line_index in self.net.line.index:
                pp.drop_lines(self.net, [line_index])

    def remove_dcline(self, node):
        """
        Remove a DC line from the pandapower network when its corresponding
        node in the graph is removed.
        """
        line_name = node.get_property('name')
        line_row = self.net.dcline[self.net.dcline['name']==line_name]
        if not line_row.empty:
            line_index = line_row.index[0]
            lines = [line_index]
            # drop_from_groups(self.net, "dcline", lines)
            drop_elements(self.net, "dcline", lines)
            # self.net["dcline"].drop(lines, inplace=True)
            # res_dclines = self.net.res_dcline.index.intersection(lines)
            # self.net["res_dcline"].drop(res_dclines, inplace=True)

    def remove_impedance(self, node):
        """
        Remove an impedance from the pandapower network when its corresponding
        node in the graph is removed.
        """
        impedance_name = node.get_property('name')
        impedance_row = self.net.impedance[self.net.impedance['name']==impedance_name]
        if not impedance_row.empty:
            impedance_index = impedance_row.index[0]
            impedances = [impedance_index]
            # drop_from_groups(self.net, "impedance", impedances)
            drop_elements(self.net, "impedance", impedances)
            # self.net["impedance"].drop(impedances, inplace=True)
            # res_impedances = self.net.res_impedance.index.intersection(impedances)
            # self.net["res_impedance"].drop(res_impedances, inplace=True)

    def remove_trafo(self, node, directly_removed=True):
        """
        Remove a two-winding transformer from the pandapower network when its corresponding
        node in the graph is removed.
        """
        if directly_removed:
            for sw in node.node_switch_connected():
                self.remove_switch(sw, directly_removed=False)
                self.delete_nodes([sw], push_undo=False)
                
        trafo_name = node.get_property('name')
        trafo_row = self.net.trafo[self.net.trafo['name']==trafo_name]
        if not trafo_row.empty:
            transformer_index = trafo_row.index[0]
            if transformer_index in self.net.trafo.index:
                pp.drop_trafos(self.net, [transformer_index], table='trafo')

    def remove_trafo3w(self, node, directly_removed=True):
        """
        Remove a three-winding transformer from the pandapower network when its corresponding
        node in the graph is removed.
        """
        if directly_removed:
            for sw in node.node_switch_connected():
                self.remove_switch(sw, directly_removed=False)
                self.delete_nodes([sw], push_undo=False)
        
        trafo_name = node.get_property('name')
        trafo_row = self.net.trafo3w[self.net.trafo3w['name']==trafo_name]
        if not trafo_row.empty:
            transformer_index = trafo_row.index[0]
            if transformer_index in self.net.trafo3w.index:
                pp.drop_trafos(self.net, [transformer_index], table='trafo3w')

    def remove_gen(self, node):
        """
        Remove a generator from the pandapower network when its corresponding
        node in the graph is removed.
        """
        gen_name = node.get_property('name')
        gen_row = self.net.gen[self.net.gen['name']==gen_name]
        if not gen_row.empty:
            gen_index = gen_row.index[0]
            gens = [gen_index]
            # drop_from_groups(self.net, "gen", gens)
            drop_elements(self.net, "gen", gens)
            # self.net["gen"].drop(gens, inplace=True)
            # res_gens = self.net.res_gen.index.intersection(gens)
            # self.net["res_gen"].drop(res_gens, inplace=True)

    def remove_sgen(self, node):
        """
        Remove a static generator from the pandapower network when its
        corresponding node in the graph is removed.
        """
        gen_name = node.get_property('name')
        gen_row = self.net.sgen[self.net.sgen['name']==gen_name]
        if not gen_row.empty:
            gen_index = gen_row.index[0]
            gens = [gen_index]
            # drop_from_groups(self.net, "sgen", gens)
            drop_elements(self.net, "sgen", gens)
            # self.net["sgen"].drop(gens, inplace=True)
            # res_sgens = self.net.res_sgen.index.intersection(gens)
            # self.net["res_sgen"].drop(res_sgens, inplace=True)

    def remove_asgen(self, node):
        """
        Remove an asymmetric static generator from the pandapower network when its
        corresponding node in the graph is removed.
        """
        gen_name = node.get_property('name')
        gen_row = self.net.asymmetric_sgen[self.net.asymmetric_sgen['name']==gen_name]
        if not gen_row.empty:
            gen_index = gen_row.index[0]
            gens = [gen_index]
            # drop_from_groups(self.net, "asymmetric_sgen", gens)
            drop_elements(self.net, "asymmetric_sgen", gens)
            # self.net["asymmetric_sgen"].drop(gens, inplace=True)
            #
            # res_asgens = self.net.res_asymmetric_sgen.index.intersection(gens)
            # self.net["res_asymmetric_sgen"].drop(res_asgens, inplace=True)

            res_asgens2 = self.net.res_asymmetric_sgen_3ph.index.intersection(gens)
            self.net["res_asymmetric_sgen_3ph"].drop(res_asgens2, inplace=True)

    def remove_ext_grid(self, node):
        """
        Remove an external grid from the pandapower network when its
        corresponding node in the graph is removed.
        """
        grid_name = node.get_property('name')
        grid_row = self.net.ext_grid[self.net.ext_grid['name']==grid_name]
        if not grid_row.empty:
            grid_index = grid_row.index[0]
            grids = [grid_index]
            # drop_from_groups(self.net, "ext_grid", grids)
            drop_elements(self.net, "ext_grid", grids)
            # self.net["ext_grid"].drop(grids, inplace=True)

            # res_grids = self.net.res_ext_grid.index.intersection(grids)
            # self.net["res_ext_grid"].drop(res_grids, inplace=True)

            res_grids2 = self.net.res_ext_grid_3ph.index.intersection(grids)
            self.net["res_ext_grid_3ph"].drop(res_grids2, inplace=True)

            res_grids3 = self.net.res_ext_grid_sc.index.intersection(grids)
            self.net["res_ext_grid_sc"].drop(res_grids3, inplace=True)

    def remove_load(self, node):
        """
        Remove a symmetric load from the pandapower network when its corresponding
        node in the graph is removed.
        """
        load_name = node.get_property('name')
        load_row = self.net.load[self.net.load['name'] == load_name]
        if not load_row.empty:
            load_index = node.get_property('load_index')
            if load_index is not None:
                pp.drop_elements_simple(self.net, 'load', load_index)

    def remove_aload(self, node):
        """
        Remove an asymmetric load from the pandapower network when its corresponding
        node in the graph is removed.
        """
        load_name = node.get_property('name')
        load_row = self.net.asymmetric_load[self.net.asymmetric_load['name'] == load_name]
        if not load_row.empty:
            load_index = node.get_property('load_index')
            if load_index is not None:
                pp.drop_elements_simple(self.net, 'asymmetric_load', load_index)

    def remove_shunt(self, node):
        """
        Remove a shunt element from the pandapower network when its corresponding
        node in the graph is removed.
        """
        shunt_name = node.get_property('name')
        shunt_row = self.net.shunt[self.net.shunt['name'] == shunt_name]
        if not shunt_row.empty:
            shunt_index = node.get_property('shunt_index')
            if shunt_index is not None:
                pp.drop_elements_simple(self.net, 'shunt', shunt_index)

    def remove_motor(self, node):
        """
        Remove a motor from the pandapower network when its corresponding
        node in the graph is removed.
        """
        motor_name = node.get_property('name')
        motor_row = self.net.motor[self.net.motor['name'] == motor_name]
        if not motor_row.empty:
            motor_index = node.get_property('motor_index')
            if motor_index is not None:
                pp.drop_elements_simple(self.net, 'motor', motor_index)

    def remove_ward(self, node):
        """
        Remove a ward from the pandapower network when its corresponding
        node in the graph is removed.
        """
        ward_name = node.get_property('name')
        ward_row = self.net.ward[self.net.ward['name'] == ward_name]
        if not ward_row.empty:
            ward_index = node.get_property('ward_index')
            if ward_index is not None:
                pp.drop_elements_simple(self.net, 'ward', ward_index)

    def remove_xward(self, node):
        """
        Remove an extended ward from the pandapower network when its corresponding
        node in the graph is removed.
        """
        xward_name = node.get_property('name')
        xward_row = self.net.xward[self.net.xward['name'] == xward_name]
        if not xward_row.empty:
            ward_index = node.get_property('ward_index')
            if ward_index is not None:
                pp.drop_elements_simple(self.net, 'xward', ward_index)

    def remove_storage(self, node):
        """
        Remove a storage from the pandapower network when its corresponding
        node in the graph is removed.
        """
        storage_name = node.get_property('name')
        storage_row = self.net.storage[self.net.storage['name'] == storage_name]
        if not storage_row.empty:
            storage_index = node.get_property('storage_index')
            if storage_index is not None and storage_index in self.net.storage.index:
                pp.drop_elements_simple(self.net, 'storage', storage_index)
            
    def remove_switch(self, node, directly_removed=True):
        """
        Remove a switch from the pandapower network when its corresponding
        node in the graph is removed.
        """
        node.set_locked(False)  # Necessary to remove the node
        switch_index = node.get_property('switch_index')
        if switch_index is not None:
            if switch_index in self.net.switch.index:
                pp.drop_elements_simple(self.net, 'switch', switch_index)
        
        if directly_removed:
            lines = node.node_line_connected()
            for line_node in lines:
                self.remove_line(line_node, directly_removed=False)
                
            trafos = node.node_trafo_connected()
            for trafo_node in trafos:
                self.remove_trafo(trafo_node, directly_removed=False)
            
            trafos3w = node.node_trafo3w_connected()
            for trafo3w_node in trafos3w:
                self.remove_trafo3w(trafo3w_node, directly_removed=False)

    def run_extension(self, name):
        """
        Run an extension.

        Args:
            name: Extension name

        Returns: None

        """
        ex_mod = self.extensions_dict[name]
        ex_obj = ex_mod.Extension(graph=self)
        ex_obj.set_name(name)

        if ex_obj.extension_window() is True:
            ex_obj.show_dialog()
        else:
            ex_obj.before_running()
            if ex_obj.separate_thread() is True:
                ex_wkr = ExtensionWorker(ex_obj)
                ex_wkr.signals.finished.connect(ex_obj.finish)
                ex_threadpool = QtCore.QThreadPool()
                ex_threadpool.start(ex_wkr)
            else:
                ex_obj()
                ex_obj.finish()

    def execute_extension(self):
        """
        Execute the selected extension.

        Returns: None

        """
        selector = self.main_window.findChild(QtWidgets.QComboBox, 'extension_selector')
        extension_name = selector.currentText()
        self.run_extension(extension_name)

    def update_extensions_list(self):
        """
        Update the extensions list in the combobox selector.

        Returns: None

        """
        selector = self.main_window.findChild(QtWidgets.QComboBox, 'extension_selector')
        btn = self.main_window.findChild(QtWidgets.QToolButton, 'extension_run_btn')
        selector.clear()
        if self.extensions_dict:
            selector.addItems(sorted(self.extensions_dict.keys()))
            btn.setEnabled(True)
        else:
            selector.addItem('<No extensions available>')
            btn.setEnabled(False)

    def update_widgets_properties(self):
        """
        Update the state of widgets inside the nodes when opening a session.

        Returns: None

        """
        dcline_nodes = self.get_nodes_by_type('DCLineNode.DCLineNode')
        for node in dcline_nodes:
            node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            line_index = node.get_property('line_index')
            if line_index is not None:
                try:
                    node.p_mw_widget.get_custom_widget().setValue(self.net.dcline.loc[line_index, 'p_mw'])
                except KeyError:
                    node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))

        trafo_nodes = self.get_nodes_by_type('TrafoNode.TrafoNode')
        for node in trafo_nodes:
            node.tap_pos_widget.get_custom_widget().setMinimum(node.get_property('tap_min'))
            node.tap_pos_widget.get_custom_widget().setMaximum(node.get_property('tap_max'))
            # node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))
            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None:
                try:
                    node.tap_pos_widget.get_custom_widget().setValue(self.net.trafo.loc[transformer_index, 'tap_pos'])
                except KeyError:
                    node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))

        std_trafo_nodes = self.get_nodes_by_type('StdTrafoNode.StdTrafoNode')
        for node in std_trafo_nodes:
            node.tap_pos_widget.get_custom_widget().setMinimum(node.get_property('tap_min'))
            node.tap_pos_widget.get_custom_widget().setMaximum(node.get_property('tap_max'))
            # node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))
            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None:
                try:
                    node.tap_pos_widget.get_custom_widget().setValue(self.net.trafo.loc[transformer_index, 'tap_pos'])
                except KeyError:
                    node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))

        trafo3w_nodes = self.get_nodes_by_type('Trafo3wNode.Trafo3wNode')
        for node in trafo3w_nodes:
            node.tap_pos_widget.get_custom_widget().setMinimum(node.get_property('tap_min'))
            node.tap_pos_widget.get_custom_widget().setMaximum(node.get_property('tap_max'))
            # node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))
            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None:
                try:
                    node.tap_pos_widget.get_custom_widget().setValue(self.net.trafo3w.loc[transformer_index, 'tap_pos'])
                except KeyError:
                    node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))

        std_trafo3w_nodes = self.get_nodes_by_type('StdTrafo3wNode.StdTrafo3wNode')
        for node in std_trafo3w_nodes:
            node.tap_pos_widget.get_custom_widget().setMinimum(node.get_property('tap_min'))
            node.tap_pos_widget.get_custom_widget().setMaximum(node.get_property('tap_max'))
            # node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))
            transformer_index = node.get_property('transformer_index')
            if transformer_index is not None:
                try:
                    node.tap_pos_widget.get_custom_widget().setValue(self.net.trafo3w.loc[transformer_index, 'tap_pos'])
                except KeyError:
                    node.tap_pos_widget.get_custom_widget().setValue(node.get_property('tap_pos'))

        gen_nodes = self.get_nodes_by_type('GenNode.GenNode')
        for node in gen_nodes:
            node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
            node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            node.vm_pu_widget.get_custom_widget().setMinimum(node.get_property('min_vm_pu'))
            node.vm_pu_widget.get_custom_widget().setMaximum(node.get_property('max_vm_pu'))

            gen_index = node.get_property('gen_index')
            if gen_index is not None:
                try:
                    node.p_mw_widget.get_custom_widget().setValue(self.net.gen.loc[gen_index, 'p_mw'])
                    node.vm_pu_widget.get_custom_widget().setValue(self.net.gen.loc[gen_index, 'vm_pu'])
                except KeyError:
                    node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
                    node.vm_pu_widget.get_custom_widget().setValue(node.get_property('vm_pu'))

        sgen_nodes = self.get_nodes_by_type('SGenNode.SGenNode')
        for node in sgen_nodes:
            node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
            node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            # node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
            node.q_mvar_widget.get_custom_widget().setMinimum(node.get_property('min_q_mvar'))
            node.q_mvar_widget.get_custom_widget().setMaximum(node.get_property('max_q_mvar'))
            # node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

            gen_index = node.get_property('gen_index')
            if gen_index is not None:
                try:
                    node.p_mw_widget.get_custom_widget().setValue(self.net.sgen.loc[gen_index, 'p_mw'])
                    node.q_mvar_widget.get_custom_widget().setValue(self.net.sgen.loc[gen_index, 'q_mvar'])
                except KeyError:
                    node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
                    node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

        # ext_grid_nodes = self.get_nodes_by_type('ExtGridNode.ExtGridNode')
        # for node in ext_grid_nodes:
        #     node.vm_pu_widget.get_custom_widget().setValue(node.get_property('vm_pu'))

        load_nodes = self.get_nodes_by_type('LoadNode.LoadNode')
        for node in load_nodes:
            node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
            node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            # node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
            node.q_mvar_widget.get_custom_widget().setMinimum(node.get_property('min_q_mvar'))
            node.q_mvar_widget.get_custom_widget().setMaximum(node.get_property('max_q_mvar'))
            # node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

            load_index = node.get_property('load_index')
            if load_index is not None:
                try:
                    node.p_mw_widget.get_custom_widget().setValue(self.net.load.loc[load_index, 'p_mw'])
                    node.q_mvar_widget.get_custom_widget().setValue(self.net.load.loc[load_index, 'q_mvar'])
                except KeyError:
                    node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
                    node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

        shunt_nodes = self.get_nodes_by_type('ShuntNode.ShuntNode')
        for node in shunt_nodes:
            # node.p_mw_widget.get_custom_widget().setMinimum(node.get_property('min_p_mw'))
            # node.p_mw_widget.get_custom_widget().setMaximum(node.get_property('max_p_mw'))
            # node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
            # node.q_mvar_widget.get_custom_widget().setMinimum(node.get_property('min_q_mvar'))
            # node.q_mvar_widget.get_custom_widget().setMaximum(node.get_property('max_q_mvar'))
            # node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

            shunt_index = node.get_property('shunt_index')
            if shunt_index is not None:
                try:
                    node.p_mw_widget.get_custom_widget().setValue(self.net.shunt.loc[shunt_index, 'p_mw'])
                    node.q_mvar_widget.get_custom_widget().setValue(self.net.shunt.loc[shunt_index, 'q_mvar'])
                except KeyError:
                    node.p_mw_widget.get_custom_widget().setValue(node.get_property('p_mw'))
                    node.q_mvar_widget.get_custom_widget().setValue(node.get_property('q_mvar'))

    def search_node(self):
        """
        Displays a dialog for searching nodes by name.
        """
        all_nodes = self.all_nodes()

        dialog = search_node_dialog(all_nodes)
        dialog.setWindowIcon(QtGui.QIcon(icon_path))
        main_win_rect = self.main_window.geometry()
        dialog.setParent(self.main_window)
        dialog.move(main_win_rect.center() - dialog.rect().center())  # centering in the main window

        def dialog_closed(result):
            if result:
                node = self.get_node_by_name(dialog.selected_node)
                if node is not None:
                    self.clear_selection()
                    node.set_selected(True)
                    self.fit_to_selection()
                    self.main_window.toolBox.setCurrentIndex(0)
                    simulate_ESC_key()
                    # if node.type_=='BusNode.BusNode':
                    #     four_ports_on_buses(node)
                    self.update_bus_ports()

            self.viewer().setFocus()
            simulate_ESC_key()
        
        dialog.finished.connect(dialog_closed)
        dialog.open()
        dialog.input_search.setFocus()

    def update_bus_ports(self):
        """Update port positions on bus nodes."""
        for node in self.all_nodes():
            if node.type_=='BusNode.BusNode':
                four_ports_on_buses(node)
