from langgraph.graph import StateGraph, START, END

from .state import FYPState
from .nodes import (
    solar_node,
    wind_node,
    demand_node,
    prepare_forecasts,
    optimization_node,
)


def build_graph():

    graph = StateGraph(FYPState)

    # Nodes
    graph.add_node("solar", solar_node)
    graph.add_node("wind", wind_node)
    graph.add_node("demand", demand_node)
    graph.add_node("prepare_forecasts", prepare_forecasts)
    graph.add_node("optimization", optimization_node)

    # Start parallel agents
    graph.add_edge(START, "solar")
    graph.add_edge(START, "wind")
    graph.add_edge(START, "demand")

    # All three must finish before preparation
    graph.add_edge("solar", "prepare_forecasts")
    graph.add_edge("wind", "prepare_forecasts")
    graph.add_edge("demand", "prepare_forecasts")

    # Prepare → Optimization
    graph.add_conditional_edges(
        "prepare_forecasts",
        lambda state: (
            "optimization"
            if state.get("status") == "ready_for_optimization"
            else END
        ),
        {
            "optimization": "optimization",
            END: END,
        },
    )

    graph.add_edge("optimization", END)

    return graph.compile()