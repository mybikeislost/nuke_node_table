from nukescripts import panels


def get_node_table_widget():
    from node_table import view as node_table_view
    return node_table_view.NodeTableWidget()


panels.registerWidgetAsPanel(
    'get_node_table_widget',
    'Node Spreadsheet',
    'de.filmkorn.NodeSpreadsheet',
    False
    )