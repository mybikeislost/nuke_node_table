"""Build the widget and stack the models."""

# Import third party modules
# pylint: disable=import-error
import nuke

# Keeping this for development to enable auto-completion.
from Qt import QtCore, QtGui, QtWidgets, __binding__  # pylint: disable=no-name-in-module

# Import internal modules
from node_table import constants
from node_table import delegate
from node_table import nuke_utils
from node_table import model


# pylint: disable=invalid-name
class NodeHeaderView(QtWidgets.QHeaderView):
    """This header view selects and zooms to node of clicked header section.

    Shows properties of node if double clicked.

    """

    def __init__(self, orientation=QtCore.Qt.Vertical, parent=None):
        """Construct the header view.

        Args:
            orientation (QtCore.Qt.Orientation): Orientation of the header.
            parent (QtWidgets.QWidget, optional): Parent widget.

        """
        super(NodeHeaderView, self).__init__(orientation, parent)
        if "PySide2" in __binding__:
            self.setSectionsClickable(True)
        elif "PySide" in __binding__:
            self.setClickable(True)

        self.shade_dag_nodes_enabled = nuke_utils.shade_dag_nodes_enabled()

        self.sectionClicked.connect(self.select_node)
        self.sectionDoubleClicked.connect(self.show_properties)

    def paintSection(self, painter, rect, index):
        """Mimic Nuke's way of drawing nodes in DAG.

        Args:
            painter (QtGui.QPainter): Painter to perform the painting.
            rect (QtCore.QRect): Section to paint in.
            index (QtCore.QModelIndex): Current logical index.

        """
        painter.save()
        QtWidgets.QHeaderView.paintSection(self, painter, rect, index)
        painter.restore()

        bg_brush = self.model().headerData(index,
                                           QtCore.Qt.Vertical,
                                           QtCore.Qt.BackgroundRole)  # type: QtGui.QBrush

        fg_pen = self.model().headerData(index,
                                         QtCore.Qt.Vertical,
                                         QtCore.Qt.ForegroundRole)  # type: QtGui.QPen

        if self.shade_dag_nodes_enabled:
            gradient = QtGui.QLinearGradient(rect.topLeft(),
                                             rect.bottomLeft())
            gradient.setColorAt(0, bg_brush.color())
            gradient_end_color = model.scalar(bg_brush.color().getRgbF()[:3],
                                              0.6)
            gradient.setColorAt(1, QtGui.QColor.fromRgbF(*gradient_end_color))
            painter.fillRect(rect, gradient)
        else:
            painter.fillRect(rect, bg_brush)

        rect_adj = rect
        rect_adj.adjust(-1, -1, -1, -1)
        painter.setPen(fg_pen)
        text = self.model().headerData(index,
                                       QtCore.Qt.Vertical,
                                       QtCore.Qt.DisplayRole)
        painter.drawText(rect, QtCore.Qt.AlignCenter, text)
        painter.setPen(QtGui.QPen(QtGui.QColor.fromRgbF(0.0, 0.0, 0.0)))
        painter.drawRect(rect_adj)

    def get_node(self, section):
        """Return node at current section (index).

        Args:
            section (int): Index of current section in the models header data.

        Returns:
            node (nuke.Node): Node at the current section.

        """
        return self.model().headerData(section,
                                       QtCore.Qt.Vertical,
                                       QtCore.Qt.UserRole)

    def select_node(self, section):
        """Select node and zoom node graph.

        Args:
            section (int): Index of the node to zoom to.

        """
        node = self.get_node(section)
        nuke_utils.select_node(node, zoom=1)

    def show_properties(self, section):
        """Open properties bin for node at current section.

        Args:
            section (int): Index of the node to show in properties bin.

        """
        node = self.get_node(section)
        nuke.show(node)


