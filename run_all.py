"""
run_all.py
Stage:      master script (G3): rebuild every output from data/raw/ with one command.
Usage:      uv run python run_all.py                     # cleaning -> processing -> empirics
            uv run python run_all.py --with-collection   # also re-acquire raw data first
            uv run python run_all.py --stage empirics    # one stage only
            uv run python run_all.py --only clean_cbp    # one step only (name or substring)
            uv run python run_all.py --list              # show steps and dependencies, run nothing
            uv run python run_all.py --check             # afterwards, compare outputs with archive/baseline
            uv run python run_all.py --set-baseline      # afterwards, freeze outputs as the new baseline
Writes:     data/logs/run_all.log, data/logs/session_info.log, one appended row in
            attempts-log.csv (the only append-only file: it is a register, not an output),
            plus everything the steps write.

Each step runs in a fresh process with the project root as working directory and stops the
run on failure. Python steps use this interpreter (the uv .venv), R steps Rscript (renv
activates via .Rprofile), Stata steps batch mode. Every script must appear in STEPS, in run
order; `needs` lists steps whose outputs it reads, and is checked before running.
"""
import argparse
import csv
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RSCRIPT = os.environ.get("RSCRIPT", "Rscript")
CHECK_SCRIPT = "data/scripts/checks/check_baseline.py"

# (stage, script path, [names of steps it needs]); name = file stem
STEPS = [
    ("collection", "data/scripts/collection/acquire_rlms.py", []),
    ("collection", "data/scripts/collection/acquire_housing_prices.py", []),
    ("cleaning", "data/scripts/cleaning/clean_rlms.py", []),
    ("cleaning", "data/scripts/cleaning/clean_housing_prices.py", []),
    ("processing", "data/scripts/processing/process_longrun_2006.py", ['clean_rlms']),
    ("processing", "data/scripts/processing/process_housing_wealth.py", ['clean_rlms', 'clean_housing_prices']),
    ("processing", "data/scripts/processing/process_annual_panel.py", ['clean_rlms', 'clean_housing_prices']),
    ("empirics", "empirics/scripts/01_analyze_longrun_2006.py", ['process_longrun_2006']),
    ("empirics", "empirics/scripts/02_explore_figures.py", ['01_analyze_longrun_2006', 'process_longrun_2006', 'clean_rlms']),
    ("empirics", "empirics/scripts/03_analyze_housing_wealth.py", ['process_housing_wealth']),
    ("empirics", "empirics/scripts/05_analyze_event_study.py", ['process_annual_panel']),
    ("empirics", "empirics/scripts/06_explore_housing_figures.py", ['03_analyze_housing_wealth', 'process_housing_wealth', '05_analyze_event_study']),
]
STAGES = ["collection", "cleaning", "processing", "empirics"]


def stata_bin():
    return shutil.which("stata-mp") or shutil.which("stata-se") or shutil.which("stata") or "stata"


def command_for(script: str) -> list:
    suffix = Path(script).suffix
    if suffix == ".py":
        return [sys.executable, script]
    if suffix.lower() == ".r":
        return [RSCRIPT, script]
    if suffix == ".do":
        return [stata_bin(), "-b", "do", script]
    raise ValueError(f"don't know how to run {script}")


def git_commit() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                               text=True).stdout.strip()
        return h + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT,
                                capture_output=True).returncode == 0 if shutil.which("git") else False
        return "uncommitted" if inside else "no-git"


def log_attempt(what: str, command: str, outcome: str, details: str) -> None:
    path = ROOT / "attempts-log.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["timestamp", "actor", "what", "command", "outcome", "details", "git_commit"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "run_all", what, command,
                    outcome, details, git_commit()])


