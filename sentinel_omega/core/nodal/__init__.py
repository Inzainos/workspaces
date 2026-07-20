"""Node-level prediction framework for Sentinel Omega.

Converts global alerts ("WATCH on Earth") to node-specific alerts
("WATCH on nodes 14, 21, 57") for improved Molchan gain.
"""

from .node_aggregation import aggregate_nodes_from_signals
from .nodal_validation import validate_prediction_per_node

__all__ = [
    "aggregate_nodes_from_signals",
    "validate_prediction_per_node",
]