class NodeTableView(QtWidgets.QTableView):
    """Table with multi-cell editing."""

    def __init__(self, parent=None):
        super(NodeTableView, self).__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        self.delegate = delegate.KnobsItemDelegate(self)
        self.setItemDelegate(self.delegate)

        self.setHorizontalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setVerticalScrollMode(QtWidgets.QTableView.ScrollPerPixel)

        self.nodes_header = NodeHeaderView(QtCore.Qt.Vertical, parent)
        self.setVerticalHeader(self.nodes_header)

    def selectionCommand(self, index, event):
        """Returns the SelectionFlags to be used when updating a selection.

        Allow to keep editing the same selection when clicking into a checkbox.
        The selection change can't be prevented in the delegate, so we have to
        return the `NoUpdate` flag here to keep the selection.

        Args:
            index (QtCore.QModelIndex): Current index.
            event (QtCore.QEvent): Current event.

        Returns:
             QtCore.QItemSelectionModel.Flag: The selection update flag.

        """
        try:
            pos = event.pos()
        except AttributeError:
            # Event is does not have a position ie. KeyPressEvent.
            return super(NodeTableView, self).selectionCommand(index, event)

        index = self.indexAt(pos)
        if not index.isValid():
            return super(NodeTableView, self).selectionCommand(index, event)

        # Prevent loosing selection when clicking a checkbox.
        if event.type() in (QtCore.QEvent.MouseButtonRelease, QtCore.QEvent.MouseMove,
                            QtCore.QEvent.MouseButtonPress):
            data = index.model().data(index, QtCore.Qt.EditRole)
            if isinstance(data, bool):
                checkbox_rect = self.delegate.get_check_box_rect(rect=self.visualRect(index))
                if checkbox_rect.contains(event.pos()):
                    return QtCore.QItemSelectionModel.NoUpdate

        return super(NodeTableView, self).selectionCommand(index, event)

    def mouseReleaseEvent(self, event):
        """Enter edit mode after single click.

        Enter the edit mode on mouse release after dragging a selection or
        selecting a single cell.

        Args:
            event (QtCore.QEvent): The current mouse event.

        """
        if event.button() == QtCore.Qt.LeftButton:
            if event.type() == QtCore.QEvent.MouseButtonRelease:
                index = self.indexAt(event.pos())
                if index.isValid():
                    self.edit(index)
                else:
                    # Close an active editor if it is open.
                    index = self.currentIndex()
                    editor = self.indexWidget(index)
                    if editor:
                        self.commitData(editor)
                        self.closeEditor(editor, QtWidgets.QAbstractItemDelegate.NoHint)

        if event.button() == QtCore.Qt.RightButton:
            # TODO: implement right click options
            pass

        return super(NodeTableView, self).mouseReleaseEvent(event)

    def commitData(self, editor):
        """Set the current editor data to the model for the whole selection.

        Args:
            editor (QtWidgets.QWidget): The current editor.

        """
        # Call parent commitData first.
        super(NodeTableView, self).commitData(editor)

        # self.currentIndex() is the QModelIndex of the cell just edited
        current_index = self.currentIndex()  # type: QtCore.QModelIndex

        # Return early if nothing is selected. This can happen when editing
        # a checkbox that doesn't rely on selection.
        if not current_index.isValid():
            return

        _model = self.currentIndex().model()
        # Get the value that the user just submitted.
        value = _model.data(self.currentIndex(), QtCore.Qt.EditRole)
        edited_knob = _model.data(self.currentIndex(), QtCore.Qt.UserRole)

        current_row = self.currentIndex().row()
        current_column = self.currentIndex().column()

        # Selection is a list of QItemSelectionRange instances.
        for isr in self.selectionModel().selection():
            rows = range(isr.top(), isr.bottom() + 1)
            columns = range(isr.left(), isr.right() +1)
            for row in rows:
                for col in columns:
                    if row != current_row or col != current_column:
                        # Other rows and columns are also in the selection.
                        # Create an index so we can apply the same value
                        # change.
                        idx = _model.index(row, col)
                        knob = _model.data(idx, QtCore.Qt.UserRole)
                        if type(knob) == type(edited_knob):
                            _model.setData(idx, value, QtCore.Qt.EditRole)


