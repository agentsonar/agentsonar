"""
AFTER: same LangGraph + AgentSonar (detection only).

Run:
    pip install agentsonar[langgraph]
    python detect.py

This example uses pure Python nodes (no LLM calls), so it runs without
an API key. Replace the node functions with real LLM-backed nodes in
your own code; AgentSonar's wiring stays identical.

What you'll see:
    - Each node entry recorded as a delegation edge.
    - WARNING fires at rotation 5, CRITICAL at rotation 15.
    - agentsonar_logs/run-<latest>/report.html written on graph completion.
    - Same mocked cost as before/pipeline.py, but now you also know
      something went wrong.
"""
from typing import TypedDict

from agentsonar import monitor
from langgraph.graph import StateGraph, END


class State(TypedDict):
    text: str
    rounds: int


def generator(state):
    return {"text": state["text"] + "draft. ", "rounds": state["rounds"]}


def reviewer(state):
    return {"text": "needs more work", "rounds": state["rounds"] + 1}


ROTATIONS = 30
INPUT_TOKENS_PER_CALL = 3_000
OUTPUT_TOKENS_PER_CALL = 1_500
INPUT_PRICE_PER_M = 3.00
OUTPUT_PRICE_PER_M = 15.00

builder = StateGraph(State)
builder.add_node("generator", generator)
builder.add_node("reviewer",  reviewer)
builder.set_entry_point("generator")
builder.add_edge("generator", "reviewer")
builder.add_conditional_edges(
    "reviewer",
    lambda s: "generator" if s["rounds"] < ROTATIONS else END,
)

graph = builder.compile()
graph = monitor(graph)  # one line

result = graph.invoke({"text": "", "rounds": 0})

calls = result["rounds"] * 2
input_cost = calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M / 1_000_000
output_cost = calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M / 1_000_000
total = input_cost + output_cost
print(f"Final rounds: {result['rounds']}")
print(f"Mocked cost: ${total:,.2f}")
print("Done. Open agentsonar_logs/run-<latest>/report.html in a browser.")
