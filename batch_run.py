r"""
batch_run.py - execute RUN_pLCA.ipynb once per prepared scenario, unattended.

WHAT THIS IS FOR

    Running several scenarios back to back by supplying the notebook's
    constants cell (its twelve answers) from a file, one file per scenario.
    The constants cell's source is replaced before executing, so the notebook
    asks no questions.

THE INPUT FILES

    batch_runs_inputs/inputs_S1.txt, inputs_S3.txt, ... - one file per
    scenario, each holding exactly the twelve assignments of the constants
    cell, in valid Python syntax:

        PROJECT_NAME           = "plca_nest"
        EI_VERSION              = "3.11"
        ...
        SCENARIO_DB_NAME        = "S1"

    Each file is exec()'d in an empty namespace, so a typo raises a normal
    Python error before anything is launched.

WHAT IT DOES TO THE NOTEBOOK

    Nothing durable: the notebook is read with nbformat, executed from memory
    and never written back. A fresh copy is read for every scenario.

/!\ WARNINGS, PER SCENARIO

    SCENARIO_DB_NAME must not collide with an existing database you want to
    keep. create_scenario_db() would ask before deleting it, but stdin is
    closed here, so the prompt fails the scenario instead of overwriting
    anything. Duplicate names among the batch's own input files are refused
    up front.

    The ecoinvent database and the premise background database must already
    exist in the project: importing or generating them asks for credentials,
    which fails here for the same reason. Run one scenario interactively
    first.

ON FAILURE

    A failing scenario does not abort the batch by default: the failure is
    logged, its kernel is shut down and the next input file starts fresh.
    Pass --stop-on-failure for the opposite.

USAGE

    python batch_run.py RUN_pLCA.ipynb --inputs-dir batch_runs_inputs
    python batch_run.py RUN_pLCA.ipynb batch_runs_inputs/inputs_S1.txt

    Run from pLCA-NEST/ with the project's interpreter. Writes
    batch_run_<SCENARIO_DB_NAME>.json per scenario and batch_run_summary.json
    at the end.
"""

import argparse
import glob
import json
import os
import sys
import time

import queue

import nbformat
from jupyter_client.manager import KernelManager

# How long one cell may run before it is abandoned [s], and how often the
# iopub channel is polled while it runs [s].
CELL_TIMEOUT = 6 * 60 * 60
POLL_INTERVAL = 0.25


def start_kernel(kernel_name):
    """Start a Jupyter kernel and return (manager, client)."""
    km = KernelManager(kernel_name=kernel_name)
    km.start_kernel(cwd=os.getcwd())
    kc = km.client()
    kc.start_channels()
    kc.wait_for_ready(timeout=120)
    return km, kc


def check_interpreter(kc):
    """Print the kernel's Python next to this script's, and warn if they differ."""
    out = []
    kc.execute("import sys; print(sys.executable)")
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=60)
        except queue.Empty:
            break
        if msg["msg_type"] == "stream":
            out.append(msg["content"]["text"])
        if (msg["msg_type"] == "status"
                and msg["content"]["execution_state"] == "idle"):
            break
    kernel_python = "".join(out).strip()
    print(f"  kernel interpreter : {kernel_python}")
    print(f"  this script's      : {sys.executable}")
    if os.path.normcase(kernel_python) != os.path.normcase(sys.executable):
        print("  /!\\  The kernel runs a different Python environment from "
              "this script.")
    return kernel_python


def run_cell(kc, source):
    """Execute one cell, echoing its output. Returns (seconds, error or None).

    stdin is closed, so a cell that prompts for input fails at once instead of
    waiting until CELL_TIMEOUT.
    """
    started = time.perf_counter()
    kc.execute(source, allow_stdin=False)
    error = None
    while True:
        if time.perf_counter() - started > CELL_TIMEOUT:
            return time.perf_counter() - started, "TIMEOUT"
        try:
            msg = kc.get_iopub_msg(timeout=POLL_INTERVAL)
        except queue.Empty:
            continue
        kind = msg["msg_type"]
        if kind == "stream":
            sys.stdout.write(msg["content"]["text"])
            sys.stdout.flush()
        elif kind == "error":
            error = "\n".join(msg["content"]["traceback"])
        elif (kind == "status"
              and msg["content"]["execution_state"] == "idle"):
            break
    return time.perf_counter() - started, error


