from PySide2 import QtWidgets, QtGui, QtCore
import nuke

def to_hex(rgb):
    return  int('%02x%02x%02x%02x' % (rgb[0] * 255,
                                              rgb[1] * 255,
                                              rgb[2] * 255, 1), 16)

def to_rgb(hex):
    """hex to rgb
    Author: Ivan Busquets

    Args:
        hex: color in hex format

    Returns (tuple): color in 0-1 range

    """

    r = (0xFF & hex>> 24) / 255.0
    g = (0xFF & hex >> 16) / 255.0
    b = (0xFF & hex >> 8) / 255.0

    return r,g,b


class ArrayEditor(QtWidgets.QGroupBox):

    def __init__(self, parent, length, rows = 1):
        super(ArrayEditor, self).__init__(parent)

        self.length = length
        self.rows = rows

        self.layout = QtWidgets.QGridLayout(self)
        self.setLayout(self.layout)
        self.layout.setMargin(0)
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
            self.layout.addWidget(sp,  int( ((i) / float(self.length)  )*self.rows) , i )
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
        new_color = to_rgb(nuke.getColor(to_hex(initial_color)))
        self.setEditorData(new_color)