def session_info(steps) -> None:
    """Document the software environment of this run (G3)."""
    lines = [f"Python {platform.python_version()} ({sys.executable})", f"Platform {platform.platform()}",
             f"Commit {git_commit()}", ""]
    if shutil.which("uv"):
        out = subprocess.run(["uv", "pip", "freeze", "--python", sys.executable],
                             cwd=ROOT, capture_output=True, text=True)
        lines += ["# Python packages (uv pip freeze; pinned in uv.lock)", out.stdout.strip(), ""]
    if any(s.lower().endswith(".r") for _, s, _ in steps) and shutil.which(RSCRIPT):
        out = subprocess.run([RSCRIPT, "-e", "sessionInfo()"], cwd=ROOT, capture_output=True, text=True)
        lines += ["# R sessionInfo() (pinned in renv.lock)", (out.stdout or out.stderr).strip(), ""]
    if any(s.endswith(".do") for _, s, _ in steps):
        lines += ["# Stata: version and ado packages are listed in README.md", f"binary: {stata_bin()}", ""]
    (ROOT / "data/logs/session_info.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def stata_failed(script: str) -> bool:
    """Stata batch mode exits 0 on error; its batch log in the cwd shows r(###);."""
    batch_log = ROOT / (Path(script).stem + ".log")
    if not batch_log.exists():
        return False
    text = batch_log.read_text(errors="replace")
    batch_log.unlink()  # the do-file keeps its own log under data/logs or empirics/results/logs
    return bool(re.search(r"^r\(\d+\);", text, re.M))


def validate_steps() -> None:
    names = [Path(s).stem for _, s, _ in STEPS]
    for i, (stage, script, needs) in enumerate(STEPS):
        assert stage in STAGES, f"{script}: unknown stage {stage}"
        for n in needs:
            assert n in names[:i], f"{script} needs {n}, which is not an earlier step"
    nums = [int(Path(s).name[:2]) for st, s, _ in STEPS if st == "empirics" and Path(s).name[:2].isdigit()]
    assert nums == sorted(nums), f"empirics scripts are not numbered in run order: {nums}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-collection", action="store_true")
    ap.add_argument("--stage", choices=STAGES)
    ap.add_argument("--only")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set-baseline", action="store_true")
    args = ap.parse_args()
    validate_steps()

    steps = [s for s in STEPS if s[0] != "collection" or args.with_collection or args.stage == "collection"]
    if args.stage:
        steps = [s for s in steps if s[0] == args.stage]
    if args.only:
        steps = [s for s in steps if args.only in Path(s[1]).stem]
        if not steps:
            sys.exit(f"--only {args.only!r} matches no step")
    if args.list:
        for stage, script, needs in steps:
            print(f"{stage:<11} {script:<60} needs: {', '.join(needs) or '-'}")
        return

    (ROOT / "data/logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                        handlers=[logging.FileHandler(ROOT / "data/logs/run_all.log", mode="w"),
                                  logging.StreamHandler(sys.stdout)])
    log = logging.getLogger("run_all")
    invocation = "run_all.py " + " ".join(sys.argv[1:])
    log.info("START %s: %d steps", invocation, len(steps))
    session_info(steps)

    for stage, script, _ in steps:
        cmd = command_for(script)
        log.info("RUN [%s] %s", stage, " ".join(cmd))
        rc = subprocess.run(cmd, cwd=ROOT).returncode
        if rc != 0 or (script.endswith(".do") and stata_failed(script)):
            log.error("FAILED %s (exit %d); see its log", script, rc)
            log_attempt("pipeline run", invocation, "failure", f"failed at {script}")
            sys.exit(rc or 1)
        log.info("DONE %s", script)

    if args.set_baseline or args.check:
        flag = ["--set-baseline"] if args.set_baseline else []
        rc = subprocess.run([sys.executable, CHECK_SCRIPT] + flag, cwd=ROOT).returncode
        if args.check and rc != 0:
            log.warning("outputs differ from archive/baseline: see data/logs/check_baseline.log")
            log_attempt("pipeline run + baseline check", invocation, "failure",
                        "outputs differ from baseline")
            sys.exit(1)
    log.info("END run_all")
    log_attempt("pipeline run", invocation, "success", f"{len(steps)} steps")


if __name__ == "__main__":
    main()
