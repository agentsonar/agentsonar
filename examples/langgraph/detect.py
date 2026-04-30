"""
AgentSonar LangGraph adapter, detection only.

Run:
    pip install agentsonar[langgraph]
    python detect.py

This example uses pure Python nodes (no LLM calls), so it runs without
an API key. Replace the node functions with real LLM-backed nodes in
your own code; AgentSonar's wiring stays identical.

What you'll see:
    - Each node entry recorded as a delegation edge.
    - WARNING fires at rotation 5, CRITICAL at rotation 15.
    - agentsonar_logs/run-<latest>/report.html written on graph
      completion.
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


builder = StateGraph(State)
builder.add_node("generator", generator)
builder.add_node("reviewer",  reviewer)
builder.set_entry_point("generator")
builder.add_edge("generator", "reviewer")
# Reviewer never approves; the loop runs until rounds >= 30.
builder.add_conditional_edges(
    "reviewer",
    lambda s: "generator" if s["rounds"] < 30 else END,
)

graph = builder.compile()
graph = monitor(graph)  # one line

result = graph.invoke({"text": "", "rounds": 0})
print(f"Final rounds: {result['rounds']}")
