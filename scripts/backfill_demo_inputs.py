"""One-off: backfill provenance.inputs onto a COPY of the innovation-digest run store.

The recorded innovation-digest run predates the copilot-backend fix that records
provenance.inputs, so its derived DAG renders edge-less. The plan's declared dependencies are
the real ones that executed, so we reconstruct each artifact's provenance.inputs from the plan
and write to a COPY (never the evidence DB). Result: a demo store whose DAG renders the true
research -> critique -> worker -> extension chain.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

SRC = Path(r"C:\Code\innovation-digest\.run\run.db")
DST = Path(r"C:\Code\innovation-digest\.run\run-demo.db")
PLAN = Path(r"C:\Code\innovation-digest\plan.v1.json")


def main() -> int:
    if not SRC.exists() or not PLAN.exists():
        print(f"missing source: {SRC if not SRC.exists() else PLAN}")
        return 1
    shutil.copy2(SRC, DST)

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    # produces -> declared input artifact ids (the plan node.inputs are artifact ids)
    inputs_for = {n["produces"]: list(n.get("inputs", [])) for n in plan["nodes"]}

    conn = sqlite3.connect(DST)
    conn.row_factory = sqlite3.Row
    updated = []
    for row in conn.execute("SELECT task_id, id, provenance FROM artifacts").fetchall():
        prov = json.loads(row["provenance"]) if row["provenance"] else {}
        if not prov.get("inputs") and inputs_for.get(row["id"]):
            prov["inputs"] = sorted(inputs_for[row["id"]])
            conn.execute("UPDATE artifacts SET provenance=? WHERE task_id=? AND id=?",
                         (json.dumps(prov), row["task_id"], row["id"]))
            updated.append(f'{row["id"]} <- {prov["inputs"]}')
    conn.commit()
    conn.close()
    print(f"backfilled {len(updated)} artifacts into {DST.name}:")
    for u in updated:
        print("  " + u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
