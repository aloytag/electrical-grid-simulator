# -*- coding: utf-8 -*-

from Qt import QtCore, QtWidgets


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
