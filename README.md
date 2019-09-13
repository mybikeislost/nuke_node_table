# README #

Spreadsheet showing and editing knobs of selected Nodes

![demo](demo.gif)

### How do I get set up? ###

download Qt.py and add into your .nuke folder or PYTHON_PATH:
https://github.com/mottosso/Qt.py

Add to your menu.py:

```python
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
```

# License: MIT
