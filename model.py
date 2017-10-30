if __name__ == '__main__':
    from PySide2 import QtCore, QtGui, QtWidgets
    __binding__ = 'PySide2'
else:
    from Qt import QtCore, QtGui, QtWidgets, __binding__

import nuke


from NodeTable import nuke_utils
from NodeTable import constants


def scalar(tpl, sc):
    """multiply each value in tuple by scalar

    Args:
        tpl (tuple):
        scalar (float):

    Returns (touple):
        tpl * sc
    """

    return tuple([sc * t for t in tpl])


def get_palette(widget = None):
    app = QtWidgets.QApplication.instance() #tpye: QtWidget.QApplication
    return app.palette(widget)


def find_key_in_dict(dictionary, key_str, lower=True, first_only=False, substring = True):
    """find keys that include key

    TODO:
        test performance against:
        return list(key for k in d.iterkeys() if key_str in k.lower())

    Args:
        dictionary (dict): search this dictionary
        key_str (str): find this string in keys of dictionary
        lower (bool): case insensitive matching
        first_only (bool): return only first found key
    Returns:
        list: found keys
    """
    result = []
    for key in dictionary.keys():
        if lower:
            key = key.lower()
            key_str = key_str.lower()

        if substring:
            if key_str in key:
                if first_only:
                    return [key]
                else:
                    result.append(key)
        else:
            if key_str == key:
                if first_only:
                    return [key]
                else:
                    result.append(key)
    return result


class ListModel(QtCore.QAbstractItemModel):

    """replacement for QStringListModel that can't be created in the PySide2 API

    """

    def __init__(self, lst):
        super(ListModel, self).__init__()
        self.lst = lst

    def rowCount(self, *args, **kwargs):
        return len(self.lst)

    def index(self, row, column, parent):
        return self.createIndex(row, column, parent)

    def data(self, index, role):
        row = index.row()
        return self.lst[row]


class KnobStatesFilterModel(QtCore.QSortFilterProxyModel):
    """Filters columns by the knobs flags

    """

    def __init__(self, parent):
        super(KnobStatesFilterModel, self).__init__(parent)

        self._hidden_knobs = False
        self._disabled_knobs = False

    def filterAcceptsRow(self, row, parent):
        return True

    def filterAcceptsColumn(self, column, parent):
        knob = self.sourceModel().headerData(column, QtCore.Qt.Horizontal, QtCore.Qt.UserRole)

        accept = knob.visible() or self._hidden_knobs
        accept &= knob.enabled() or self._disabled_knobs

        return accept

    def set_hidden_knobs(self, hidden):
        self._hidden_knobs = hidden
        self.invalidateFilter()

    def set_disabled_knobs(self, disabled):
        self._disabled_knobs = disabled
        self.invalidateFilter()


class ListFilterModel(QtCore.QSortFilterProxyModel):
    """abstract class that defines how the filter is set

    The derived FilterProxyModel should do substring matching if
    length of filter is 1.
    """

    def __init__(self, parent, filter_delimiter=','):
        super(ListFilterModel, self).__init__(parent)
        self.filter_list = None
        self.filter_delimiter = filter_delimiter

    def set_filter(self, filter_str):
        filter_list = [filter_s.strip() for filter_s in filter_str.split(self.filter_delimiter)]
        self.filter_list = filter_list
        self.invalidateFilter()

    def match(self, string):
        matching = True

        if not self.filter_list:
            return matching

        if len(self.filter_list) > 1:
            matching = string in self.filter_list
        elif len(self.filter_list) == 1:
            matching = self.filter_list[0] in string

        return matching


class HeaderHorizontalFilterModel(ListFilterModel):
    """Filter by knob name

    """

    def __init__(self, parent):
        super(HeaderHorizontalFilterModel, self).__init__(parent)
        self.header_filter_horizontal = None
        self.header_filter_vertical = None

    def filterAcceptsColumn(self, column, parent):
        header_name = self.sourceModel().headerData(column, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
        return self.match(header_name)


class NodeNameFilterModel(ListFilterModel):
    def __init__(self, parent, filter_delimiter=','):
        super(NodeNameFilterModel, self).__init__(parent, filter_delimiter)

    def filterAcceptsRow(self, row, parent):
        if not self.filter_list:
            return True
        header_name = self.sourceModel().headerData(row, QtCore.Qt.Vertical, QtCore.Qt.DisplayRole)
        return self.match(header_name)


class NodeClassFilterModel(ListFilterModel):
    def __init__(self, parent, filter_delimiter=','):
        super(NodeClassFilterModel, self).__init__(parent, filter_delimiter)

    def filterAcceptsRow(self, row, parent):
        if not self.filter_list:
            return True
        node = self.sourceModel().headerData(row, QtCore.Qt.Vertical, QtCore.Qt.UserRole)
        node_class = node.Class()
        return self.match(node_class)


class EmptyColumnFilterModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent):
        super(EmptyColumnFilterModel, self).__init__(parent)

    def filterAcceptsRow(self, row, parent):
        return True

    def filterAcceptsColumn(self, column, parent):
        # TODO: optimize to no run constantly
        header_name = self.sourceModel().headerData(column, QtCore.Qt.Horizontal,
                                                    QtCore.Qt.DisplayRole)
        for row in xrange(self.sourceModel().rowCount()):
            node = self.sourceModel().headerData(row, QtCore.Qt.Vertical, QtCore.Qt.UserRole)
            if find_key_in_dict(node.knobs(), header_name, first_only=True, substring=False):
                return True
        return False