# The constants cell's twelve names, in the order RUN_pLCA.ipynb declares
# them. Checked against every input file so a missing or misspelled one is
# caught before any kernel is started, not mid-batch.
REQUIRED_CONSTANTS = [
    "PROJECT_NAME", "EI_VERSION", "EI_MODEL", "PREMISE_SOURCE_DB",
    "PREMISE_SOURCE_VERSION", "PREMISE_MODEL", "PREMISE_PATHWAY",
    "PREMISE_YEAR", "EI_BACKGROUND", "BIO_BACKGROUND", "DATA_INPUT",
    "SCENARIO_DB_NAME",
]


def load_constants(path):
    """exec() one input file and return its twelve constants, in order.

    The file IS Python source - the same syntax as the constants cell - so
    this is not a parser, it is the interpreter. A missing name, a stray
    comma, a bad string: all raise here, before any kernel is started.
    """
    namespace = {}
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    exec(compile(source, path, "exec"), {}, namespace)

    missing = [name for name in REQUIRED_CONSTANTS if name not in namespace]
    if missing:
        raise ValueError(f"{path}: missing {missing}")
    extra = [name for name in namespace if name not in REQUIRED_CONSTANTS]
    if extra:
        raise ValueError(
            f"{path}: {extra} are not names the constants cell has - "
            f"a typo, most likely")
    return {name: namespace[name] for name in REQUIRED_CONSTANTS}


def find_constants_cell(nb):
    """The index of RUN_pLCA.ipynb's constants cell.

    Identified by content: a code cell defining both PROJECT_NAME and
    SCENARIO_DB_NAME.
    """
    for i, cell in enumerate(nb.cells):
        if (cell.cell_type == "code"
                and "PROJECT_NAME" in cell.source
                and "SCENARIO_DB_NAME" in cell.source):
            return i
    raise ValueError(
        "no constants cell found - expected a code cell defining "
        "PROJECT_NAME and SCENARIO_DB_NAME. Has RUN_pLCA.ipynb changed?")


def constants_source(constants):
    """The replacement cell source: one `NAME = repr(value)` line each.

    repr() rather than the input file's own text, so a batch run does not
    depend on how that file happened to format its values - "3.11" and
    2030 both round-trip correctly through repr(), which is all that
    matters here.
    """
    return "\n".join(f"{name} = {constants[name]!r}"
                     for name in REQUIRED_CONSTANTS)


def check_for_duplicate_names(all_constants):
    """Refuse to start if two input files share a SCENARIO_DB_NAME.

    Only checks within THIS batch - see the module docstring's warning about
    what it cannot know.
    """
    seen = {}
    for path, constants in all_constants:
        name = constants["SCENARIO_DB_NAME"]
        if name in seen:
            raise ValueError(
                f"SCENARIO_DB_NAME {name!r} is used by both {seen[name]} "
                f"and {path} - the second run would delete the first's "
                f"database. Rename one.")
        seen[name] = path


def warn_before_batch(scenarios, assume_yes):
    print("=" * 78)
    print(f"ABOUT TO RUN {len(scenarios)} SCENARIO(S), UNATTENDED:")
    for path, constants in scenarios:
        print(f"  {constants['SCENARIO_DB_NAME']:20s} "
              f"<- {constants['DATA_INPUT']:30s} ({path})")
    print("""
  Each SCENARIO_DB_NAME above must not name a database another run is
  diffed against - RUN_pLCA.ipynb's create_scenario_db() would otherwise
  raise trying to ask about it (stdin is closed for a batch run - see the
  module docstring). If the background for a scenario is not already
  built, that scenario builds it, and that dominates its wall time.
""")
    if assume_yes:
        return
    reply = input("Type RUN to continue, anything else to abort: ").strip()
    if reply != "RUN":
        sys.exit("aborted - nothing was executed")


