"""Backend A smoke test (retires risk R3): a real end-to-end manager-less run.

Runs a one-node plan (teachAS) through the deterministic orchestrator using the live
``copilot`` CLI as the worker backend, and prints the resulting artifact. This is a real
LLM call; keep the prompt tiny and tool-free.

Usage:
    python scripts/smoke_backend_a.py
"""

from __future__ import annotations

import sys

from agentsuite.contracts.models import Plan, Node
from agentsuite.orchestrator import Orchestrator
from agentsuite.registry import Registry
from agentsuite.runners import CopilotRunner


def main() -> int:
    plan = Plan(
        task_id="smoke-1",
        goal="Verify Backend A invokes a real AS agent and returns a valid artifact.",
        nodes=[
            Node(
                id="teach",
                agent="teachAS",
                prompt="In one sentence, what is an eigenvector? Do not use any tools; just answer.",
                produces="lesson",
                budget={"timeout_s": 180},
            )
        ],
    )

    runner = CopilotRunner(allow_all_tools=True)
    orch = Orchestrator(runner=runner, registry=Registry.load(),
                        event_sink=lambda e: print(f"  [event] {e['type']} {e.get('node_id','')}"))

    print("Running one-node plan through Backend A (live copilot)...\n")
    result = orch.run(plan)

    print(f"\nstatus: {result.status}")
    if result.error:
        print(f"error:  {result.error}")
    for aid, art in result.artifacts.items():
        print(f"\nartifact {aid!r} (status={art.status}, by={art.produced_by}):")
        print("  " + str(art.content.get("response", art.content))[:800])
        print(f"  provenance: exit={art.provenance.get('exit_code')} "
              f"model={art.provenance.get('model')} "
              f"cost={art.provenance.get('cost')}")

    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
