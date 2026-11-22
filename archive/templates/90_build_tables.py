"""
build_tables.py
Stage:      analysis: report tables (G6, D3)
Purpose:    Build the report's LaTeX tables from the machine-readable results files.
            Nothing in the paper's tables is typed by hand: edit this script, not the .tex.
Reads:      empirics/results/analyze_*.csv
Writes:     empirics/results/tables/*.tex, empirics/results/logs/build_tables.log
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data" / "scripts" / "utils"))
from pipeline import check, get_logger, project_root  # noqa: E402

# table name -> (estimates file, ordered specs, ordered terms with labels)
TABLES = {
    # "table4": ("analyze_assessor_panel_rci_table4.csv", ["s1_ols", "s2_controls", "s3_fe"],
    #             {"log_distance": "Log distance", "contiguity": "Contiguous"}),
}

log = get_logger("build_tables", log_dir="empirics/results/logs")
root = project_root()


def stars(p):
    return "^{***}" if p < 0.01 else "^{**}" if p < 0.05 else "^{*}" if p < 0.1 else ""


for name, (fname, specs, terms) in TABLES.items():
    est = pd.read_csv(root / "empirics/results" / fname)
    check(set(specs) <= set(est["spec"]), f"{name}: specs missing from {fname}: {set(specs) - set(est['spec'])}")
    lines = [r"\begin{tabular}{l" + "c" * len(specs) + "}", r"\hline",
             " & " + " & ".join(f"({i + 1})" for i in range(len(specs))) + r" \\", r"\hline"]
    for term, label in terms.items():
        cells, ses = [], []
        for s in specs:
            row = est[(est["spec"] == s) & (est["term"] == term)]
            if row.empty:
                cells.append(""); ses.append("")
            else:
                r = row.iloc[0]
                cells.append(f"${r.estimate:.3f}{stars(r.p_value)}$"); ses.append(f"({r.std_error:.3f})")
        lines += [label + " & " + " & ".join(cells) + r" \\", " & " + " & ".join(ses) + r" \\"]
    meta = est.drop_duplicates("spec").set_index("spec")
    lines += [r"\hline",
              "Observations & " + " & ".join(f"{int(meta.loc[s, 'nobs']):,}" for s in specs) + r" \\",
              "$R^2$ & " + " & ".join(f"{meta.loc[s, 'r2']:.3f}" for s in specs) + r" \\",
              r"\hline", r"\end{tabular}"]
    out = root / "empirics/results/tables" / f"{name}.tex"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("wrote", file=str(out.relative_to(root)))
log.info("end")