def run_one(notebook_path, constants, kernel_name):
    """Run RUN_pLCA.ipynb once with `constants` substituted in. Returns a dict."""
    label = constants["SCENARIO_DB_NAME"]
    nb = nbformat.read(notebook_path, as_version=4)
    idx = find_constants_cell(nb)
    nb.cells[idx].source = constants_source(constants)
    cells = [c for c in nb.cells if c.cell_type == "code" and c.source.strip()]

    print(f"\n{'=' * 78}\nSCENARIO {label}  ({len(cells)} code cell(s))\n{'=' * 78}")

    km, kc = start_kernel(kernel_name)
    check_interpreter(kc)

    per_cell = []
    failed = None
    started = time.perf_counter()
    try:
        for i, cell in enumerate(cells, 1):
            first = cell.source.strip().splitlines()[0][:60]
            print(f"\n--- [{label}] cell {i}/{len(cells)}  {first}")
            seconds, error = run_cell(kc, cell.source)

            per_cell.append({"cell": i, "seconds": seconds,
                             "first_line": first})
            print(f"--- [{label}] cell {i} took {seconds:.1f} s")
            if error:
                failed = {"cell": i, "traceback": error}
                print(f"\n/!\\ [{label}] CELL {i} RAISED - stopping this "
                      f"scenario.\n{error}")
                break
        wall = time.perf_counter() - started
    finally:
        kc.stop_channels()
        km.shutdown_kernel(now=True)

    result = {
        "label": label,
        "data_input": constants["DATA_INPUT"],
        "notebook": notebook_path,
        "cells_executed": len(per_cell),
        "cells_total": len(cells),
        "wall_seconds": wall,
        "failed": failed,
        "per_cell": per_cell,
    }
    out = f"batch_run_{label}.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"\n[{label}] {'FAILED' if failed else 'done'} in "
          f"{wall / 60:,.1f} min - written to {out}")
    return result


def main():
    ap = argparse.ArgumentParser(
        description="Execute RUN_pLCA.ipynb once per prepared scenario, "
                    "unattended, substituting each input file's twelve "
                    "constants for the constants cell.")
    ap.add_argument("notebook", help="the .ipynb to execute, e.g. RUN_pLCA.ipynb")
    ap.add_argument("inputs", nargs="*",
                    help="one or more input files. If omitted, every "
                         "inputs_*.txt under --inputs-dir is used, sorted.")
    ap.add_argument("--inputs-dir", default="batch_runs_inputs",
                    help="directory to glob inputs_*.txt from when no "
                         "explicit input files are given "
                         "(default: batch_runs_inputs)")
    ap.add_argument("--kernel", default="python3",
                    help="kernelspec name (default: python3)")
    ap.add_argument("--stop-on-failure", action="store_true",
                    help="abort the whole batch on the first scenario that "
                         "fails, instead of moving on to the next one")
    ap.add_argument("--yes", action="store_true",
                    help="skip the confirmation prompt - only once you have "
                         "read the warnings and checked every "
                         "SCENARIO_DB_NAME")
    args = ap.parse_args()

    if not os.path.exists(args.notebook):
        sys.exit(f"no such notebook: {args.notebook}")

    input_paths = args.inputs or sorted(
        glob.glob(os.path.join(args.inputs_dir, "inputs_*.txt")))
    if not input_paths:
        sys.exit(f"no input files - gave none and found none matching "
                 f"{args.inputs_dir}/inputs_*.txt")

    scenarios = [(path, load_constants(path)) for path in input_paths]
    check_for_duplicate_names(scenarios)
    warn_before_batch(scenarios, args.yes)

    results = []
    batch_started = time.perf_counter()
    for path, constants in scenarios:
        result = run_one(args.notebook, constants, args.kernel)
        results.append(result)
        if result["failed"] and args.stop_on_failure:
            print(f"\n/!\\ STOPPING BATCH - {result['label']} failed and "
                  f"--stop-on-failure was given.")
            break
    batch_wall = time.perf_counter() - batch_started

    print(f"\n{'=' * 78}\nBATCH SUMMARY\n{'=' * 78}")
    for result in results:
        status = "FAILED" if result["failed"] else "ok"
        print(f"  {result['label']:20s} {status:8s} "
              f"{result['wall_seconds'] / 60:8,.1f} min")
    print(f"  {'TOTAL':20s} {'':8s} {batch_wall / 60:8,.1f} min")
    ran = len(results)
    failed_count = sum(1 for r in results if r["failed"])
    print(f"  {ran} of {len(scenarios)} scenario(s) run, "
          f"{failed_count} failed")

    with open("batch_run_summary.json", "w", encoding="utf-8") as fh:
        json.dump({"batch_wall_seconds": batch_wall, "results": results},
                  fh, indent=2)
    print(f"  written to batch_run_summary.json")
    print("=" * 78)

    if failed_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
