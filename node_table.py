import sys
import os

nuke_loaded = True
try:
    import nuke
except ImportError:
    nuke_loaded = False

if __name__ == '__main__':
    from PySide2 import QtCore, QtGui, QtWidgets
    __binding__ = 'PySide2'
else:
    from Qt import QtCore, QtGui, QtWidgets, __binding__

from NodeTable import knob_editors



def get_unique(seq):
    """returns all unique items in of a list of strings

    Args:
        seq (list): list of strings

    Returns:
        list: unique items
    """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def get_node_classes(no_ext=True):
    """returns list of all available node classes (plugins)

    Args:
        no_ext: strip extension to return only class name

    Returns:
        list: available node classes
    """
    if nuke_loaded:
        plugins = nuke.plugins(nuke.ALL | nuke.NODIR, "*." + nuke.PLUGIN_EXT)
    else:
        plugins = ['Merge2', 'Mirror', 'Transform']
    plugins = get_unique(plugins)
    if no_ext:
        plugins = [os.path.splitext(plugin)[0] for plugin in plugins]

    return plugins


def select_node(node, zoom = 1):
    """selects and (optionally) zooms DAG to given node.

    Warnings:
        If name of node inside a group is given,
        the surrounding group will be selected instead of the node

    Args:
        node (nuke.Node, str): node or name of node. If name of node inside a group is given,
            the surrounding group will be selected instead of the node.
        zoom (int): optionally zoom to given node. If zoom = 0, no DAG will not zoom to given node.

    Returns:
        None
    """
    # deselecting all nodes:  looks stupid but works in non-commercial mode
    nuke.selectAll()
    nuke.invertSelection()

    if isinstance(node, basestring):
        # if node is part of a group: select the group
        if "." in node:
            node_name = node.split(".")[0]
            node = nuke.toNode(node_name)

    if node:
        node['selected'].setValue(True)
        if zoom:
            nuke.zoom(zoom, [node.xpos(), node.ypos()])


def find_substring_in_dict_keys(dictionary, key_str, lower=True, first_only=False):
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
        if key_str in key:
            if first_only:
                return [key]
            else:
                result.append(key)
    return result


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
            if find_substring_in_dict_keys(node.knobs(), header_name, first_only=True):
                return True
        return False


class NodeTableModel(QtCore.QAbstractTableModel):

    def __init__(self, node_list=None):
        super(NodeTableModel, self).__init__()

        self._node_list = node_list  # type: list
        self._header = []

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

        if len(self._node_list) < 1:
            return
        for node in self._node_list:
            if node:
                # noinspection PyUnresolvedReferences
                for knob_name, knob in node.knobs().iteritems():
                    if knob_name not in [knob_header.name() for knob_header in self._header]:
                        self._header.append(knob)
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
                        return QtGui.QBrush(QtGui.QColor().fromRgbF(0.165186, 0.385106, 0.723738))
                    return QtGui.QBrush(QtGui.QColor().fromRgbF(0.312839, 0.430188, 0.544651))
        else:
            if role == QtCore.Qt.BackgroundRole:
                return QtGui.QBrush(QtGui.QColor().fromHsvF(0.0, 0.0, 0.3))

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
            node_knob = node.knob(self._header[col].name())

            # TODO: extend for various Knob types
            if node_knob:
                if isinstance(value, list):
                    for i, v in enumerate(value):
                        v = self.safe_string(v)
                        edited = node_knob.setValueAt(v, nuke.root()['frame'].value(),  i )

                else:
                    value = self.safe_string(value)
                    edited = node_knob.setValue(value)

                if edited:
                    # noinspection PyUnresolvedReferences
                    self.dataChanged.emit(index, index)
                    return True
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


class KnobsItemDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, parent):
        super(KnobsItemDelegate, self).__init__()
        self.parent = parent

    def createEditor(self, parent, option, index):
        """

        Args:
            parent (QtWidgets.QWidget): parent widget
            option (QtWidget.QStyleOptionViewItem):
            index (QtCore.QModelIndex): current index

        Returns:
            new editor
        """
        reload(knob_editors)
        model = index.model() # type: NodeTableModel
        row = index.row() # type: int
        column = index.column() # type: int

        knob = model.data(index, QtCore.Qt.UserRole)

        if isinstance(knob, nuke.Array_Knob):
            if isinstance(knob, nuke.AColor_Knob):
                return knob_editors.AColorEditor(parent)

            elif isinstance(knob, nuke.Boolean_Knob):
            #    return QtWidgets.QCheckBox()
                return super(KnobsItemDelegate, self).createEditor(parent, option, index)

            elif isinstance(knob, nuke.Enumeration_Knob):

                combobox = QtWidgets.QComboBox(parent)
                for v in knob.values():
                    combobox.addItem(v)
                return combobox

            if isinstance(knob.value(), list):
                return knob_editors.ArrayEditor(parent, len(knob.value()))
            else:
                return super(KnobsItemDelegate, self).createEditor(parent, option, index)
        else:
            return super(KnobsItemDelegate, self).createEditor(parent, option, index)
        # Array knobs:

    def setEditorData(self, editor, index):
        """sets editor to knobs value

        Args:
            editor (QtWidgets.QWidget):
            index (QtCore.QModelIndex): current index

        Returns: None
        """

        model = index.model() # type: NodeTableModel
        row = index.row() # type: int
        column = index.column() # type: int

        data = model.data(index, QtCore.Qt.EditRole)

        # Array knobs:
        if isinstance(data, list):
            editor.setEditorData(data)
        else:
            super(KnobsItemDelegate, self).setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        """sets new value to model

        Args:
            editor (QtWidgets.QWidget):
            model (QtCore.QAbstractTableModel):
            index (QtCore.QModelIndex): current index

        Returns:
            None

        """

        model = index.model() # type: NodeTableModel
        row = index.row() # type: int
        column = index.column() # type: int

        knob = model.data(index, QtCore.Qt.UserRole)
        data = None
        # Array knobs:
        if isinstance(knob, nuke.Array_Knob):
            if isinstance(knob, nuke.Boolean_Knob):
                super(KnobsItemDelegate, self).setModelData(editor, model, index)
            elif isinstance(knob, nuke.Enumeration_Knob):
                data = editor.currentText()
            elif isinstance(knob.value(), list):
                data = editor.getEditorData()

            if data:
                model.setData(index, data, QtCore.Qt.EditRole)
            else:
                super(KnobsItemDelegate, self).setModelData(editor, model, index)
        else:
            super(KnobsItemDelegate, self).setModelData(editor, model, index)

    def updateEditorGeometry(self, editor, option, index):
        """

        Args:
            editor (QtWidget.QWidget):
            option (QtWidget.QStyleOptionViewItem):
            index (QtCore.QModelIndex): current index

        Returns:
            None
        """
        model = index.model() # type: NodeTableModel
        row = index.row() # type: int
        column = index.column() # type: int

        knob = model.data(index, QtCore.Qt.UserRole)

        # Array knobs:
        if isinstance(knob, nuke.Array_Knob):
            if isinstance(knob, nuke.Boolean_Knob):
                super(KnobsItemDelegate, self).updateEditorGeometry(editor, option, index)
            elif isinstance(knob, nuke.Enumeration_Knob):
                super(KnobsItemDelegate, self).updateEditorGeometry(editor, option, index)
            else:
                rect = option.rect
                if isinstance(knob.value(), list):
                    if column == 0:
                        rect.adjust(0, 0, 100, 0 )
                    else:
                        rect.adjust(-50 , 0, 50 , 0)
                editor.setGeometry(rect)
                #editor.adjustSize()
        else:
            super(KnobsItemDelegate, self).updateEditorGeometry(editor, option, index)


    def paint(self, painter, option, index):

        model = index.model() # type: NodeTableModel
        row = index.row() # type: int
        column = index.column() # type: int

        knob = model.data(index, QtCore.Qt.UserRole)

        super(KnobsItemDelegate, self).paint(painter, option, index)

