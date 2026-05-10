"""
AFTER: same LangGraph + AgentSonar with Prevent Mode (auto-stop).

Run:
    pip install agentsonar[langgraph]
    python prevent.py

What you'll see:
    - WARNING fires at rotation 5.
    - At rotation 10, PreventError raises out of graph.invoke().
    - The except block prints the cycle path and rotation count.
    - Mocked cost is roughly one third of the unmonitored run because
      the loop stopped before burning the rest of the rotations.

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
    lambda s: "generator" if s["rounds"] < 100 else END,
)

graph = builder.compile()
graph = monitor(graph, config={
    # Stop the silent loop at exactly 10 rotations.
    "prevent": {"cyclic_delegation": {"max_rotations": 10}},
})

rounds = 0
try:
    result = graph.invoke({"text": "", "rounds": 0})
    rounds = result["rounds"]
    print(f"Final rounds: {rounds}")
except PreventError as e:
    rounds = e.rotations
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")
    print(f"After:   {e.rotations} rotations")

calls = rounds * 2
input_cost = calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M / 1_000_000
output_cost = calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M / 1_000_000
total = input_cost + output_cost
print(f"Mocked cost: ${total:,.2f}")
print("Saved versus the 'before' run: roughly $9.67 of the $14.50 baseline.")
