# Keeping this for development to enable auto-completion.
# pylint: disable=no-name-in-module
import math
if __name__ == '__main__':
    from PySide2 import QtCore, QtWidgets
    __binding__ = 'PySide2'
else:
    from Qt import QtCore, QtWidgets

# Import third-party modules
import nuke

# Import local modules
from node_table import constants
from node_table import knob_editors
from node_table import nuke_utils


class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    """ Delegate for editing bool values via a centered checkbox.

    Does not actually create a QCheckBox, but instead overrides the paint()
    method to draw the checkbox directly. Mouse events are handled by the
    editorEvent() method which updates the model's bool value.

    Author: Marcel Goldschen
    URL: https://github.com/marcel-goldschen-ohm/ModelViewPyQt/blob/master
            /CheckBoxDelegateQtCore.Qt.py#L71

    """
    def __init__(self, parent=None):
        super(CheckBoxDelegate, self).__init__(parent)

        # Get size of a standard checkbox.
        option_button = QtWidgets.QStyleOptionButton()
        self.default_check_box_rect = QtWidgets.QApplication.style().subElementRect(
            QtWidgets.QStyle.SE_CheckBoxIndicator, option_button, None)
        del option_button

        self.mouse_pressed_pos = None

    def createEditor(self, parent, option, index):
        """ Important, otherwise an editor is created if the user clicks in this cell.
        """
        if not isinstance(index.data(QtCore.Qt.EditRole), bool):
            return super(CheckBoxDelegate, self).createEditor(parent,
                                                              option,
                                                              index)

        return None

    def paint(self, painter, option, index):
        """ Paint a checkbox without the label.

        """
        super(CheckBoxDelegate, self).paint(painter, option, index)

        if not isinstance(index.data(QtCore.Qt.EditRole), bool):
            return

        checkbox = QtWidgets.QStyleOptionButton()
        checkbox.rect = self.get_check_box_rect(option)
        checked = index.data(QtCore.Qt.EditRole)

        checkbox.state |= QtWidgets.QStyle.State_Active
        if index.flags() & QtCore.Qt.ItemIsEditable:
            checkbox.state |= QtWidgets.QStyle.State_Enabled

        if checked:
            checkbox.state |= QtWidgets.QStyle.State_On
        else:
            checkbox.state |= QtWidgets.QStyle.State_Off

        style = QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_CheckBox, checkbox, painter)
        
    def editorEvent(self, event, model, option, index):
        """Change the data in the model and the state of the checkbox.

        If the user presses the left mouse button and this cell is editable.
        Otherwise do nothing.

        """
        if not isinstance(index.data(QtCore.Qt.EditRole), bool):
            return super(CheckBoxDelegate, self).editorEvent(event,
                                                             model,
                                                             option,
                                                             index)

        if not (index.flags() & QtCore.Qt.ItemIsEditable):
            return True

        if event.type() not in (QtCore.QEvent.Type.MouseButtonPress,
                                QtCore.QEvent.Type.MouseButtonRelease,
                                ):
            return super(CheckBoxDelegate, self).editorEvent(event,
                                                             model,
                                                             option,
                                                             index)

        if event.button() == QtCore.Qt.LeftButton:
            checkbox_rect = self.get_check_box_rect(option)
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                # Record the event pos at start of dragging selection.
                # Use it later to not update checkbox if the mouse ends on a checkbox
                # but did not start dragging in the same checkbox.
                self.mouse_pressed_pos = event.pos()

            elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                if checkbox_rect.contains(event.pos()):
                    # Prevent toggling checkbox when dragging selection.
                    if self.mouse_pressed_pos and checkbox_rect.contains(self.mouse_pressed_pos):
                        self.setModelData(None, model, index)
                        self.parent().commitData(None)
                self.mouse_pressed_pos = None
                return True

        return super(CheckBoxDelegate, self).editorEvent(event,
                                                         model,
                                                         option,
                                                         index)

    def setModelData(self, editor, model, index):
        """Toggle the boolean state in the model."""
        if not isinstance(index.data(QtCore.Qt.EditRole), bool):
            return super(CheckBoxDelegate, self).setModelData(editor,
                                                              model,
                                                              index)

        checked = not index.model().data(index, QtCore.Qt.EditRole)
        model.setData(index, checked, QtCore.Qt.EditRole)

    def get_check_box_rect(self, option=None, rect=None):
        """Get the centered rectangle of the checkbox to draw.

        Args:
            option (QtWidgets.QStyleOption, optional): The option describing the
                parameters used to draw the current item.
            rect(QtCore.QRect, optional): The rectangle of the current item.
                Can be used as alternative to `option`.

        Returns:
            QtCore.QRect: The rectangle of the checkbox.

        """
        rect = option.rect if option else rect

        # Center checkbox in option.rect.
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()
        check_box_top_left_corner = QtCore.QPoint(x + w / 2 -  self.default_check_box_rect.width() / 2,
                                                  y + h / 2 -  self.default_check_box_rect.height() / 2)
        return QtCore.QRect(check_box_top_left_corner, self.default_check_box_rect.size())


