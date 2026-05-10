"""
BEFORE: a LangGraph state graph with a silent loop. No monitoring.

Run:
    pip install langgraph
    python pipeline.py

What you'll see:
    - 30 rotations finish quietly.
    - A printed "all done" line and a mocked cost number.
    - Nothing tells you the reviewer never approved.

This is the silent failure: a node that loops back to itself, bouncing
work without converging. Your only signal is a token bill that arrives
later.

The mocked cost is based on Claude Sonnet 4.6 input pricing as of
2026-05-09 ($3 / 1M input tokens, $15 / 1M output tokens). See:
    https://www.anthropic.com/pricing
We assume ~3,000 input tokens and ~1,500 output tokens per node call,
two nodes per rotation, 30 rotations -> roughly $14.50 per run.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END


class State(TypedDict):
    text: str
    rounds: int


def generator(state):
    return {"text": state["text"] + "draft. ", "rounds": state["rounds"]}


def reviewer(state):
    # Reviewer never approves.
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
result = graph.invoke({"text": "", "rounds": 0})

calls = result["rounds"] * 2
input_cost = calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M / 1_000_000
output_cost = calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M / 1_000_000
total = input_cost + output_cost

print(f"{result['rounds']} rotations completed.")
print(f"Mocked cost: ${total:,.2f}")
print("All done.")