class NodeHeaderView(QtWidgets.QHeaderView):
    """This header view selects and zooms to node of clicked header section
    shows properties of node if double clicked
    """

    def __init__(self, orientation=QtCore.Qt.Vertical, parent=None):
        super(NodeHeaderView, self).__init__(orientation, parent)
        if "PySide2" in __binding__:
            self.setSectionsClickable(True)
        elif "PySide" in __binding__:
            self.setClickable(True)
        # noinspection PyUnresolvedReferences
        self.sectionClicked.connect(self.select_node)
        self.sectionDoubleClicked.connect(self.show_properties)

    def get_node(self, section):
        """returns node at section

        Args:
            section (int): current section

        Returns:
            node (nuke.Node)
        """
        model = self.model()  # type: QtCore.QAbstractItemModel
        node = model.headerData(section, QtCore.Qt.Vertical, QtCore.Qt.UserRole)
        return node

    def select_node(self, section):
        """selects node and zooms node graph

        Args:
            section (int):

        Returns:
            None
        """
        node = self.get_node(section)
        select_node(node, zoom=1)

    def show_properties(self, section):
        """opens properties bin for node at current section

        Args:
            section (int):

        Returns:
            None
        """
        node = self.get_node(section)
        nuke.show(node)


class NodeTableView(QtWidgets.QTableView):
    """Table with multi-cell editing
    """

    def __init__(self, parent=None):
        super(NodeTableView, self).__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        self.delegate = KnobsItemDelegate(self)
        self.setItemDelegate(self.delegate)

        self.resizeColumnsToContents()
        self.setHorizontalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setVerticalScrollMode(QtWidgets.QTableView.ScrollPerPixel)

        self.nodes_header = NodeHeaderView(QtCore.Qt.Vertical, parent)
        self.setVerticalHeader(self.nodes_header)

    def mouseReleaseEvent(self, event):
        """enter edit mode after single click

        Necessary for multi cell editing
        Args:
            event (QtCore.QEvent): mouse event

        Returns:
            None
        """
        if event.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(event.pos())
            self.edit(index)

        super(NodeTableView, self).mouseReleaseEvent(event)

    def commitData(self, editor):
        # call parent commitData first
        super(NodeTableView, self).commitData(editor)

        # self.currentIndex() is the QModelIndex of the cell just edited
        _model = self.currentIndex().model()
        # get the value that the user just submitted
        value = _model.data(self.currentIndex(), QtCore.Qt.EditRole)

        _row, _column = self.currentIndex().row(), self.currentIndex().column()

        # selection is a list of QItemSelectionRange instances
        for isr in self.selectionModel().selection():
            rows = range(isr.top(), isr.bottom() + 1)
            for row in rows:
                if row != _row:
                    # row,curCol is also in the selection. make an index:
                    idx = _model.index(row, _column)
                    # so we can apply the same value change
                    _model.setData(idx, value, QtCore.Qt.EditRole)


class ListModel(QtCore.QAbstractItemModel):

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


class MultiCompleter(QtWidgets.QCompleter):
    """QCompleter that supports completing multiple words in a QLineEdit,
        separated by delimiter.

    Args:
        model_list (QtCore.QStringListModel or list): complete these words
        delimiter (str): seperate words by this string (optional, default: ",")
    """
    def __init__(self, model_list=None, delimiter=","):
        super(MultiCompleter, self).__init__(model_list)
        self.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
        self.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.delimiter = delimiter

    def pathFromIndex(self, index):
        path = super(MultiCompleter, self).pathFromIndex(index)
        lst = str(self.widget().text()).split(self.delimiter)
        if len(lst) > 1:
            path = '%s%s %s' % (self.delimiter.join(lst[:-1]), self.delimiter, path)
        return path

    def splitPath(self, path):
        path = str(path.split(self.delimiter)[-1]).lstrip(' ')
        return [path]


