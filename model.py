"""models to server and filter nodes data to the view

"""

import logging

if __name__ == '__main__':
    from PySide2 import QtCore, QtGui, QtWidgets
    __binding__ = 'PySide2'
else:
    from Qt import QtCore, QtGui, QtWidgets, __binding__

import nuke


from NodeTable import nuke_utils
from NodeTable import constants


LOG = logging.getLogger(__name__)


def scalar(tpl, multiplier):
    """multiply each value in tuple by scalar

    Args:
        tpl (tuple):
        scalar (float):

    Returns (tuple):
        tpl * sc
    """

    return tuple([multiplier * t for t in tpl])


def get_palette(widget=None):
    """return the applications palette

    Args:
        widget: current widget (optional)

    Returns:

    """
    app = QtWidgets.QApplication.instance() #tpye: QtWidget.QApplication
    return app.palette(widget)


def find_substring_in_dict_keys(dictionary,
                                key_str,
                                lower=True,
                                first_only=False,
                                substring=True):
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


class StringListModel(QtCore.QAbstractItemModel):
    """replacement for QStringListModel that can't be created in the
    PySide2 API

    """

    def __init__(self, lst):
        super(StringListModel, self).__init__()
        self.lst = lst

    def rowCount(self, parent=QtCore.QModelIndex()):
        """ return length of the list

        Args:
            parent (QtCore.QModelIndex): parent index

        Returns:
            int: number of rows
        """
        return len(self.lst)

    def index(self, row, column, pointer):
        """build an index from given row column holding data in pointer

        Args:
            row (int): current row below parent
            column (int): current column below parent
            pointer (object): some data

        Returns:
            QtCore.QModelIndex: index at given row, column
        """
        return self.createIndex(row, column, pointer)

    def data(self, index, role):
        """return data at index for role

        As this is a string list model, we just return the string for all
        roles.

        Args:
            index (QtCore.QModelIndex): current index
            role (QtCore.Qt.ItemRole): item role (ignored)

        Returns:
            string: string at current index
        """
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
        """pass all data

        Args:
            row (int): current row
            parent (QtCore.QModelIndex): parent index

        Returns:
            bool: true for all rows
        """
        return True

    def filterAcceptsColumn(self, column, parent):
        """filter hidden and disabled knobs

        Warning: if this knob is filtered out, but another knob is visible,
        both are hidden.

        @ TODO: filter by row and column using the models flags

        Args:
            column (int): current column
            parent (QtCore.QModelIndex): parent index

        Returns:
            bool: true if shown or false if column is excluded
        """
        knob = self.sourceModel().headerData(column,
                                             QtCore.Qt.Horizontal,
                                             QtCore.Qt.UserRole)

        accept = knob.visible() or self._hidden_knobs
        accept &= knob.enabled() or self._disabled_knobs

        return accept

    @property
    def hidden_knobs(self):
        """hidden knobs filter

        Returns:
            bool: true if hidden knobs are shown
        """
        return self._hidden_knobs

    @hidden_knobs.setter
    def hidden_knobs(self, hidden):
        self._hidden_knobs = hidden
        self.invalidateFilter()

    @property
    def disabled_knobs(self):
        """disabled knobs filter

        Returns:
            bool: true if disabled knobs are shown
        """
        return self.disabled_knobs

    @disabled_knobs.setter
    def disabled_knobs(self, disabled):
        self._disabled_knobs = disabled
        self.invalidateFilter()


class ListFilterModel(QtCore.QSortFilterProxyModel):
    """abstract class that defines how the filter is set

    The derived FilterProxyModel should do substring matching if
    length of filter is 1.
    """

    def __init__(self, parent, filter_delimiter=constants.FILTER_DELIMITER):
        super(ListFilterModel, self).__init__(parent)
        self.filter_list = None
        self.filter_delimiter = filter_delimiter

    def set_filter_str(self, filter_str):
        """set filter as string with delimiter

        Args:
            filter_str (str): filter

        Returns:
            None
        """
        filter_list = [filter_s.strip() for filter_s
                       in filter_str.split(self.filter_delimiter)]
        self.filter_list = filter_list
        self.invalidateFilter()

    def match(self, string):
        """check if string is in filter_list or if it is substring when
        filtering by one item only.

        Args:
            string (str): match this string against filter

        Returns:
            bool: true if string is in filter_list
        """
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

    def filterAcceptsColumn(self, column, parent):
        """filter header with set filter

        Args:
            column (int): current column
            parent (QtCore.QModelIndex():

        Returns:
            bool: true if header matches filter
        """
        if not self.filter_list:
            return True

        header_name = self.sourceModel().headerData(column,
                                                    QtCore.Qt.Horizontal,
                                                    QtCore.Qt.DisplayRole)
        return self.match(header_name)

