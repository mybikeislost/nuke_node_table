import nuke

FILTER_DELIMITER = ','

# Knob classes that can't be edited directly
READ_ONLY_KNOBS = [nuke.Transform2d_Knob]

# Colors
# knob is animated
KNOB_ANIMTED_COLOR = (0.312839, 0.430188, 0.544651)
# knob has key at current frame
KNOB_HAS_KEY_AT_COLOR = (0.165186, 0.385106, 0.723738)

# Mix background color with node color by this amount
# if cell has no knob:
CELL_MIX_NODE_COLOR_AMOUNT_NO_KNOB = .08
# if cell has knob:
CELL_MIX_NODE_COLOR_AMOUNT_HAS_KNOB = 0.3

# Editors:
# Cell size:
EDITOR_CELL_WIDTH = 80
EDITOR_CELL_HEIGHT = 28

# editor precision
EDITOR_DECIMALS = 8
