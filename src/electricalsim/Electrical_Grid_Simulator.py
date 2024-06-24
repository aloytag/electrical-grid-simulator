#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import importlib

from PySide6.QtUiTools import QUiLoader
from PySide6 import QtWidgets, QtGui, QtCore
import qdarktheme  # Always import after Qt
import qtawesome as qta

from lib.electricalGraph import ElectricalGraph
from lib.table_widget import TableWidgetWithMenu
from lib.auxiliary import QVLine, QMainWindow2, return_config
from lib.calculations import Run_PF
from icons import rc_icons
from version import VERSION

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


def main():
    """
    Execute the Electrical Grid Simulator (GUI).
    """
    directory = os.path.dirname(__file__)
    os.chdir(directory)
    
    # Reading the config file:
    config, config_file_path = return_config(directory)
    
    # qdarktheme.enable_hi_dpi()
    # app = QtWidgets.QApplication(sys.argv)
    # theme = config['general']['theme']
    # if theme in ('dark', 'light', 'auto'):
    #     qdarktheme.setup_theme(theme)
    
    ui_file = os.path.join(directory, 'ui', 'main_window.ui')
    ui_file_ = QtCore.QFile(ui_file)
    ui_file_.open(QtCore.QIODeviceBase.OpenModeFlag.ReadOnly)
    loader = QUiLoader()
    # main_window = loader.load(ui_file_)
    # window = QMainWindow2(main_window)

    qdarktheme.enable_hi_dpi()
    app = QtWidgets.QApplication(sys.argv)

    icon_splash_svg = os.path.join(directory, 'icons', 'splash_screen.svg')
    data_splash = None
    with open(icon_splash_svg, 'r') as banner:
        data_splash = banner.read().replace('&lt;VERSION&gt;', VERSION)
        directory_splash2, _ = os.path.split(config_file_path)
        icon_splash_svg2 = os.path.join(directory_splash2, 'egs_splash_screen.svg')
        banner2 = open(icon_splash_svg2, 'w')
        banner2.write(data_splash)
        banner2.close()

        pixmap_splash = QtGui.QPixmap(icon_splash_svg2)
        splash = QtWidgets.QSplashScreen(pixmap_splash)
        splash.show()
        app.processEvents()

    theme = config['general']['theme']
    if theme in ('dark', 'light', 'auto'):
        qdarktheme.setup_theme(theme, additional_qss="QToolTip { border: 0px; }")

    main_window = loader.load(ui_file_)
    window = QMainWindow2(main_window)
    
    icon_path = os.path.join(directory, 'icons', 'app_icon.png')
    window.setWindowIcon(QtGui.QIcon(icon_path))
    window.setWindowTitle('Electrical Grid Simulator')

    # Loading extensions:
    extensions = entry_points(group='electricalsim.extensions')
    extensions_dict = dict()
    for ex in extensions:
        extension_module = importlib.import_module(f'electricalsim_{ex.name}.extension')
        extensions_dict[ex.name] = extension_module
    
    graph = ElectricalGraph(config, config_file_path,
                            main_window=main_window,
                            extensions_dict=extensions_dict)
    graph.viewer().setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)

    # Toolbar settings------------------------------
    addBus_action = QtGui.QAction('addBus')
    addBus_action.setText('Bus')
    addBus_action.setToolTip('Add a bus')
    addBus_action.triggered.connect(graph.add_bus)
    addBus_action.setIcon(qta.icon('ph.git-commit'))
    main_window.toolBar.addAction(addBus_action)
    
    addLine_action = QtGui.QAction('addLine')
    addLine_action.setText('Line')
    addLine_action.setToolTip('Add a line')
    addLine_action.triggered.connect(graph.add_line)
    addLine_action.setIcon(qta.icon('ph.line-segment'))
    main_window.toolBar.addAction(addLine_action)
    
    addImpedance_action = QtGui.QAction('addImpedance')
    addImpedance_action.setText('Impedance')
    addImpedance_action.setToolTip('Add an impedance')
    addImpedance_action.triggered.connect(graph.add_impedance)
    addImpedance_action.setIcon(qta.icon('mdi6.alpha-z-box-outline'))
    main_window.toolBar.addAction(addImpedance_action)
    
    addTrafo_action = QtGui.QAction('addTrafo')
    addTrafo_action.setText('Transformer')
    addTrafo_action.setToolTip('Add a transformer')
    addTrafo_action.triggered.connect(graph.add_trafo)
    addTrafo_action.setIcon(qta.icon('ph.intersect'))
    main_window.toolBar.addAction(addTrafo_action)
    
    addGenerator_action = QtGui.QAction('addGenerator')
    addGenerator_action.setText('Generator')
    addGenerator_action.setToolTip('Add a generator')
    addGenerator_action.triggered.connect(graph.add_generator)
    addGenerator_action.setIcon(qta.icon('mdi6.alpha-g-circle-outline'))
    main_window.toolBar.addAction(addGenerator_action)
    
    addGrid_action = QtGui.QAction('addGrid')
    addGrid_action.setText('External Grid')
    addGrid_action.setToolTip('Add an external grid')
    addGrid_action.triggered.connect(graph.add_external_grid)
    addGrid_action.setIcon(qta.icon('mdi6.grid'))
    main_window.toolBar.addAction(addGrid_action)
    
    addLoad_action = QtGui.QAction('addLoad')
    addLoad_action.setText('Load')
    addLoad_action.setToolTip('Add a load')
    addLoad_action.triggered.connect(graph.add_load)
    addLoad_action.setIcon(qta.icon('mdi6.download-circle-outline'))
    main_window.toolBar.addAction(addLoad_action)
    
    addStorage_action = QtGui.QAction('addStorage')
    addStorage_action.setText('Storage')
    addStorage_action.setToolTip('Add a storage system')
    addStorage_action.triggered.connect(graph.add_storage)
    addStorage_action.setIcon(qta.icon('mdi6.battery-medium'))
    main_window.toolBar.addAction(addStorage_action)
    
    addSwitch_action = QtGui.QAction('addSwitch')
    addSwitch_action.setText('Switch')
    addSwitch_action.setToolTip('Add a switch')
    addSwitch_action.triggered.connect(graph.add_switch)
    addSwitch_action.setIcon(qta.icon('mdi6.electric-switch'))
    main_window.toolBar.addAction(addSwitch_action)
    # ----------------------------------------------
    
    main_window.layout_graph.addWidget(graph.widget)
      
    # Adding Bus DataFrame from pandapower network for the first time:
    df_bus_widget = TableWidgetWithMenu(graph.net.bus, graph)
    main_window.layout_bus.addWidget(df_bus_widget)
    
    # Adding Line DataFrame from pandapower network for the first time:
    df_line_widget = TableWidgetWithMenu(graph.net.line, graph)
    main_window.layout_line.addWidget(df_line_widget)
    
    # Adding DC Line DataFrame from pandapower network for the first time:
    df_dcline_widget = TableWidgetWithMenu(graph.net.dcline, graph)
    main_window.layout_dcline.addWidget(df_dcline_widget)
    
    # Adding Impedance DataFrame from pandapower network for the first time:
    df_impedance_widget = TableWidgetWithMenu(graph.net.impedance, graph)
    main_window.layout_impedance.addWidget(df_impedance_widget)
    
    # Adding Two Winding Transformer DataFrame from pandapower network for the first time:
    df_trafo_widget = TableWidgetWithMenu(graph.net.trafo, graph)
    main_window.layout_trafo.addWidget(df_trafo_widget)
    
    # Adding Three Winding Transformer DataFrame from pandapower network for the first time:
    df_trafo3w_widget = TableWidgetWithMenu(graph.net.trafo3w, graph)
    main_window.layout_trafo3w.addWidget(df_trafo3w_widget)
    
    # Adding Generator DataFrame from pandapower network for the first time:
    df_gen_widget = TableWidgetWithMenu(graph.net.gen, graph)
    main_window.layout_gen.addWidget(df_gen_widget)
    
    # Adding Static Generator DataFrame from pandapower network for the first time:
    df_sgen_widget = TableWidgetWithMenu(graph.net.sgen, graph)
    main_window.layout_sgen.addWidget(df_sgen_widget)
    
    # Adding Asymmetric Static Generator DataFrame from pandapower network for the first time:
    df_asgen_widget = TableWidgetWithMenu(graph.net.asymmetric_sgen, graph)
    main_window.layout_asgen.addWidget(df_asgen_widget)
    
    # Adding External Grid DataFrame from pandapower network for the first time:
    df_ext_grid_widget = TableWidgetWithMenu(graph.net.ext_grid, graph)
    main_window.layout_ext_grid.addWidget(df_ext_grid_widget)
    
    # Adding Symmetric Load DataFrame from pandapower network for the first time:
    df_load_widget = TableWidgetWithMenu(graph.net.load, graph)
    main_window.layout_load.addWidget(df_load_widget)
    
    # Adding Asymmetric Load DataFrame from pandapower network for the first time:
    df_aload_widget = TableWidgetWithMenu(graph.net.asymmetric_load, graph)
    main_window.layout_aload.addWidget(df_aload_widget)
    
    # Adding Shunt DataFrame from pandapower network for the first time:
    df_shunt_widget = TableWidgetWithMenu(graph.net.shunt, graph)
    main_window.layout_shunt.addWidget(df_shunt_widget)
    
    # Adding Motor DataFrame from pandapower network for the first time:
    df_motor_widget = TableWidgetWithMenu(graph.net.motor, graph)
    main_window.layout_motor.addWidget(df_motor_widget)
    
    # Adding Ward DataFrame from pandapower network for the first time:
    df_ward_widget = TableWidgetWithMenu(graph.net.ward, graph)
    main_window.layout_ward.addWidget(df_ward_widget)
    
    # Adding Extended Ward DataFrame from pandapower network for the first time:
    df_xward_widget = TableWidgetWithMenu(graph.net.xward, graph)
    main_window.layout_xward.addWidget(df_xward_widget)
    
    # Adding Storage DataFrame from pandapower network for the first time:
    df_storage_widget = TableWidgetWithMenu(graph.net.storage, graph)
    main_window.layout_storage.addWidget(df_storage_widget)
    
    # Adding Switch DataFrame from pandapower network for the first time:
    df_switch_widget = TableWidgetWithMenu(graph.net.switch, graph)
    main_window.layout_switch.addWidget(df_switch_widget)
    
    main_window.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
    
    # Icons for diferent sections on the main window:
    main_window.toolBox.setItemIcon(0, qta.icon('ph.share-network'))  # Graph section
    main_window.toolBox.setItemIcon(1, qta.icon('ph.table'))  # Model data section
    
    # Upper toolbar:
    icon_size = QtCore.QSize(36, 36)
    
    new_session = QtWidgets.QToolButton(main_window)
    new_session.setToolTip('New session (Ctrl+N)')
    new_session.setIconSize(icon_size)
    new_session.setIcon(qta.icon('mdi6.file-plus-outline'))
    main_window.layout_upper_toolbar.addWidget(new_session)
    new_session.clicked.connect(graph.new_session)
    
    open_session = QtWidgets.QToolButton(main_window)
    open_session.setToolTip('Open session (Ctrl+O)')
    open_session.setIconSize(icon_size)
    open_session.setIcon(qta.icon('mdi6.folder-outline'))
    main_window.layout_upper_toolbar.addWidget(open_session)
    open_session.clicked.connect(graph.open_session)
    
    save_session = QtWidgets.QToolButton(main_window)
    save_session.setToolTip('Save session (Ctrl+S)')
    save_session.setIconSize(icon_size)
    save_session.setIcon(qta.icon('mdi6.content-save-outline'))
    main_window.layout_upper_toolbar.addWidget(save_session)
    save_session.clicked.connect(graph.save_session)
    
    save_session_as = QtWidgets.QToolButton(main_window)
    save_session_as.setToolTip('Save session as... (Ctrl+W)')
    save_session_as.setIconSize(icon_size)
    save_session_as.setIcon(qta.icon('mdi6.content-save-edit-outline'))
    main_window.layout_upper_toolbar.addWidget(save_session_as)
    save_session_as.clicked.connect(graph.save_session_as)
    
    # main_window.layout_upper_toolbar.addWidget(QVLine())  # separator
    
    export_net = QtWidgets.QToolButton(main_window)
    export_net.setToolTip('Export pandapower network (Ctrl+E)')
    export_net.setIconSize(icon_size)
    export_net.setIcon(qta.icon('mdi6.database-export-outline'))
    main_window.layout_upper_toolbar.addWidget(export_net)
    export_net.clicked.connect(graph.export_net)
    
    main_window.layout_upper_toolbar.addWidget(QVLine())  # separator
    
    run_pf_btn = QtWidgets.QToolButton(main_window)
    run_pf_btn.setToolTip('Balanced AC power flow')
    run_pf_btn.setIconSize(icon_size)
    run_pf_btn.setIcon(qta.icon('mdi6.play-outline'))
    main_window.layout_upper_toolbar.addWidget(run_pf_btn)
    run_pf_btn.clicked.connect(Run_PF(graph))

    main_window.layout_upper_toolbar.addStretch()

    search_node_btn = QtWidgets.QToolButton(main_window)
    search_node_btn.setToolTip('Find node (Ctrl+F)')
    search_node_btn.setIconSize(icon_size)
    search_node_btn.setIcon(qta.icon('mdi6.map-search-outline'))
    main_window.layout_upper_toolbar.addWidget(search_node_btn)
    search_node_btn.clicked.connect(graph.search_node)

    main_window.layout_upper_toolbar.addWidget(QVLine())  # separator

    extensions_label = QtWidgets.QLabel(main_window)
    extensions_label.setText('Extensions:')
    extensions_combobox = QtWidgets.QComboBox(main_window)
    extensions_combobox.setObjectName('extension_selector')
    extensions_combobox.setMinimumSize(250, 0)
    extension_run_btn = QtWidgets.QToolButton(main_window)
    extension_run_btn.setObjectName('extension_run_btn')
    extension_run_btn.setToolTip('Execute the selected extension')
    extension_run_btn.setIconSize(icon_size)
    extension_run_btn.setIcon(qta.icon('mdi6.puzzle-outline'))
    main_window.layout_upper_toolbar.addWidget(extensions_label)
    main_window.layout_upper_toolbar.addWidget(extensions_combobox)
    main_window.layout_upper_toolbar.addWidget(extension_run_btn)
    extension_run_btn.clicked.connect(graph.execute_extension)
    
    main_window.layout_upper_toolbar.addStretch()
    
    net_settings = QtWidgets.QToolButton(main_window)
    net_settings.setToolTip('Basic network settings')
    net_settings.setIconSize(icon_size)
    net_settings.setIcon(qta.icon('mdi6.grid'))
    main_window.layout_upper_toolbar.addWidget(net_settings)
    net_settings.clicked.connect(graph.net_settings)
    
    edit_settings = QtWidgets.QToolButton(main_window)
    edit_settings.setToolTip('Settings and default parameters')
    edit_settings.setIconSize(icon_size)
    edit_settings.setIcon(qta.icon('mdi6.cog-outline'))
    main_window.layout_upper_toolbar.addWidget(edit_settings)
    edit_settings.clicked.connect(graph.edit_settings)

    main_window.menubar.setStyleSheet('border: 1px solid #d3d3d3')

    # Menubar:
    file_menu = main_window.menubar.addMenu('File')
    
    new_session_action = QtGui.QAction('newSession')
    new_session_action.setText('New session')
    new_session_action.triggered.connect(graph.new_session)
    new_session_action.setIcon(qta.icon('mdi6.file-plus-outline'))
    new_session_action.setShortcut(QtGui.QKeySequence('Ctrl+N'))
    file_menu.addAction(new_session_action)
    
    open_session_action = QtGui.QAction('openSession')
    open_session_action.setText('Open session')
    open_session_action.triggered.connect(graph.open_session)
    open_session_action.setIcon(qta.icon('mdi6.folder-outline'))
    open_session_action.setShortcut(QtGui.QKeySequence('Ctrl+O'))
    file_menu.addAction(open_session_action)
    
    save_session_action = QtGui.QAction('saveSession')
    save_session_action.setText('Save session')
    save_session_action.triggered.connect(graph.save_session)
    save_session_action.setIcon(qta.icon('mdi6.content-save-outline'))
    save_session_action.setShortcut(QtGui.QKeySequence('Ctrl+S'))
    file_menu.addAction(save_session_action)
    
    save_session_as_action = QtGui.QAction('saveSessionAs')
    save_session_as_action.setText('Save session as...')
    save_session_as_action.triggered.connect(graph.save_session_as)
    save_session_as_action.setIcon(qta.icon('mdi6.content-save-edit-outline'))
    save_session_as_action.setShortcut(QtGui.QKeySequence('Ctrl+Shift+S'))
    file_menu.addAction(save_session_as_action)
    
    file_menu.addSeparator()
    export_net_action = QtGui.QAction('exportNet')
    export_net_action.setText('Export pandapower network')
    export_net_action.triggered.connect(graph.export_net)
    export_net_action.setIcon(qta.icon('mdi6.database-export-outline'))
    export_net_action.setShortcut(QtGui.QKeySequence('Ctrl+E'))
    file_menu.addAction(export_net_action)
    
    component_menu = main_window.menubar.addMenu('Add component')
    component_actions = [addBus_action, addLine_action, addImpedance_action,
                         addTrafo_action, addGenerator_action, addGrid_action,
                         addLoad_action, addStorage_action, addSwitch_action]
    for component in component_actions:
        component_menu.addAction(component)
        
    settings_menu = main_window.menubar.addMenu('Settings')
    net_settings_action = QtGui.QAction('netSettings')
    net_settings_action.setText('Basic network settings')
    net_settings_action.triggered.connect(graph.net_settings)
    net_settings_action.setIcon(qta.icon('mdi6.grid'))
    settings_menu.addAction(net_settings_action)
    
    settings_menu.addSeparator()
    settings_action = QtGui.QAction('AppSettings')
    settings_action.setText('Settings and default parameters')
    settings_action.triggered.connect(graph.edit_settings)
    settings_action.setIcon(qta.icon('mdi6.cog-outline'))
    settings_menu.addAction(settings_action)
    
    help_menu = main_window.menubar.addMenu('Help')
    about_action = QtGui.QAction('About')
    about_action.setText('About this application')
    about_action.triggered.connect(graph.about)
    about_action.setIcon(qta.icon('mdi6.information-outline'))
    help_menu.addAction(about_action)
        
    def page_changed_on_toolbox(index):
        """
        Update pandapower data tables in the GUI.
        """
        if index==0:
            main_window.toolBar.setEnabled(True)
            component_menu.setEnabled(True)
        elif index==1:
            main_window.toolBar.setEnabled(False)
            component_menu.setEnabled(False)
            
            # Adding Bus DataFrame from pandapower network:
            old_bus_table = main_window.layout_bus.itemAt(0).widget()
            old_bus_table.setParent(None)
            df_bus_widget = TableWidgetWithMenu(graph.net.bus.copy(deep=True), graph)
            main_window.layout_bus.addWidget(df_bus_widget)
            
            # Adding Line DataFrame from pandapower network:
            old_line_table = main_window.layout_line.itemAt(0).widget()
            old_line_table.setParent(None)
            df_line_widget = TableWidgetWithMenu(graph.net.line.copy(deep=True), graph)
            main_window.layout_line.addWidget(df_line_widget)
            
            # Adding DC Line DataFrame from pandapower network:
            old_dcline_table = main_window.layout_dcline.itemAt(0).widget()
            old_dcline_table.setParent(None)
            df_dcline_widget = TableWidgetWithMenu(graph.net.dcline.copy(deep=True), graph)
            main_window.layout_dcline.addWidget(df_dcline_widget)
            
            # Adding Impedance DataFrame from pandapower network:
            old_impedance_table = main_window.layout_impedance.itemAt(0).widget()
            old_impedance_table.setParent(None)
            df_impedance_widget = TableWidgetWithMenu(graph.net.impedance.copy(deep=True), graph)
            main_window.layout_impedance.addWidget(df_impedance_widget)
            
            # Adding Two Winding Transformer DataFrame from pandapower network:
            old_trafo_table = main_window.layout_trafo.itemAt(0).widget()
            old_trafo_table.setParent(None)
            df_trafo_widget = TableWidgetWithMenu(graph.net.trafo.copy(deep=True), graph)
            main_window.layout_trafo.addWidget(df_trafo_widget)
            
            # Adding Three Winding Transformer DataFrame from pandapower network:
            old_trafo3w_table = main_window.layout_trafo3w.itemAt(0).widget()
            old_trafo3w_table.setParent(None)
            df_trafo3w_widget = TableWidgetWithMenu(graph.net.trafo3w.copy(deep=True), graph)
            main_window.layout_trafo3w.addWidget(df_trafo3w_widget)
            
            # Adding Generator DataFrame from pandapower network:
            old_gen_table = main_window.layout_gen.itemAt(0).widget()
            old_gen_table.setParent(None)
            df_gen_widget = TableWidgetWithMenu(graph.net.gen.copy(deep=True), graph)
            main_window.layout_gen.addWidget(df_gen_widget)
            
            # Adding Static Generator DataFrame from pandapower network:
            old_sgen_table = main_window.layout_sgen.itemAt(0).widget()
            old_sgen_table.setParent(None)
            df_sgen_widget = TableWidgetWithMenu(graph.net.sgen.copy(deep=True), graph)
            main_window.layout_sgen.addWidget(df_sgen_widget)
            
            # Adding Asymmetric Static Generator DataFrame from pandapower network:
            old_asgen_table = main_window.layout_asgen.itemAt(0).widget()
            old_asgen_table.setParent(None)
            df_asgen_widget = TableWidgetWithMenu(graph.net.asymmetric_sgen.copy(deep=True), graph)
            main_window.layout_asgen.addWidget(df_asgen_widget)
            
            # Adding External Grid DataFrame from pandapower network:
            old_ext_grid_table = main_window.layout_ext_grid.itemAt(0).widget()
            old_ext_grid_table.setParent(None)
            df_ext_grid_widget = TableWidgetWithMenu(graph.net.ext_grid.copy(deep=True), graph)
            main_window.layout_ext_grid.addWidget(df_ext_grid_widget)
            
            # Adding Symmetric Load DataFrame from pandapower network:
            old_load_table = main_window.layout_load.itemAt(0).widget()
            old_load_table.setParent(None)
            df_load_widget = TableWidgetWithMenu(graph.net.load.copy(deep=True), graph)
            main_window.layout_load.addWidget(df_load_widget)
            
            # Adding Asymmetric Load DataFrame from pandapower network:
            old_aload_table = main_window.layout_aload.itemAt(0).widget()
            old_aload_table.setParent(None)
            df_aload_widget = TableWidgetWithMenu(graph.net.asymmetric_load.copy(deep=True), graph)
            main_window.layout_aload.addWidget(df_aload_widget)
            
            # Adding Shunt DataFrame from pandapower network:
            old_shunt_table = main_window.layout_shunt.itemAt(0).widget()
            old_shunt_table.setParent(None)
            df_shunt_widget = TableWidgetWithMenu(graph.net.shunt.copy(deep=True), graph)
            main_window.layout_shunt.addWidget(df_shunt_widget)
            
            # Adding Motor DataFrame from pandapower network:
            old_motor_table = main_window.layout_motor.itemAt(0).widget()
            old_motor_table.setParent(None)
            df_motor_widget = TableWidgetWithMenu(graph.net.motor.copy(deep=True), graph)
            main_window.layout_motor.addWidget(df_motor_widget)
            
            # Adding Ward DataFrame from pandapower network:
            old_ward_table = main_window.layout_ward.itemAt(0).widget()
            old_ward_table.setParent(None)
            df_ward_widget = TableWidgetWithMenu(graph.net.ward.copy(deep=True), graph)
            main_window.layout_ward.addWidget(df_ward_widget)
            
            # Adding Extended Ward DataFrame from pandapower network:
            old_xward_table = main_window.layout_xward.itemAt(0).widget()
            old_xward_table.setParent(None)
            df_xward_widget = TableWidgetWithMenu(graph.net.xward.copy(deep=True), graph)
            main_window.layout_xward.addWidget(df_xward_widget)
            
            # Adding Storage DataFrame from pandapower network:
            old_storage_table = main_window.layout_storage.itemAt(0).widget()
            old_storage_table.setParent(None)
            df_storage_widget = TableWidgetWithMenu(graph.net.storage.copy(deep=True), graph)
            main_window.layout_storage.addWidget(df_storage_widget)
            
            # Adding Switch DataFrame from pandapower network:
            old_switch_table = main_window.layout_switch.itemAt(0).widget()
            old_switch_table.setParent(None)
            df_switch_widget = TableWidgetWithMenu(graph.net.switch.copy(deep=True), graph)
            main_window.layout_switch.addWidget(df_switch_widget)
            
    main_window.toolBox.currentChanged.connect(page_changed_on_toolbox)
    graph.page_changed_on_toolbox = page_changed_on_toolbox

    # Update the extensions list in the UI (combobox selector):
    graph.update_extensions_list()

    # Show main window:
    # main_window.show()
    window.show()
    # splash.finish(window)
    if data_splash is not None:
        QtCore.QTimer.singleShot(2000, splash, splash.close)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
