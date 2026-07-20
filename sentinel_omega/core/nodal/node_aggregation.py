"""Extract and aggregate node-level predictions from agent signals."""

from typing import Any, Dict, List, Set
from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType


def aggregate_nodes_from_signals(signals: List[AgentSignal]) -> List[int]:
    """Extract all unique nodes mentioned in agent signals.

    When agents match firmas, they should include 'nodos' in signal.data
    (list of node_ids where the matching signature was strongest).
    This function aggregates all nodes from all signals to determine
    which geographic zones the alert applies to.

    Args:
        signals: List of AgentSignal objects from all bots

    Returns:
        Sorted list of unique node_ids mentioned across all signals.
        Empty list if no signals mention nodes.
    """
    nodos_set: Set[int] = set()

    for signal in signals:
        # Only aggregate nodes from ALERT and WATCH signals
        if signal.signal_type not in (SignalType.ALERT, SignalType.WATCH):
            continue

        # Extract nodos from signal.data if present
        nodos = signal.data.get("nodos")
        if nodos is None:
            continue

        # Handle both single node (int) and multiple nodes (list)
        if isinstance(nodos, int):
            nodos_set.add(nodos)
        elif isinstance(nodos, list):
            for nodo in nodos:
                if isinstance(nodo, int):
                    nodos_set.add(nodo)
                elif isinstance(nodo, (str, float)):
                    try:
                        nodos_set.add(int(nodo))
                    except (ValueError, TypeError):
                        pass  # Skip invalid values silently

    return sorted(list(nodos_set))


def nodes_from_firma_matches(matches: List[Dict[str, Any]]) -> List[int]:
    """Extract unique node_ids from a list of firma match results.

    Each match dict from signature_engine.match_estado_actual() contains
    an 'id_nodo' field. This function collects all unique nodes.

    Args:
        matches: List of match dicts from signature_engine.match_estado_actual()

    Returns:
        Sorted list of unique node_ids from matches.
    """
    nodos_set: Set[int] = set()

    for match in matches:
        nodo = match.get("id_nodo")
        if nodo is not None:
            if isinstance(nodo, int):
                nodos_set.add(nodo)
            else:
                try:
                    nodos_set.add(int(nodo))
                except (ValueError, TypeError):
                    pass

    return sorted(list(nodos_set))


def mark_alert_with_nodes(
    signal: AgentSignal,
    nodos: List[int],
    agent_name: str = None,
) -> AgentSignal:
    """Add node information to an alert signal.

    When a bot generates an ALERT or WATCH based on signature matches,
    mark the alert with the specific nodes where the signatures matched.

    Args:
        signal: The AgentSignal to enhance
        nodos: List of node_ids associated with this signal
        agent_name: Optional agent name for logging

    Returns:
        AgentSignal with 'nodos' added to data dict
    """
    if not nodos:
        return signal

    enhanced_data = {**signal.data, "nodos": nodos}

    return AgentSignal(
        agent_name=signal.agent_name,
        signal_type=signal.signal_type,
        confidence=signal.confidence,
        timestamp=signal.timestamp,
        data=enhanced_data,
        reasoning=signal.reasoning,
    )
