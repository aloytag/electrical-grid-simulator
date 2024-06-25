# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# menu command functions
# ------------------------------------------------------------------------------

import os

from PySide6 import QtGui
import pandapower as pp

from lib.auxiliary import four_ports_on_buses

directory = os.path.dirname(__file__)
root_directory, _ = os.path.split(directory)
icon_app_path = os.path.join(root_directory, 'icons', 'app_icon.png')


def horizontal_layout(graph):
    """
    Set a horizontal layout for the selected nodes.
    """
    selected = graph.selected_nodes()
    for node in selected:
        if node.type_=='BusNode.BusNode':
            continue
        node.set_layout_direction(0)
        node.model.set_property('text_color', (255, 255, 255, 180))  # default color
        node.update()
        node.set_property('layout_vert', False, push_undo=False)
        # node.set_property('layout_direction', 0, push_undo=False)
        
    for node in selected:
        node.set_selected()


def vertical_layout(graph):
    """
    Set a vertical layout for the selected nodes.
    """
    theme = graph.config['general']['theme']
    selected = graph.selected_nodes()
    for node in selected:
        # if node.type_ in ('GenNode.GenNode', 'SGenNode.SGenNode', 'ASGenNode.ASGenNode'):
        #     continue
        if node.type_=='BusNode.BusNode':
            continue
        node.set_layout_direction(1)
        node.set_property('layout_vert', True, push_undo=False)
        # node.set_property('layout_direction', 1, push_undo=False)
        if theme=='light':
            node.model.set_property('text_color', (0, 0, 0, 255))  # black
            node.update()
            
    for node in selected:
        node.set_selected()

     
def clear_undo(graph):
    """
    Prompts a warning dialog to clear undo.
    """
    viewer = graph.viewer()
    msg = 'Clear all undo history, Are you sure?'
    if viewer.question_dialog('Clear Undo History', msg):
        graph.clear_undo_stack()
        

def show_undo_view(graph):
    """
    Show the undo list widget.
    """
    undo_view = graph.undo_view
    undo_view.setWindowIcon(QtGui.QIcon(icon_app_path))
    undo_view.show()


def delete_nodes(graph):
    """
    Delete selected node.
    """
    selected = graph.selected_nodes()
    if selected:
        graph.session_change_warning()
    for node in selected:
        if node.type_=='BusNode.BusNode':
            graph.remove_bus(node)
            inputs = list(node.connected_input_nodes().values())[0]
            outputs = list(node.connected_output_nodes().values())[0]
            for n in inputs + outputs:
                if n.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode'):
                    graph.remove_line(node)
                if n.type_=='DCLineNode.DCLineNode':
                    graph.remove_dcline(node)
                if n.type_=='ImpedanceNode.ImpedanceNode':
                    graph.remove_impedance(node)
                if n.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode'):
                    graph.remove_trafo(node)
                if n.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode'):
                    graph.remove_trafo3w(node)
                if n.type_=='GenNode.GenNode':
                    graph.remove_gen(node)
                if n.type_=='SGenNode.SGenNode':
                    graph.remove_sgen(node)
                if n.type_=='ASGenNode.ASGenNode':
                    graph.remove_asgen(node)
                if n.type_=='ExtGridNode.ExtGridNode':
                    graph.remove_ext_grid(node)
                if n.type_=='LoadNode.LoadNode':
                    graph.remove_load(node)
                if n.type_=='ALoadNode.ALoadNode':
                    graph.remove_aload(node)
                if n.type_=='ShuntNode.ShuntNode':
                    graph.remove_shunt(node)
                if n.type_=='MotorNode.MotorNode':
                    graph.remove_motor(node)
                if n.type_=='WardNode.WardNode':
                    graph.remove_ward(node)
                if n.type_=='XWardNode.XWardNode':
                    graph.remove_xward(node)
                if n.type_=='StorageNode.StorageNode':
                    graph.remove_storage(node)
                if n.type_=='SwitchNode.SwitchNode':
                    graph.remove_switch(node)
        elif node.type_ in ('LineNode.LineNode', 'StdLineNode.StdLineNode'):
            graph.remove_line(node)
        elif node.type_=='DCLineNode.DCLineNode':
            graph.remove_dcline(node)
        elif node.type_=='ImpedanceNode.ImpedanceNode':
            graph.remove_impedance(node)
        elif node.type_ in ('TrafoNode.TrafoNode', 'StdTrafoNode.StdTrafoNode'):
            graph.remove_trafo(node)
        elif node.type_ in ('Trafo3wNode.Trafo3wNode', 'StdTrafo3wNode.StdTrafo3wNode'):
            graph.remove_trafo3w(node)
        elif node.type_=='GenNode.GenNode':
            graph.remove_gen(node)
        elif node.type_=='SGenNode.SGenNode':
            graph.remove_sgen(node)
        elif node.type_=='ASGenNode.ASGenNode':
            graph.remove_asgen(node)
        elif node.type_=='ExtGridNode.ExtGridNode':
            graph.remove_ext_grid(node)
        elif node.type_=='LoadNode.LoadNode':
            graph.remove_load(node)
        elif node.type_=='ALoadNode.ALoadNode':
            graph.remove_aload(node)
        elif node.type_=='ShuntNode.ShuntNode':
            graph.remove_shunt(node)
        elif node.type_=='MotorNode.MotorNode':
            graph.remove_motor(node)
        elif node.type_=='WardNode.WardNode':
            graph.remove_ward(node)
        elif node.type_=='XWardNode.XWardNode':
            graph.remove_xward(node)
        elif node.type_=='StorageNode.StorageNode':
            graph.remove_storage(node)
        elif node.type_=='SwitchNode.SwitchNode':
            graph.remove_switch(node)
    
    graph.delete_nodes(graph.selected_nodes(), push_undo=False)
    
    
