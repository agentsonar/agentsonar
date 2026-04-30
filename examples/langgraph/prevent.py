"""
AgentSonar LangGraph adapter, with Prevent Mode.

Run:
    pip install agentsonar[langgraph]
    python prevent.py

What you'll see:
    - WARNING fires at rotation 5.
    - At rotation 15, PreventError raises out of graph.invoke().
    - The except block prints the cycle path and rotation count.

Same graph as detect.py. Only difference: prevent={...} in the
monitor() config and a try/except around graph.invoke().
"""
from typing import TypedDict

from agentsonar import monitor, PreventError
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
builder.add_conditional_edges(
    "reviewer",
    lambda s: "generator" if s["rounds"] < 100 else END,
)

graph = builder.compile()
graph = monitor(graph, config={
    "prevent": {"cyclic_delegation": True}
})

try:
    result = graph.invoke({"text": "", "rounds": 0})
    print(f"Final rounds: {result['rounds']}")
except PreventError as e:
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")
    print(f"After:   {e.rotations} rotations")
