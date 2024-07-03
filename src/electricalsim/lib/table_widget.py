# -*- coding: utf-8 -*-

from PySide6 import QtCore, QtWidgets, QtGui
import qtawesome as qta


class TableModel(QtCore.QAbstractTableModel):

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return str(self._data.columns[section])

            if orientation == QtCore.Qt.Vertical:
                return str(self._data.index[section])

    def get_data(self):
        return self._data


class TableWidget(QtWidgets.QWidget):

    def __init__(self, data):
        super().__init__()

        self.table = QtWidgets.QTableView()

        self.model = TableModel(data)
        self.table.setModel(self.model)
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        self.adjust_content()
        
    def adjust_content(self):
        """
        Resize the columns width to content.
        """
        header = self.table.horizontalHeader()
        for i in range(self.model.columnCount(None)):
            # header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            # header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)


class TableWidgetWithMenu(TableWidget):
    """
    Same as TableWidget class but with context menu for the data model.
    """
    def __init__(self, data, graph):
        super().__init__(data)
        self.graph = graph

        self.menu = None  # Context menu
        self.row = None  # Table row when doing a right click
        self.column = None  # Table column when doing a right click

        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.generate_menu)

    @QtCore.Slot(QtCore.QPoint)
    def generate_menu(self, pos):
        """
        Show a context menu when right-clicking.
        """
        index = self.table.indexAt(pos)
        if index.isValid():
            self.row = index.row()
            self.column = index.column()

            self.menu = QtWidgets.QMenu(self)  # Context menu
            self.menu.setStyleSheet('border: 1px solid #d3d3d3')

            show_action = QtGui.QAction('Show component in the graph', self)
            show_action.setText('Show component in the graph')
            show_action.triggered.connect(self.show_component)
            show_action.setIcon(qta.icon('mdi6.eye-outline'))
            self.menu.addAction(show_action)

            copy_action = QtGui.QAction('Copy', self)
            copy_action.setText('Copy')
            copy_action.triggered.connect(self.copy)
            copy_action.setIcon(qta.icon('mdi6.content-copy'))
            self.menu.addAction(copy_action)

            self.menu.popup(QtGui.QCursor.pos())

    def show_component(self):
        """
        Show the selected component in the graph.
        """
        node_name = self.model.get_data().iloc[self.row, :]['name']
        node = self.graph.get_node_by_name(node_name)
        if node is not None:
            self.graph.clear_selection()
            node.set_selected(True)
            self.graph.fit_to_selection()
            node.update_tooltip(self.graph.net)
            self.graph.main_window.toolBox.setCurrentIndex(0)
            self.graph.update_bus_ports()

    def copy(self):
        """
        Copy selection to clipboard.
        """
        itemSelectionModel = self.table.selectionModel()
        selected_indexes = itemSelectionModel.selectedIndexes()
        first_selected = selected_indexes[0]
        last_selected = selected_indexes[-1]

        from_row = first_selected.row()
        to_row = last_selected.row()

        from_column = first_selected.column()
        to_column = last_selected.column()

        data_portion = self.model.get_data().iloc[from_row:to_row+1, from_column:to_column+1]
        data_portion.to_clipboard()