class MultiCompleter(QtWidgets.QCompleter):
    """Complete multiple words in a QLineEdit, separated by a delimiter.

    Args:
        model_list (QtCore.QStringListModel or list): Words to complete.
        delimiter (str, optional): Separate words by this string.
            (default: ",").

    """
    def __init__(self, model_list=None, delimiter=","):
        super(MultiCompleter, self).__init__(model_list)
        self.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
        self.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.delimiter = delimiter

    def pathFromIndex(self, index):
        """Complete the input.

        Args:
            index (QtCore.QModelIndex): Current index.

        Returns:
            str: Completed input.

        """
        path = super(MultiCompleter, self).pathFromIndex(index)
        lst = str(self.widget().text()).split(self.delimiter)
        if len(lst) > 1:
            path = '%s%s %s' % (self.delimiter.join(lst[:-1]),
                                self.delimiter, path)
        return path

    def splitPath(self, path):
        """Split and strip the input.

        Splits the given path into strings that are used to match at each level
        in the model().

        Args:
            path (str): String to split.

        Returns:
            :obj:`list` of :obj:`string`: Stirng split by the delimiter.

        """
        path = str(path.split(self.delimiter)[-1]).lstrip(' ')
        return [path]


# pylint: disable=too-few-public-methods
class KeepOpenMenu(QtWidgets.QMenu):
    """Menu that stays open to allow toggling multiple actions.

    Warnings: broken, manu actually doesn't stay open.
    TODO: keep menu open.

    """

    def eventFilter(self, obj, event):
        """Eat the mouse event but trigger the objects action.

        Filters events if this object has been installed as an event filter
        for the watched object.

        Args:
            obj (QtCore.QObject): Watched object.
            event (QtCore.QEvent): Current event.

        Returns:
            bool: True if the event is filtered out, otherwise False (to
                process it further).

        """
        if event.type() in [QtCore.QEvent.MouseButtonRelease]:
            if isinstance(obj, QtWidgets.QMenu):
                if obj.activeAction():
                    # if the selected action does not have a submenu
                    if not obj.activeAction().menu():

                        # eat the event, but trigger the function
                        obj.activeAction().trigger()
                        return True
        return super(KeepOpenMenu, self).eventFilter(obj, event)


# pylint: disable=too-few-public-methods
class CheckAction(QtWidgets.QAction):
    """A checkable QAction."""

    def __init__(self, text, parent=None):
        """Create a checkable QAction.

        Args:
            text (str): text to display on QAction
            parent (QtWidgets.QWidget): parent widget (optional).

        """
        super(CheckAction, self).__init__(text, parent)
        self.setCheckable(True)


