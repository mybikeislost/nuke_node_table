"""
module to not break existing installations

deprecated: use view module instead
"""

import logging

LOG = logging.getLogger(__name__)

# legacy
from NodeTable import view
NodeTableWidget = view.NodeTableWidget