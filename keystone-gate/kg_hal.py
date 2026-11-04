"""HAL — the LLM interface. Every answer goes through the gate.

Language only, never truth. The LLM (or the substrate's own walker) proposes
an answer; the gate decides whether it can be shown. If the gate rejects,
the answer is withheld — not shown with a warning, withheld.

For the substrate's own SymLM walker, "HAL" is a thin wrapper around
ask.answer_question. When a real LLM is wired up later, that LLM's output
still goes through gate.check before rendering.
"""
from answer.ask import answer_question, render as render_answer
from store.substrate import Substrate

from kg_gate import check as gate_check


def ask_ungated(s, question):
    """Direct substrate answer, no gate. For comparison/debugging."""
    return answer_question(s, question)


def ask_gated(s, question, sc=None):
    """Ask the substrate, then gate the result. Only gated answers are shown.

    Returns:
      {"gated": True, "answer": str, "check": {...}}
        on success
      {"gated": True, "rejected": True, "check": {...}, "question": str}
        on rejection
      {"gated": True, "no_intent": True, "question": str}
        when no intent matched (nothing to gate, nothing to answer)
    """
    proposed = {
        "input": question,
        "result": answer_question(s, question),
    }
    if proposed["result"] is None:
        return {
            "gated": True,
            "no_intent": True,
            "question": question,
        }

    compliance = gate_check(s, proposed, sc=sc)
    if not compliance["ok"]:
        return {
            "gated": True,
            "rejected": True,
            "check": compliance,
            "question": question,
        }

    return {
        "gated": True,
        "answer": render_answer(proposed["result"]),
        "check": compliance,
    }