# pylint: disable=line-too-long, too-many-instance-attributes
class NodeTableWidget(QtWidgets.QWidget):
    """The main GUI for the table view and filtering.

    Filtering is achieved by stacking multiple custom QSortFilterProxyModels.
    The node list and filters are accessible through pythonic properties.

    Examples:
        >>> from node_table import view
        >>> table = view.NodeTableWidget()
        >>> table.node_list = nuke.selectedNodes()
        >>> table.node_class_filter = 'Merge2, Blur'
        >>> table.knob_name_filter = 'disabled, cached'

    """

    def __init__(self, node_list=None, parent=None):
        """    Args:
        node_list (list): list of nuke.Node nodes (optional).
        parent (QtGui.QWidget): parent widget (optional)

        Args:
            node_list (:obj:`list` of :obj:`str`, optional): Nodes to display.
            parent (QtWidgets.QWidget, optional): Parent widget.

        """
        super(NodeTableWidget, self).__init__(parent)

        # Widget
        self.setWindowTitle(constants.PACKAGE_NICE_NAME)

        # Variables:
        self._node_classes = []
        self._node_list = []  # make sure it's iterable
        self._node_names = []
        self._knob_names = []
        self._hidden_knobs = False
        self._all_knob_states = False
        self._disabled_knobs = False
        self._grouped_nodes = False
        self._knob_name_filter = None
        self._node_name_filter = None
        self._node_class_filter = None
        self._node_class_filter = None

        # Content
        # TODO: untangle this bad mix of ui and controller functions.
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.menu_bar = QtWidgets.QMenuBar(self)
        # show menubar in parents window for osx and some linux dists
        self.menu_bar.setNativeMenuBar(False)

        self.load_selected_action = QtWidgets.QAction('Load selected Nodes',
                                                      self.menu_bar)
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

        self.disabled_knobs_action = CheckAction('disabled')
        self.knobs_menu.addAction(self.disabled_knobs_action)
        self.disabled_knobs_action.triggered[bool].connect(self.disabled_knobs_changed)

        self.nodes_menu = self.show_menu.addMenu('Nodes')
        self.grouped_nodes_action = CheckAction('grouped')
        self.nodes_menu.addAction(self.grouped_nodes_action)
        self.grouped_nodes_action.triggered[bool].connect(self.grouped_nodes_changed)

        # Filter Widget
        self.filter_widget = QtWidgets.QWidget(self)
        self.filter_layout = QtWidgets.QHBoxLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_widget.setLayout(self.filter_layout)

        # Filter by node class:
        self.node_class_filter_label = QtWidgets.QLabel('node: class:')
        self.filter_layout.addWidget(self.node_class_filter_label)
        self.node_class_filter_line_edit = QtWidgets.QLineEdit(self.filter_widget)
        self.node_class_completer = MultiCompleter(self.node_classes)
        self.node_class_model = self.node_class_completer.model()
        self.node_class_filter_line_edit.setCompleter(self.node_class_completer)
        self.node_class_filter_line_edit.textChanged.connect(self.node_class_filter_changed)
        self.filter_layout.addWidget(self.node_class_filter_line_edit)

        # Filter by node name:
        self.node_name_filter_label = QtWidgets.QLabel('name:')
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
        self.knob_filter_label = QtWidgets.QLabel('knob: name')
        self.filter_layout.addWidget(self.knob_filter_label)

        self.knob_name_filter_line_edit = QtWidgets.QLineEdit()
        self.knob_name_filter_line_edit.setAcceptDrops(True)
        self.knob_name_filter_completer = MultiCompleter(self.knob_names)
        self.knob_name_filter_model = self.knob_name_filter_completer.model()
        self.knob_name_filter_line_edit.setCompleter(self.knob_name_filter_completer)
        self.knob_name_filter_line_edit.textChanged.connect(self.knob_name_filter_changed)
        self.filter_layout.addWidget(self.knob_name_filter_line_edit)

        self.layout.addWidget(self.menu_bar)
        self.layout.addWidget(self.filter_widget)

        self.table_view = NodeTableView(self)

        self.table_model = model.NodeTableModel()
        self.layout.addWidget(self.table_view)

        # Filter disabled or enabled knobs:
        self.knob_states_filter_model = model.KnobStatesFilterModel(self)
        self.knob_states_filter_model.setSourceModel(self.table_model)
        self.disabled_knobs = True
        self.hidden_knobs = False

        # Filter by Node name
        self.node_name_filter_model = model.NodeNameFilterModel(self)
        self.node_name_filter_model.setSourceModel(self.knob_states_filter_model)
        # self.node_name_filter_model.setSourceModel(self.table_model)

        # Filter by Node Class:
        self.node_class_filter_model = model.NodeClassFilterModel(self)
        self.node_class_filter_model.setSourceModel(self.node_name_filter_model)

        # Filter by knob name:
        self.knob_name_filter_model = model.HeaderHorizontalFilterModel(self)
        self.knob_name_filter_model.setSourceModel(self.node_class_filter_model)

        # Filter empty columns
        self.empty_column_filter_model = model.EmptyColumnFilterModel(self)
        self.empty_column_filter_model.setSourceModel(self.knob_name_filter_model)

        # Set model to view
        self.table_view.setModel(self.empty_column_filter_model)

        # Load given node list
        self.node_list = node_list or []

    def load_selected(self):
        """Sets the node list to current selection."""
        self.node_list = nuke_utils.get_selected_nodes(self.grouped_nodes)

    @property
    def node_names(self):
        """:obj:`list` of :obj:`str`: Sorted list of current node's names."""
        node_names = [node.name() for node in self.node_list]
        return sorted(node_names, key=lambda n: n.lower())

    @property
    def node_classes(self):
        """:obj:`list` of :obj:`str`: Sorted list of node's classes.

        If `node_list` is set, classes are updated to include only
        classes of current nodes else all possible node classes are returned.

        """
        if self.node_list:
            node_classes = set()
            for node in self.node_list:
                node_classes.add(node.Class())
        else:
            node_classes = nuke_utils.get_node_classes(no_ext=True)
        return sorted(list(node_classes), key=lambda s: s.lower())

    @property
    def knob_names(self):
        """:obj:`list` of :obj:`str`:: All knob names of current nodes."""
        knob_names = set()
        for node in self.node_list:
            for knob in node.knobs():
                knob_names.add(knob)
        self._knob_names = sorted(list(knob_names), key=lambda s: s.lower())
        return self._knob_names

    @property
    def node_list(self):
        """:obj:`list` of :obj:`nuke.Node`: List of loaded nodes before all
            filtering.

        Setting this attribute updates all models and warns when loading too
        many nodes.

        """
        self._node_list = [node for node in self._node_list
                           if nuke_utils.node_exists(node)]
        return self._node_list

    @node_list.setter
    def node_list(self, nodes):
        num_nodes = len(nodes)

        # Ask for confirmation before loading too many nodes.
        if num_nodes > constants.NUM_NODES_WARN_BEFORE_LOAD:
            proceed = nuke_utils.ask('Loading {num_nodes} Nodes may take a '
                                     'long time. \n'
                                     'Dou you wish to proceed?'.format(
                                         num_nodes=num_nodes))

            if not proceed:
                return

        self._node_list = nodes or []
        self.table_model.node_list = self.node_list

        self.node_name_completer.setModel(
            QtCore.QStringListModel(self.node_names))
        self.node_class_completer.setModel(
            QtCore.QStringListModel(self.node_classes))
        self.knob_name_filter_completer.setModel(
            QtCore.QStringListModel(self.knob_names))

        self.table_view.resizeColumnsToContents()

    @QtCore.Slot(bool)
    def grouped_nodes_changed(self, checked=None):
        """Update the hidden knobs state filter.

        Args:
            checked (bool): If True, knobs with hidden state are displayed.

        """
        # PySide doesn't pass checked state
        if checked is None:
            checked = self.grouped_nodes_action.isChecked()
        self.grouped_nodes = checked
        self.table_view.resizeColumnsToContents()

    @property
    def grouped_nodes(self):
        """bool: Show selected nodes inside of selected group nodes."""
        return self._grouped_nodes

    @grouped_nodes.setter
    def grouped_nodes(self, checked):
        self._grouped_nodes = checked
        self.load_selected()
        self.grouped_nodes_action.setChecked(checked)

    @QtCore.Slot(bool)
    def hidden_knobs_changed(self, checked=None):
        """Update the hidden knobs state filter.

        Args:
            checked (bool): If True, knobs with hidden state are displayed.

        """
        # PySide doesn't pass checked state
        if checked is None:
            checked = self.hidden_knobs_action.isChecked()
        self.hidden_knobs = checked
        self.table_view.resizeColumnsToContents()

    @property
    def hidden_knobs(self):
        """bool: Show hidden knobs of the node."""
        return self._hidden_knobs

    @hidden_knobs.setter
    def hidden_knobs(self, checked):
        self._hidden_knobs = checked
        self.knob_states_filter_model.hidden_knobs = checked
        self.table_view.resizeColumnsToContents()
        self.hidden_knobs_action.setChecked(checked)

    @QtCore.Slot(bool)
    def disabled_knobs_changed(self, checked=None):
        """Update the disabled knobs state filter.

        Args:
            checked (bool): If True, knobs with disabled state are displayed.

        """
        # PySide doesn't pass checked state
        if checked is None:
            checked = self.disabled_knobs_action.isChecked()
        self.disabled_knobs = checked
        self.table_view.resizeColumnsToContents()

    @property
    def disabled_knobs(self):
        """bool: Show disabled knobs."""
        return self._disabled_knobs

    @disabled_knobs.setter
    def disabled_knobs(self, checked=None):
        self._disabled_knobs = checked
        self.knob_states_filter_model.disabled_knobs = checked
        self.table_view.resizeColumnsToContents()
        self.disabled_knobs_action.setChecked(checked)
        self.update_all_knob_states_action()

    @QtCore.Slot(bool)
    def all_knob_states_changed(self, checked=True):
        """Update the knob states filter.

        Args:
            checked: If True, show knobs with hidden or disabled state.

        """
        # PySide doesn't pass checked state
        if checked is None:
            checked = self.all_knobs_action.isChecked()
        self.all_knob_states = checked
        self.table_view.resizeColumnsToContents()

    @property
    def all_knob_states(self):
        """bool: Knobs with hidden or disabled knob states are displayed."""
        self._all_knob_states = self.hidden_knobs and self._disabled_knobs
        return self._all_knob_states

    @all_knob_states.setter
    def all_knob_states(self, checked=None):
        self._all_knob_states = checked
        self.hidden_knobs = checked
        self.disabled_knobs = checked

    def update_all_knob_states_action(self):
        """Update action (checkbox) 'All' knob states."""
        self.all_knobs_action.setChecked(all([self.hidden_knobs,
                                              self.disabled_knobs]))

    @QtCore.Slot(str)
    def knob_name_filter_changed(self, value=None):
        """Update the knob name filter.

        Args:
            value (str): list of knob names to display.

        """
        if not value:
            value = self.knob_name_filter_line_edit.text()
        self.knob_name_filter = value
        self.table_view.resizeColumnsToContents()

    @property
    def knob_name_filter(self):
        """str: List of knob names separated by delimiters."""
        return self._knob_name_filter

    @knob_name_filter.setter
    def knob_name_filter(self, filter_str=None):
        if filter_str is None:
            filter_str = self.knob_name_filter_line_edit.text()
        else:
            self.knob_name_filter_line_edit.setText(filter_str)
        self._knob_name_filter = filter_str
        self.knob_name_filter_model.set_filter_str(filter_str)

    @property
    def node_name_filter(self):
        """str: List of node names separated by delimiters."""
        return self._node_name_filter

    @node_name_filter.setter
    def node_name_filter(self, node_names=None):
        self._node_name_filter = node_names
        self.node_name_filter_model.set_filter_str(node_names)
        self.empty_column_filter_model.invalidateFilter()

    @QtCore.Slot(str)
    def node_name_filter_changed(self, node_names):
        """Update the node names filter.

        Args:
            node_names (str): List of node names separated by delimiter.

        """
        if not node_names:
            node_names = self.node_name_filter_line_edit.text()
        self.node_name_filter = node_names
        self.table_view.resizeColumnsToContents()

    @property
    def node_class_filter(self):
        """str: List of node classes to display separated by delimiter."""
        return self._node_class_filter

    @node_class_filter.setter
    def node_class_filter(self, node_classes=None):
        self._node_class_filter = node_classes
        self.node_class_filter_model.set_filter_str(node_classes)
        self.empty_column_filter_model.invalidateFilter()

    @QtCore.Slot(str)
    def node_class_filter_changed(self, node_classes=None):
        """Update the node class filter.

        Args:
            node_classes (str): delimited str list of node Classes to display.

        """
        if not node_classes:
            node_classes = self.node_class_filter_line_edit.text()
        self.node_class_filter = node_classes
        self.table_view.resizeColumnsToContents()
