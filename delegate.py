# Keeping this for development to enable auto-completion.
# pylint: disable=no-name-in-module
if __name__ == '__main__':
    from PySide2 import QtCore, QtGui, QtWidgets
    __binding__ = 'PySide2'
else:
    from Qt import QtCore, QtGui, QtWidgets, __binding__


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
        """ Change the data in the model and the state of the checkbox.

        If the user presses the left mouse button and this cell is editable.
        Otherwise do nothing.
        """

        if not isinstance(index.data(QtCore.Qt.EditRole), bool):
            return super(CheckBoxDelegate, self).editorEvent(event,
                                                       model,
                                                       option,
                                                       index)

        if not (index.flags() & QtCore.Qt.ItemIsEditable):
            return False

        if event.button() == QtCore.Qt.LeftButton:
            checkbox_rect = self.get_check_box_rect(option)
            if checkbox_rect.contains(event.pos()):
                if event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                    self.setModelData(None, model, index)
                    self.parent().commitData(None)
                    pass
                return False
        return False

    def setModelData(self, editor, model, index):
        """ Toggle the boolean state in the model.
        """
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
