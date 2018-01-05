# built-ins
import os
import logging

# external
nuke_loaded = True
try:
    import nuke
except ImportError:
    nuke_loaded = False


LOG = logging.getLogger(__name__)


def node_exists(node):
    """Check if python object node is still attached to a Node.

    Nuke throws a ValueError if node is not attached. This happens when the
    user deleted a node that is still in use by a python script.

    Args:
        node (nuke.Node): node python object

    Returns:
        bool: True if node exists
    """
    try:
        return node.name() is not None
    except ValueError as err:
        return False


def get_selected_nodes():
    """get current selection

    Returns:
        list: of nuke.Node
    """
    return nuke.selectedNodes()


def to_hex(rgb):
    """convert rgb color values to hex

    Args:
        rgb (tuple): color values 0-1

    Returns:
        str: color in hex notation
    """
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
    a = (0xFF & hex >> 1) / 255.0

    return r, g, b, a


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


def get_node_tile_color(node):
    """return the nodes tile color or default node color if not set

    Args:
        node (nuke.Node): node

    Returns:
        list: colors in rgb
    """
    color = None
    tile_color_knob = node.knob('tile_color')
    if tile_color_knob:
        color = tile_color_knob.value()
    if not color:
        color = nuke.defaultNodeColor(node.Class())

    if color:
        return to_rgb(color)[:3]


def get_node_font_color(node):
    color = None
    color_knob = node.knob('note_font_color')
    if color_knob:
        return to_rgb(color_knob.value())[:3]


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


def shade_dag_nodes_enabled():
    """check weather shadows in dag are enabled in settings

    Returns (boolean):
    """
    pref_node = nuke.toNode("preferences")
    return pref_node['ShadeDAGNodes'].value()