class KeepOpenMenu(QtWidgets.QMenu):
    """Menu that stays open to allow multiple selections

    Warnings: broken atm, manu actually doesn't stay open
    """
    # TODO: keep menu open

    def __init__(self, parent=None):
        super(KeepOpenMenu, self).__init__(parent)

    def eventFilter(self, obj, event):
        if event.type() in [QtCore.QEvent.MouseButtonRelease]:
            if isinstance(obj, QtWidgets.QMenu):
                if obj.activeAction():
                    # if the selected action does not have a submenu
                    if not obj.activeAction().menu():

                        # eat the event, but trigger the function
                        obj.activeAction().trigger()
                        return True
        return super(KeepOpenMenu, self).eventFilter(obj, event)


class CheckAction(QtWidgets.QAction):
    """Creates a checkable QAction

    Args:
        text (str): text to display on QAction
        parent (QtWidgets.QWidget): parent widget (optional)
    """
    def __init__(self, text, parent=None):
        super(CheckAction, self).__init__(text, parent)
        self.setCheckable(True)


class NodeTableWidget(QtWidgets.QWidget):
    """Creates the GUI for the table view and filtering

    Filtering is achieved by stacking multiple custom QSortFilterProxyModels

    Args:
        node_list (list): list of nuke.Node nodes
        parent (QtGui.QWidget): parent widget
    """

    def __init__(self, node_list=None, parent=None):
        super(NodeTableWidget, self).__init__(parent)

        # Widget
        self.setWindowTitle('Node spreadsheet')

        # Variables:
        self.filter_delimiter = ','
        # Initial list of classes, will overwrite this with given nodes classes
        self._node_classes = sorted(get_node_classes(no_ext=True),
                                    key=lambda s: s.lower())

        self._node_list = node_list or []  # make sure it's iterable
        self._node_names = []
        self._knob_names = []
        self._hidden_knobs = False
        self._all_knob_states = False
        self._disabled_knobs = False
        self._knob_name_filter = None
        self._node_name_filter = None
        self._node_class_filter = None
        self._node_class_filter = None

        # Content
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.menu_bar = QtWidgets.QMenuBar(self)

        self.load_selected_action = QtWidgets.QAction('Load selected Nodes', self.menu_bar)
        self.menu_bar.addAction(self.load_selected_action)
        self.load_selected_action.triggered.connect(self.load_selected)

        self.show_menu = KeepOpenMenu('Show')  # type: QtWidgets.QMenu
        self.menu_bar.addMenu(self.show_menu)
        self.knobs_menu = KeepOpenMenu('Knobs')  # type: QtWidgets.QMenu
        self.show_menu.addMenu(self.knobs_menu)

        self.all_knobs_action = CheckAction('all', self.knobs_menu)
        self.knobs_menu.addAction(self.all_knobs_action)
        self.all_knobs_action.triggered[bool].connect(self.all_knob_states_changed)

        self.knobs_menu.addSeparator()

        self.hidden_knobs_action = CheckAction('hidden', self.knobs_menu)
        self.knobs_menu.addAction(self.hidden_knobs_action)
        self.hidden_knobs_action.triggered[bool].connect(self.hidden_knobs_changed)

        self.disabled_knobs_action = CheckAction('enabled')
        self.knobs_menu.addAction(self.disabled_knobs_action)
        self.disabled_knobs_action.triggered[bool].connect(self.disabled_knobs_changed)

        self.nodes_classes_menu = self.show_menu.addMenu('Nodes')

        # Filter Widget
        self.filter_widget = QtWidgets.QWidget(self)
        self.filter_layout = QtWidgets.QHBoxLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_widget.setLayout(self.filter_layout)

        # Filter by node class:
        self.node_class_filter_label = QtWidgets.QLabel('class:')
        self.filter_layout.addWidget(self.node_class_filter_label)
        self.node_class_filter_line_edit = QtWidgets.QLineEdit(self.filter_widget)
        self.node_class_completer = MultiCompleter(self.node_classes)
        self.node_class_model = self.node_class_completer.model()
        self.node_class_filter_line_edit.setCompleter(self.node_class_completer)
        self.node_class_filter_line_edit.textChanged.connect(self.node_class_filter_changed)
        self.filter_layout.addWidget(self.node_class_filter_line_edit)

        # Filter by node name:
        self.node_name_filter_label = QtWidgets.QLabel(' name:')
        self.filter_layout.addWidget(self.node_name_filter_label)
        self.node_name_filter_line_edit = QtWidgets.QLineEdit()
        self.node_name_filter_label.setAcceptDrops(True)
        self.node_name_completer = MultiCompleter(self.node_names)
        self.node_name_model = self.node_name_completer.model()
        self.node_name_filter_line_edit.setCompleter(self.node_name_completer)
        self.node_name_filter_line_edit.textChanged.connect(self.node_name_filter_changed)
        self.filter_layout.addWidget(self.node_name_filter_line_edit)

        self.filter_separator_knobs = QtWidgets.QFrame(self.filter_widget)
        self.filter_separator_knobs.setFrameShape(QtWidgets.QFrame.VLine)
        self.filter_layout.addWidget(self.filter_separator_knobs)

        # Filter by knob name:
        self.knob_filter_label = QtWidgets.QLabel('knob:')
        self.filter_layout.addWidget(self.knob_filter_label)

        self.knob_name_filter_line_edit = QtWidgets.QLineEdit()
        self.knob_name_filter_line_edit.setAcceptDrops(True)
        self.knob_name_filter_completer = MultiCompleter(self.knob_names)
        self.knob_name_filter_model = self.knob_name_filter_completer.model()
        self.knob_name_filter_line_edit.setCompleter(self.knob_name_filter_completer)
        self.knob_name_filter_line_edit.textChanged.connect(self.knob_name_filter_changed)
        self.filter_layout.addWidget(self.knob_name_filter_line_edit)

        self.layout.addWidget(self.menu_bar)
        # self.menu_bar.setCornerWidget(self.filter_widget, QtCore.Qt.TopRightCorner)
        self.layout.addWidget(self.filter_widget)

        self.table_view = NodeTableView(self)

        self.table_model = NodeTableModel()
        self.layout.addWidget(self.table_view)

        # Filter disabled or enabled knobs:
        self.knob_states_filter_model = KnobStatesFilterModel(self)
        self.knob_states_filter_model.setSourceModel(self.table_model)
        self.knob_states_filter_model.set_disabled_knobs(True)
        self.knob_states_filter_model.set_hidden_knobs(False)

        # Filter by Node name
        self.node_name_filter_model = NodeNameFilterModel(self, self.filter_delimiter)
        self.node_name_filter_model.setSourceModel(self.knob_states_filter_model)

        # Filter by Node Class:
        self.node_class_filter_model = NodeClassFilterModel(self)
        self.node_class_filter_model.setSourceModel(self.node_name_filter_model)

        # Filter by knob name:
        self.knob_name_filter_model = HeaderHorizontalFilterModel(self)
        self.knob_name_filter_model.setSourceModel(self.node_class_filter_model)

        # Filter empty columns
        self.empty_column_filter_model = EmptyColumnFilterModel(self)
        self.empty_column_filter_model.setSourceModel(self.knob_name_filter_model)

        # Set model to view
        self.table_view.setModel(self.empty_column_filter_model)

        # Load given node list
        self.node_list = self._node_list

    def load_selected(self):
        """sets the displayed nodes to current selection

        Returns:
            None
        """
        # TODO: add warning when user loads too many nodes.
        self.node_list = nuke.selectedNodes()

    @property
    def node_names(self):
        """returns the list of current nodes names

        Warnings:
            Do not use _node_names
        """
        # TODO: implement as generator
        return [node.name() for node in self._node_list]

    @property
    def node_classes(self):
        """generates and returns list of node classes

        If node_list is set, classes are updated to include only
        classes of current nodes.
        """
        # TODO: implement as generator
        if self.node_list:
            self._node_classes = [node.Class() for node in self.node_list]
        return self._node_classes

    @property
    def knob_names(self):
        knobs_names = []
        for node in self._node_list:
            for knob in node.knobs():
                if knob not in knobs_names:
                    knobs_names.append(knob)
        self._knob_names = knobs_names
        return self._knob_names

    @property
    def node_list(self):
        """returns list of loaded nodes before all filtering

        Returns:
            list: current nodes
        """
        return self._node_list

    @node_list.setter
    def node_list(self, nodes):
        """Sets nodes and updates models
        """
        self._node_list = nodes or []
        self.table_model.set_node_list(self._node_list)
        self.node_name_completer.setModel(QtGui.QStringListModel(self.node_names))
        self.node_class_completer.setModel(QtGui.QStringListModel(self.node_classes))
        self.knob_name_filter_completer.setModel(QtGui.QStringListModel(self.knob_names))
        self.table_view.resizeColumnsToContents()

    @QtCore.Slot(bool)
    def hidden_knobs_changed(self, checked=None):
        # PySide doesn't pass checked state
        if checked is None:
            checked = self.hidden_knobs_action.isChecked()
        self.hidden_knobs = checked

    @property
    def hidden_knobs(self):
        return self._hidden_knobs

    @hidden_knobs.setter
    def hidden_knobs(self, checked):

        self._hidden_knobs = checked
        self.knob_states_filter_model.set_hidden_knobs(checked)
        self.table_view.resizeColumnsToContents()
        self.hidden_knobs_action.setChecked(checked)

    @QtCore.Slot(bool)
    def disabled_knobs_changed(self, checked=None):
        # PySide doesn't pass checked state
        if checked is None:
            checked = self.disabled_knobs_action.isChecked()
        self.disabled_knobs = checked

    @property
    def disabled_knobs(self):
        return self._disabled_knobs

    @disabled_knobs.setter
    def disabled_knobs(self, checked=None):
        self._disabled_knobs = checked
        self.knob_states_filter_model.set_disabled_knobs(checked)
        self.table_view.resizeColumnsToContents()
        self.disabled_knobs_action.setChecked(checked)

    @QtCore.Slot(bool)
    def all_knob_states_changed(self, checked=True):
        # PySide doesn't pass checked state
        if checked is None:
            checked = self.all_knobs_action.isChecked()
        self.all_knob_states = checked

    @property
    def all_knob_states(self):
        self._all_knob_states = self.hidden_knobs and self._disabled_knobs
        return self._all_knob_states

    @all_knob_states.setter
    def all_knob_states(self, checked=None):
        self._all_knob_states = checked
        self.hidden_knobs = checked
        self.disabled_knobs = checked

    @QtCore.Slot(str)
    def knob_name_filter_changed(self, value=None):
        if not value:
            value = self.knob_name_filter_line_edit.text()
        self.knob_name_filter = value

    @property
    def knob_name_filter(self):
        return self._knob_name_filter

    @knob_name_filter.setter
    def knob_name_filter(self, filter_str=None):
        if filter_str is None:
            filter_str = self.knob_name_filter_line_edit.text()

        self._knob_name_filter = filter_str
        self.knob_name_filter_model.set_filter(filter_str)

    @property
    def node_name_filter(self):
        return self._node_name_filter

    @node_name_filter.setter
    def node_name_filter(self, node_names=None):
        self._node_name_filter = node_names
        self.node_name_filter_model.set_filter(node_names)
        self.empty_column_filter_model.invalidateFilter()

    @QtCore.Slot(str)
    def node_name_filter_changed(self, node_names):
        if not node_names:
            node_names = self.node_name_filter_line_edit.text()
        self.node_name_filter = node_names

    @property
    def node_class_filter(self):
        return self._node_class_filter

    @node_class_filter.setter
    def node_class_filter(self, node_classes=None):
        # TODO: extract to function and create unit test
        self._node_class_filter = node_classes
        self.node_class_filter_model.set_filter(node_classes)
        self.empty_column_filter_model.invalidateFilter()

    @QtCore.Slot(str)
    def node_class_filter_changed(self, node_classes = None):
        if not node_classes:
            node_classes = self.node_class_filter_line_edit.text()
        self.node_class_filter = node_classes


if __name__ == '__main__':
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)

    widget = NodeTableWidget()
    widget.show()
    app.exec_()