def select_all_nodes(graph):
    """
    Select all nodes.
    """
    graph.select_all()


def clear_node_selection(graph):
    """
    Clear node selection.
    """
    graph.clear_selection()
    
    
def disable_nodes(graph):
    """
    Toggle disable on selected nodes.
    """
    selected = graph.selected_nodes()
    graph.disable_nodes(selected)
    graph.update_bus_ports()
    
    
def zoom_in(graph):
    """
    Set the node graph to zoom in by 0.1
    """
    zoom = graph.get_zoom() + 0.1
    graph.set_zoom(zoom)


def zoom_out(graph):
    """
    Set the node graph to zoom in by 0.1
    """
    zoom = graph.get_zoom() - 0.2
    graph.set_zoom(zoom)


def reset_zoom(graph):
    """
    Reset zoom level.
    """
    graph.reset_zoom()
    
    
def fit_to_selection(graph):
    """
    Sets the zoom level to fit selected nodes.
    """
    graph.fit_to_selection()

    
def flip_nodes(graph):
    """
    Flip the selected nodes.
    """
    selected = graph.selected_nodes()
    for node in selected:
        node.flip()


def horizontal_alignment(graph):
    """
    Apply a horizontal alignment to selected nodes.
    """
    selected = graph.selected_nodes()
    if selected:
        last_node = selected[-1]
        pos = last_node.y_pos()
        for node in selected[:-1]:
            node.set_y_pos(pos)

        graph.update_bus_ports()


def vertical_alignment(graph):
    """
    Apply a vertical alignment to selected nodes.
    """
    selected = graph.selected_nodes()
    if selected:
        last_node = selected[-1]
        pos = last_node.x_pos()
        for node in selected[:-1]:
            node.set_x_pos(pos)

        graph.update_bus_ports()


def duplicate_nodes(graph):
    """
    Duplicates the selected nodes, with Switches as the only exception.
    """
    selected = graph.selected_nodes()
    for node in selected:
        if node.type_=='SwitchNode.SwitchNode':
            continue
        node_duplicated = list(graph.duplicate_nodes([node]))[0]
        input_ports = node_duplicated.input_ports()
        output_ports = node_duplicated.output_ports()
        for port_in in input_ports:
            port_in.clear_connections(push_undo=False)
        for port_out in output_ports:
            port_out.clear_connections(push_undo=False)
        if node_duplicated.type_=='BusNode.BusNode':
            bus_index = pp.create_bus(graph.net,
                                      name=node_duplicated.get_property('name'),
                                      vn_kv=graph.net.bus.at[node.get_property('bus_index'), 'vn_kv'],
                                      min_vm_pu=graph.net.bus.at[node.get_property('bus_index'), 'min_vm_pu'],
                                      max_vm_pu=graph.net.bus.at[node.get_property('bus_index'), 'max_vm_pu'],
                                      in_service=graph.net.bus.at[node.get_property('bus_index'), 'in_service'],
                                      geodata=node_duplicated.pos())
            node_duplicated.set_property('bus_index', bus_index, push_undo=False)
            four_ports_on_buses(node_duplicated)
            
            

def find_node(graph):
    """
    Shows the dialog for searching nodes.
    """
    graph.search_node()