class KnobsItemDelegate(CheckBoxDelegate):
    """Delegate that offer custom editors for various nuke.Knob classes."""

    def __init__(self, parent):
        super(KnobsItemDelegate, self).__init__(parent)

    # pylint: disable=invalid-name
    def createEditor(self, parent, option, index):
        """

        Args:
            parent (QtWidgets.QWidget): parent widget
            option (QtWidget.QStyleOptionViewItem):
            index (QtCore.QModelIndex): current index

        Returns:
            new editor
        """
        model = index.model() # type: models.NodeTableModel
        # row = index.row() # type: int
        # column = index.column() # type: int

        knob = model.data(index, QtCore.Qt.UserRole)

        if isinstance(knob, (nuke.Array_Knob, nuke.Transform2d_Knob)):
            rows = 1
            if isinstance(knob, nuke.AColor_Knob):
                return knob_editors.ColorEditor(parent)

            elif isinstance(knob, nuke.ColorChip_Knob):
                # Allow enough precision to not loose
                return knob_editors.ColorEditor(parent, decimals=20)

            elif isinstance(knob, nuke.Boolean_Knob):
                return super(KnobsItemDelegate, self).createEditor(parent,
                                                                   option,
                                                                   index)

            elif isinstance(knob, nuke.Enumeration_Knob):

                combobox = QtWidgets.QComboBox(parent)
                for value in knob.values():
                    combobox.addItem(value)
                return combobox

            elif isinstance(knob, nuke.IArray_Knob):
                rows = knob.height()  # type: int

            elif isinstance(knob, nuke.Transform2d_Knob):
                rows = math.sqrt(len(model.data(index, QtCore.Qt.EditRole)))

            if isinstance(model.data(index, QtCore.Qt.EditRole),
                          (list, tuple)):
                items = len(model.data(index, QtCore.Qt.EditRole))
                return knob_editors.ArrayEditor(parent,
                                                items,
                                                rows)
        if isinstance(knob, nuke.Format_Knob):

            combobox = QtWidgets.QComboBox(parent)
            for format in nuke.formats():
                combobox.addItem(format.name())
            return combobox

        return super(KnobsItemDelegate, self).createEditor(parent,
                                                           option,
                                                           index)

    # pylint: disable=invalid-name
    def setEditorData(self, editor, index):
        """sets editor to knobs value

        Args:
            editor (QtWidgets.QWidget):
            index (QtCore.QModelIndex): current index

        Returns: None

        """
        model = index.model()
        data = model.data(index, QtCore.Qt.EditRole)
        knob = model.data(index, QtCore.Qt.UserRole)

        # AColorChip_Knob: Convert hex to RGB
        if isinstance(knob, nuke.ColorChip_Knob):
            if data == 0:  # No custom color is not set.
                node = knob.node()
                data = nuke.defaultNodeColor(node.Class())
            data = nuke_utils.to_rgb(data)
            return editor.set_editor_data(data)

        # Array knobs:
        if isinstance(data, (list, tuple)):
            editor.set_editor_data(data)
        else:
            super(KnobsItemDelegate, self).setEditorData(editor, index)

    # pylint: disable=invalid-name
    def setModelData(self, editor, model, index):
        """sets new value to model

        Args:
            editor (knob_editors.QWidget):
            model (QtCore.QAbstractTableModel):
            index (QtCore.QModelIndex): current index

        Returns:
            None

        """

        model = index.model()  # type: model.NodeTableModel

        knob = model.data(index, QtCore.Qt.UserRole)
        data = None

        # Array knobs:
        if isinstance(knob, (nuke.Array_Knob, nuke.Transform2d_Knob)):

            if isinstance(knob, nuke.Boolean_Knob):
                return super(KnobsItemDelegate, self).setModelData(editor,
                                                                   model,
                                                                   index)

            elif isinstance(knob, nuke.Enumeration_Knob):
                data = editor.currentText()

            elif isinstance(editor, knob_editors.ArrayEditor):
                data = editor.get_editor_data()

            if isinstance(knob, nuke.ColorChip_Knob):
                data = nuke_utils.to_hex(data)
                default_node_color = nuke.defaultNodeColor(knob.node().Class())
                if data == default_node_color:
                    data = 0

            if data:
                return model.setData(index, data, QtCore.Qt.EditRole)
            else:
                return super(KnobsItemDelegate, self).setModelData(editor,
                                                            model,
                                                            index)
        else:
            return super(KnobsItemDelegate, self).setModelData(editor,
                                                        model,
                                                        index)

    # pylint: disable=invalid-name
    def updateEditorGeometry(self, editor, option, index):
        """

        Args:
            editor (QtWidget.QWidget):
            option (QtWidget.QStyleOptionViewItem):
            index (QtCore.QModelIndex): current index

        Returns:
            None
        """
        model = index.model() # type: model.NodeTableModel
        column = index.column() # type: int

        knob = model.data(index, QtCore.Qt.UserRole)
        value = model.data(index, QtCore.Qt.EditRole)

        # Array knobs:
        if isinstance(knob, (nuke.Array_Knob, nuke.Transform2d_Knob)):
            if isinstance(knob, nuke.Boolean_Knob):
                super(KnobsItemDelegate, self).updateEditorGeometry(editor,
                                                                    option,
                                                                    index)
            elif isinstance(knob, nuke.Enumeration_Knob):
                super(KnobsItemDelegate, self).updateEditorGeometry(editor,
                                                                    option,
                                                                    index)
            else:
                rect = option.rect
                rows = columns = 0
                try:
                    rows, columns = knob.rows(), knob.columns()
                except AttributeError:
                    # Not an IArray_Knob.
                    columns = knob.width()
                except AttributeError:
                    # Not an Array_Knob.
                    pass

                if isinstance(knob, nuke.ColorChip_Knob):
                    columns = 4

                if any((rows, columns)):
                    if isinstance(knob, nuke.IArray_Knob):
                        rect.setWidth(constants.EDITOR_CELL_WIDTH *
                                      knob.width())
                        rect.setHeight(constants.EDITOR_CELL_HEIGHT *
                                       knob.height())

                    elif isinstance(knob, nuke.Transform2d_Knob):
                        root = math.sqrt(len(value))
                        width = constants.EDITOR_CELL_WIDTH * root
                        rect.setWidth(width)
                        rect.setHeight(constants.EDITOR_CELL_HEIGHT * root)

                    else:
                        if column == 0:
                            rect.adjust(0, 0, 100, 0)
                        else:
                            rect.adjust(-50, 0, 50, 0)

                    rect.setWidth(max(rect.width(),
                                      constants.EDITOR_CELL_WIDTH * columns))

                editor.setGeometry(rect)
        else:
            super(KnobsItemDelegate, self).updateEditorGeometry(editor,
                                                                option,
                                                                index)
