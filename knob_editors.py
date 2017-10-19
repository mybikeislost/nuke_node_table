if __name__ == '__main__':
    from Qt import QtCore, QtGui, QtWidgets
    __binding__ = 'PySide2'
else:
    from Qt import QtCore, QtGui, QtWidgets, __binding__

import nuke

from NodeTable import nuke_utils


class ArrayEditor(QtWidgets.QGroupBox):

    def __init__(self, parent, length, rows = 1):
        super(ArrayEditor, self).__init__(parent)

        self.length = length
        self.rows = rows

        self.layout = QtWidgets.QGridLayout(self)
        self.setLayout(self.layout)

        self.layout.setContentsMargins(0,0,0,0)
        self.setContentsMargins(4, 4, 4, 4)

        self.setAutoFillBackground(True)

        self.doubleSpinBoxes = []
        for i in range(length):
            sp = QtWidgets.QDoubleSpinBox(self)
            sp.setMinimumHeight(22)
            sp.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            sp.setDecimals(8)
            sp.setRange(-9999999, 99999999)
            row = i % rows
            col = int( ((i) / float(self.length)  )*self.rows)
            self.layout.addWidget(sp, col , row )
            self.doubleSpinBoxes.append(sp)

        self.adjustSize()
        self.raise_()

    def setEditorData(self, data):
        for i, v in enumerate(data):
            self.doubleSpinBoxes[i].setValue(v)

    def getEditorData(self):
        data = [v.value() for v in self.doubleSpinBoxes]
        return data


class ColorEditor(ArrayEditor):

    def __init__(self, parent):
        super(ColorEditor, self).__init__(parent=parent, length=4, rows=1)

        # prefixes=['r', 'g', 'b', 'a']
        # for i, sp in enumerate(self.doubleSpinBoxes):
        #     sp.setPrefix(prefixes[i])

        self.pick_button = QtWidgets.QPushButton('c')
        self.pick_button.clicked.connect(self.get_color)
        self.pick_button.setMaximumWidth(32)
        self.layout.addWidget(self.pick_button, 0 ,4)


    def get_color(self):
        initial_color = self.getEditorData()
        new_color = nuke_utils.to_rgb(nuke.getColor(nuke_utils.to_hex(initial_color)))
        self.setEditorData(new_color)