class NodeNameFilterModel(ListFilterModel):
    """match node name from vertical header against filter

    """
    def __init__(self, parent):
        super(NodeNameFilterModel, self).__init__(parent)

    def filterAcceptsRow(self, row, parent):
        """filter header with set filter

        Args:
            row (int): current row
            parent (QtCore.QModelIndex():

        Returns:
            bool: true if header matches filter
        """
        if not self.filter_list:
            return True

        header_name = self.sourceModel().headerData(row,
                                                    QtCore.Qt.Vertical,
                                                    QtCore.Qt.DisplayRole)
        return self.match(header_name)


class NodeClassFilterModel(ListFilterModel):
    """filter by node classes

    """
    def __init__(self, parent):
        super(NodeClassFilterModel, self).__init__(parent)

    def filterAcceptsRow(self, row, parent):
        if not self.filter_list:
            return True
        node = self.sourceModel().headerData(row,
                                             QtCore.Qt.Vertical,
                                             QtCore.Qt.UserRole)
        node_class = node.Class()
        return self.match(node_class)


class EmptyColumnFilterModel(QtCore.QSortFilterProxyModel):
    """filter out every empty column

    Notes:
        this is quire expensive it seems
    """
    def __init__(self, parent):
        super(EmptyColumnFilterModel, self).__init__(parent)

    def filterAcceptsRow(self, row, parent):
        """no filtering here

        Args:
            row (int): current row
            parent (QtCore.QModelIndex:

        Returns:
            bool: True for all rows (nodes)
        """
        return True

    def filterAcceptsColumn(self, column, parent):
        """for every node check if current columns name is in its knobs

        Args:
            column (int): current column
            parent (QtCore.QModelIndex):

        Returns:
            bool: true if at least one node has a knob for current column
        """
        # TODO: optimize to no run constantly
        header_name = self.sourceModel().headerData(column,
                                                    QtCore.Qt.Horizontal,
                                                    QtCore.Qt.DisplayRole)

        for row in range(self.sourceModel().rowCount()):
            node = self.sourceModel().headerData(row, QtCore.Qt.Vertical,
                                                 QtCore.Qt.UserRole)
            if header_name in node.knobs():
                return True
        return False


