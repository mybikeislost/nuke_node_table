"""Custom knob editors where knobs.

Some knobs need to be translated into custom editor widgets to be editable.
"""

# Import third-party modules
import nuke
from Qt import QtGui  # pylint: disable=no-name-in-module
from Qt import QtWidgets  # pylint: disable=no-name-in-module


# Import local modules
from node_table import nuke_utils
from node_table import constants


class ArrayEditor(QtWidgets.QGroupBox):
    """Knob editor to allow changing multiple 'channels' of an Array_Knob."""

    def __init__(self, parent, length, rows=1,
                 decimals=constants.EDITOR_DECIMALS):
        """Widget to edit multiple float values at a time.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
            length (int): Number of elements in the knob's array.
            rows (int, optional): Split `length` by this many rows.
            decimals (float, optional): Number of decimals to display in the
                each `QDoubleSpinBox`.

        """
        super(ArrayEditor, self).__init__(parent)

        self.length = length
        self.rows = rows

        self.layout = QtWidgets.QGridLayout(self)
        self.setLayout(self.layout)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(4, 4, 4, 4)

        self.setAutoFillBackground(True)

        self.double_spin_boxes = []
        for i in range(length):
            spin_box = QtWidgets.QDoubleSpinBox(self)
            spin_box.setMinimumHeight(22)
            spin_box.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            spin_box.setDecimals(decimals)
            spin_box.setRange(-9999999, 99999999)
            col = i % rows
            row = int(float(i) / self.rows)
            self.layout.addWidget(spin_box, col, row)
            self.double_spin_boxes.append(spin_box)

        self.adjustSize()
        self.raise_()

    def set_editor_data(self, data):
        """Set data to editor.

        Args:
            data (:obj:`list` of :obj:`float`): The knob's value.

        """
        try:
            for i, value in enumerate(data):
                self.double_spin_boxes[i].setValue(value)
        except TypeError:
            # Set single values directly.
            self.double_spin_boxes[0].setValue(data)

    def get_editor_data(self):
        """Return the current editor data.

        Returns:
            list,tuple: list of double values

        """
        data = [v.value() for v in self.double_spin_boxes]
        return data


class ColorEditor(ArrayEditor):
    """Editor for the AColor_Knob.

    An extra button allows to pick a new value.

    """

    def __init__(self, parent, decimals=constants.EDITOR_DECIMALS):
        super(ColorEditor, self).__init__(parent=parent, length=4, rows=1,
                                          decimals=decimals)

        self.pick_button = None
        self._create_pick_button()

    def _create_pick_button(self):
        """Create the pick button and add it to the widget."""
        self.pick_button = QtWidgets.QPushButton()
        self.pick_button.clicked.connect(self.get_color)
        self.pick_button.setMaximumWidth(24)
        self.pick_button.setMaximumHeight(24)
        self.pick_button.setAutoFillBackground(True)
        self.layout.addWidget(self.pick_button, 0, 4)

    def set_editor_data(self, data):
        """Update the data on the editor.

        Args:
            data (:obj:`list` of :obj:`float`): Color to set editor to.

        """
        super(ColorEditor, self).set_editor_data(data)
        self._set_color_picker_button_color()

    def _set_color_picker_button_color(self):
        """Update the color of the pick button."""
        color = self.get_editor_data()[:3]
        color = [int(c * 255) for c in color]
        style_sheet = 'QPushButton {{background-color:rgb({},{},{})}}'.format(*color)
        self.pick_button.setStyleSheet(style_sheet)

    def get_color(self):
        """Set the editor to a color from nukes floating color picker."""
        initial_color_hex = nuke_utils.to_hex(self.get_editor_data())
        new_color = nuke_utils.to_rgb(nuke.getColor(initial_color_hex))
        self.set_editor_data(new_color)
        self._set_color_picker_button_color()