class NodeTableModel(QtCore.QAbstractTableModel):
    def __init__(self, node_list=None):
        super(NodeTableModel, self).__init__()

        self._node_list = node_list  # type: list
        self._header = []

        self.palette = get_palette()  # type: QtGui.QPalette

        if node_list:
            self.setup_model_data()

    def set_node_list(self, node_list):
        self.beginResetModel()
        self._node_list = node_list
        self.setup_model_data()
        self.endResetModel()

    def rowCount(self, parent):
        if parent.isValid():
            return 0

        if not self._node_list:
            return 0

        return len(self._node_list)

    def columnCount(self, parent):
        """

        Note: When implementing a table based model, PySide.QtCore.QAbstractItemModel.rowCount()
        should return 0 when the parent is valid.

        Args:
            parent (QtCore.QModelIndex): parent index

        Returns:
            int: number of columns
        """
        if parent.isValid():
            return 0

        if not self._node_list:
            return 0

        return len(self._header)

    def setup_model_data(self):

        self._header = []
        if not self._node_list:
            return

        knob_names = []
        if len(self._node_list) < 1:
            return
        for node in self._node_list:
            if node:
                # noinspection PyUnresolvedReferences
                for knob_name, knob in node.knobs().items():
                    if knob_name not in knob_names:
                        self._header.append(knob)
                        knob_names.append(knob.name())

        self._header = sorted(self._header, key=lambda s: s.name().lower())

    def data(self, index, role):
        """Returns the header data.

        For UserRole this returns the node or knob, depending on given orientation.

        Args:
            index (QtCore.QModelIndex): return headerData for this index
            role (QtCore.int): the current role
                QtCore.Qt.BackgroundRole: background color if knob is animated
                QtCore.Qt.EditRole: value of knob at current index
                QtCore.Qt.DisplayRole: current value of knob at current index as str
                QtCore.Qt.UserRole: the knob itself at current index

        Returns:
            object
        """

        row = index.row()
        col = index.column()

        if not self._node_list:
            self.setup_model_data()
            return None

        node = self._node_list[row]

        if not node:
            self.beginResetModel()
            self._node_list.remove(node)
            self.setup_model_data()
            self.endResetModel()
            return None

        knob = node.knob(self._header[col].name())

        if knob:

            if isinstance(knob, nuke.Boolean_Knob):
                if role == QtCore.Qt.CheckStateRole:
                    if knob.value():
                        return QtCore.Qt.Checked
                    else:
                        return QtCore.Qt.Unchecked
                if role == QtCore.Qt.DisplayRole:
                    return None
            elif isinstance(knob, nuke.IArray_Knob):
                if (role == QtCore.Qt.DisplayRole) or (role == QtCore.Qt.EditRole):
                    # dim = knob.dimensions()
                    width = knob.width()
                    height = knob.height()
                    value = [knob.value(i / width, i % width) for i in range(width * height)]
                    # return value
                    if role == QtCore.Qt.DisplayRole:
                        return str(value)
                    else:
                        return value
            elif isinstance(knob, nuke.Transform2d_Knob):
                if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                    matrix_list =[]
                    matrix = knob.value()
                    for i in range(len(matrix)):
                        matrix_list.append(matrix[i])

                    if role == QtCore.Qt.DisplayRole:
                        return str(matrix_list)
                    else:
                        return matrix_list

            # all other knobs:
            if role == QtCore.Qt.DisplayRole:
                try:
                    return str(knob.value())
                except Exception as exception:
                    print(exception)

            elif role == QtCore.Qt.EditRole:
                return knob.value()

            elif role == QtCore.Qt.UserRole:
                return knob

            elif role == QtCore.Qt.BackgroundRole:
                if knob.isAnimated():
                    # noinspection PyArgumentList
                    if knob.isKeyAt(nuke.frame()):
                        return QtGui.QBrush(QtGui.QColor().fromRgbF(constants.KNOB_HAS_KEY_AT_COLOR))
                    return QtGui.QBrush(QtGui.QColor().fromRgbF(constants.KNOB_ANIMTED_COLOR))

        if role == QtCore.Qt.BackgroundRole:
            color = nuke_utils.get_node_tile_color(node)
            if not row % 2:
                base = self.palette.base().color()  # type: QtGui.QColor
            else:
                base = self.palette.alternateBase().color()  # type: QtGui.QColor
            if not knob:
                mix = constants.CELL_MIX_NODE_COLOR_AMOUNT_NO_KNOB
            else:
                mix = constants.CELL_MIX_NODE_COLOR_AMOUNT_HAS_KNOB

            base_color = base.getRgbF()[:3]

            base_color_blend = scalar(base_color, 1.0 - mix)
            color_blend = scalar(color, mix)
            color = [sum(x) for x in zip(base_color_blend, color_blend)]
            return QtGui.QBrush(QtGui.QColor().fromRgbF(*color))

        return None

    @staticmethod
    def safe_string(string):
        """encodes unicode to string because nuke knobs don't accept unicode.

            Args:
                string: encode this string

            Returns:
                str: string encoded or string unchanged if not unicode
        """
        if isinstance(string, unicode):
            return string.encode('utf-8')
        else:
            return string

    def setData(self, index, value, role):
        """sets edited data to node

        Warnings:
            Currently this only works for a few knob types.
            Array knobs are not supported

        Args:
            index (QtCore.QModelIndex): current index
            value (object): new value
            role (QtCore.Qt.int): current Role. Only EditRole supported

        Returns:
            True if successfully set knob to new value, otherwise False
        """

        if role == QtCore.Qt.EditRole:
            row = index.row()
            col = index.column()
            node = self._node_list[row]
            knob_name = self.headerData(col, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
            node_knob = node.knob(knob_name)

            # TODO: extend for various Knob types
            if node_knob:
                edited = False
                if isinstance(value, (list, tuple)):

                    for i, v in enumerate(value):
                        frame = nuke.root()['frame'].value()
                        if node_knob.valueAt(frame, i) == v:
                            edited = True
                        else:
                            edited = node_knob.setValueAt(v, frame, i)
                else:
                    value = self.safe_string(value)
                    edited = node_knob.setValue(value) if node_knob.value() != value else True

                if edited:
                    # noinspection PyUnresolvedReferences
                    self.dataChanged.emit(index, index)
                    return True
                else:
                    print 'could not edit knob %s ' % knob_name
        return False

    def flags(self, index):
        """make cell selectable and editable if the corresponding knob is enabled

        This ensures that NukeX features can't be edited with nuke_i license.
        Args:
            index (QtCore.QModelIndex): current index

        Returns:
            QtCore.Qt.ItemFlag: flags for current cell
        """

        knob = self.data(index, QtCore.Qt.UserRole)  # type: nuke.Knob

        if not knob:
            return QtCore.Qt.NoItemFlags

        flags = 0

        if isinstance(knob, nuke.Boolean_Knob):
            flags |= QtCore.Qt.ItemIsUserCheckable

        if knob.enabled():
            flags |= QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled

            return flags

        return QtCore.Qt.NoItemFlags

    def headerData(self, section, orientation, role):
        """Returns the header data.

        For UserRole this returns the node or knob, depending on given orientation.

        Args:
            section (QtCore.int): return headerData for this section
            orientation (QtCore.Qt.Orientation): either QtCore.Qt.Horizontal or QtCore.Qt.Vertical
            role (QtCore.int): the current role.
                QtCore.Qt.DisplayRole: name of node or knob
                QtCore.Qt.UserRole: the node or knob itself
        """

        if orientation == QtCore.Qt.Horizontal:
            if section >= len(self._header):
                return None

            if role == QtCore.Qt.DisplayRole:
                return self._header[section].name()
            elif role == QtCore.Qt.UserRole:
                return self._header[section]
            return None

        elif orientation == QtCore.Qt.Vertical:
            if section >= len(self._node_list):
                return None

            node = self._node_list[section]  # type: nuke.Node
            if not node:
                # TODO: delete rows for deleted nodes
                return None
            else:
                if role == QtCore.Qt.DisplayRole:
                    return node.name()
                elif role == QtCore.Qt.UserRole:
                    return node
                elif role == QtCore.Qt.BackgroundRole:
                    return QtGui.QBrush(QtGui.QColor.fromRgbF(*(nuke_utils.get_node_tile_color(node))))
                elif role == QtCore.Qt.ForegroundRole:
                    return QtGui.QPen(QtGui.QColor.fromRgbF(*(nuke_utils.get_node_font_color(node))))