class NodeTableModel(QtCore.QAbstractTableModel):
    """hold and serve the nodes data
    """
    def __init__(self, nodes=None):
        super(NodeTableModel, self).__init__()

        self._node_list = nodes or []  # type: list
        self._header = []  # type: list

        self.palette = get_palette()  # type: QtGui.QPalette

        if nodes:
            self.setup_model_data()


    @property
    def node_list(self):
        """current list of nodes

        Returns:
            list: list of nuke.Node
        """
        return self._node_list

    @node_list.setter
    def node_list(self, nodes):

        self.beginResetModel()
        self._node_list = nodes
        self.setup_model_data()
        self.endResetModel()

    def rowCount(self, parent):
        """number of nodes

        Args:
            parent (QtCore.QModelIndex): parent index

        Returns:
            int: number of nodes
        """
        if parent.isValid():
            return 0

        if not self.node_list:
            return 0

        return len(self.node_list)

    def columnCount(self, parent):
        """

        Note: When implementing a table based model,
        PySide.QtCore.QAbstractItemModel.rowCount()
        should return 0 when the parent is valid.

        Args:
            parent (QtCore.QModelIndex): parent index

        Returns:
            int: number of columns
        """
        if parent.isValid():
            return 0

        if not self.node_list:
            return 0

        return len(self._header)

    def setup_model_data(self):
        """read all knob names from set self.node_list to define header.

        Returns:

        """

        self._header = []
        if not self.node_list:
            return

        knob_names = []
        if len(self.node_list) < 1:
            return
        for node in self.node_list:
            if node:
                # noinspection PyUnresolvedReferences
                for knob_name, knob in node.knobs().items():
                    if knob_name not in knob_names:
                        self._header.append(knob)
                        knob_names.append(knob.name())

        self._header = sorted(self._header, key=lambda s: s.name().lower())

    def removeRows(self, parent, first, last):

        self.beginRemoveRows(parent, first, last)
        LOG.debug('Removing rows: %s to %s', first, last)
        for i in reversed(range(first, last+1)):
            self._node_list.pop(i)
        self.endRemoveRows()
        return

    def data(self, index, role):
        """Returns the header data.

        For UserRole this returns the node or knob, depending on given
        orientation.

        Args:
            index (QtCore.QModelIndex): return headerData for this index
            role (QtCore.int): the current role
                QtCore.Qt.BackgroundRole: background color if knob is animated
                QtCore.Qt.EditRole: value of knob at current index
                QtCore.Qt.DisplayRole: current value of knob as str
                QtCore.Qt.UserRole: the knob itself at current index

        Returns:
            object
        """

        row = index.row()
        col = index.column()

        if not self.node_list:
            self.setup_model_data()
            return

        node = self.node_list[row]

        if not nuke_utils.node_exists(node):
            self.removeRows(QtCore.QModelIndex(), row, row)
            self.setup_model_data()
            return

        knob = node.knob(self._header[col].name())

        if role == QtCore.Qt.BackgroundRole:
            if knob and knob.isAnimated():
                # noinspection PyArgumentList
                if knob.isKeyAt(nuke.frame()):
                    return QtGui.QBrush(QtGui.QColor().fromRgbF(
                        *constants.KNOB_HAS_KEY_AT_COLOR))
                return QtGui.QBrush(QtGui.QColor().fromRgbF(
                    *constants.KNOB_ANIMATED_COLOR))

            else:
                color = nuke_utils.get_node_tile_color(node)
                if not row % 2:
                    base = self.palette.base().color()  # type: QtGui.QColor
                else:
                    base = self.palette.alternateBase().color()

                if knob:
                    mix = constants.CELL_MIX_NODE_COLOR_AMOUNT_HAS_KNOB
                else:
                    mix = constants.CELL_MIX_NODE_COLOR_AMOUNT_NO_KNOB

                base_color = base.getRgbF()[:3]

                # Blend Nodes color with base color
                base_color_blend = scalar(base_color, 1.0 - mix)
                color_blend = scalar(color, mix)
                color = [sum(x) for x in zip(base_color_blend, color_blend)]
                return QtGui.QBrush(QtGui.QColor().fromRgbF(*color))

        # Return early if node has no knob at current index.
        # Further data roles require a knob.
        if not knob:
            return

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
                value = [knob.value(i / width, i % width)
                         for i in range(width * height)]
                # return value
                if role == QtCore.Qt.DisplayRole:
                    return str(value)
                else:
                    return value
        elif isinstance(knob, nuke.Transform2d_Knob):
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                matrix_list = []
                matrix = knob.value()
                for i in range(len(matrix)):
                    matrix_list.append(matrix[i])

                if role == QtCore.Qt.DisplayRole:
                    return str(matrix_list)
                else:
                    return matrix_list
        if role == QtCore.Qt.DisplayRole:
            try:
                return str(knob.value())
            except Exception as exception:
                LOG.warn('Could not get value from knob %s on node %s',
                         knob.name(),
                         node.name(),
                         exc_info=True)
            # all other knobs:


        elif role == QtCore.Qt.EditRole:
            return knob.value()

        elif role == QtCore.Qt.UserRole:
            return knob

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
        if not index.isValid():
            return

        if role == QtCore.Qt.EditRole:
            row = index.row()
            col = index.column()
            node = self.node_list[row]
            knob_name = self.headerData(col,
                                        QtCore.Qt.Horizontal,
                                        QtCore.Qt.DisplayRole)
            knob = node.knob(knob_name)

            if knob:
                edited = False
                if isinstance(value, (list, tuple)):

                    for i, val in enumerate(value):
                        frame = nuke.root()['frame'].value()
                        if knob.valueAt(frame, i) == val:
                            edited = True
                        else:
                            edited = knob.setValueAt(val, frame, i)
                else:
                    value = self.safe_string(value)
                    edited = knob.setValue(value) \
                        if knob.value() != value else True

                if edited:
                    # noinspection PyUnresolvedReferences
                    self.dataChanged.emit(index, index)
                    return True
                else:
                    LOG.warn('could not edit knob %s ', knob_name)
        return False

    def flags(self, index):
        """cell selectable and editable if the corresponding knob is enabled

        This ensures that NukeX features can't be edited with nuke_i license.
        Args:
            index (QtCore.QModelIndex): current index

        Returns:
            QtCore.Qt.ItemFlag: flags for current cell
        """
        row = index.row()

        node = self.node_list[row]
        if not nuke_utils.node_exists(node):
            self.removeRows(QtCore.QModelIndex(), row, row)
            return 0

        knob = self.data(index, QtCore.Qt.UserRole)  # type: nuke.Knob

        if not knob:
            return QtCore.Qt.NoItemFlags

        flags = 0

        if isinstance(knob, nuke.Boolean_Knob):
            flags |= QtCore.Qt.ItemIsUserCheckable

        if knob.enabled():
            flags |= QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

            if not isinstance(knob, tuple(constants.READ_ONLY_KNOBS)):
                flags |= QtCore.Qt.ItemIsEnabled

            return flags

        return QtCore.Qt.NoItemFlags

    def headerData(self, section, orientation, role):
        """Returns the header data.

        For UserRole this returns the node or knob, depending on given
        orientation.

        Args:
            section (QtCore.int): return headerData for this section
            orientation (QtCore.Qt.Orientation): header orientation
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
            if section >= len(self.node_list):
                return None

            node = self.node_list[section]  # type: nuke.Node
            if not node:
                # TODO: delete rows for deleted nodes
                return None
            else:
                if role == QtCore.Qt.DisplayRole:
                    return node.name()
                elif role == QtCore.Qt.UserRole:
                    return node
                elif role == QtCore.Qt.BackgroundRole:
                    return QtGui.QBrush(QtGui.QColor.fromRgbF(
                        *(nuke_utils.get_node_tile_color(node))))
                elif role == QtCore.Qt.ForegroundRole:
                    return QtGui.QPen(QtGui.QColor.fromRgbF(
                        *(nuke_utils.get_node_font_color(node))))
