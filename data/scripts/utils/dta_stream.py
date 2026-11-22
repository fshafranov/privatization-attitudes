"""dta_stream.py — read selected columns from a Stata 118 .dta arriving on stdin (screening utility).

The RLMS individual file is 16 GB uncompressed and does not fit on disk, so it is streamed out
of the .7z archive and only the requested numeric columns are kept. Strings (strL) and value
labels are not parsed; labels come from the HSE codebook.

Usage:
  tar -xOf data/raw/rlms/RLMS_IND_1994_2025_eng_DTA.7z | \
      uv run python -I data/scripts/utils/dta_stream.py --list PATTERN...         # print matching names+labels
  tar -xOf ... | uv run python -I data/scripts/utils/dta_stream.py --out FILE.pkl COL...   # extract columns
"""

import re
import struct
import sys

import numpy as np
import pandas as pd

TYPES = {65526: ("<f8", 8), 65527: ("<f4", 4), 65528: ("<i4", 4), 65529: ("<i2", 2), 65530: ("i1", 1)}
MISS = {"<f8": 8.988e307, "<f4": 1.701e38, "<i4": 2147483620, "<i2": 32740, "i1": 100}


def read_exact(f, n):
    b = f.read(n)
    if len(b) != n:
        raise EOFError(f"expected {n} bytes, got {len(b)}")
    return b


def expect(f, tag):
    b = read_exact(f, len(tag))
    if b != tag:
        raise ValueError(f"expected {tag!r}, found {b!r}")


def read_header(f):
    expect(f, b"<stata_dta><header><release>118</release><byteorder>LSF</byteorder><K>")
    k = struct.unpack("<H", read_exact(f, 2))[0]
    expect(f, b"</K><N>")
    n = struct.unpack("<Q", read_exact(f, 8))[0]
    expect(f, b"</N><label>")
    read_exact(f, struct.unpack("<H", read_exact(f, 2))[0])
    expect(f, b"</label><timestamp>")
    read_exact(f, struct.unpack("<B", read_exact(f, 1))[0])
    expect(f, b"</timestamp></header><map>")
    offsets = struct.unpack("<14Q", read_exact(f, 112))
    expect(f, b"</map>")
    pos = offsets[1] + len(b"<map>") + 112 + len(b"</map>")
    # everything up to the data section is read as one block
    block = read_exact(f, offsets[9] - pos)
    base = pos

    def section(i, j):
        return block[offsets[i] - base : offsets[j] - base]

    vt = section(2, 3)
    vt = vt[len(b"<variable_types>") : -len(b"</variable_types>")]
    vtypes = struct.unpack(f"<{k}H", vt)
    vn = section(3, 4)[len(b"<varnames>") : -len(b"</varnames>")]
    names = [vn[i * 129 : (i + 1) * 129].split(b"\0")[0].decode() for i in range(k)]
    vl = section(7, 8)[len(b"<variable_labels>") : -len(b"</variable_labels>")]
    labels = [vl[i * 321 : (i + 1) * 321].split(b"\0")[0].decode("utf-8", "replace") for i in range(k)]
    expect(f, b"<data>")
    return k, n, vtypes, names, labels


def main():
    args = sys.argv[1:]
    f = sys.stdin.buffer
    if args[0] == "--list":
        k, n, vtypes, names, labels = read_header(f)
        pats = [re.compile(p) for p in args[1:]]
        print(f"K={k} N={n}")
        for nm, lb, t in zip(names, labels, vtypes):
            if any(p.fullmatch(nm) for p in pats):
                print(f"{nm}\t{t}\t{lb.strip()}")
        return
    read_columns(f, args[2:]).to_pickle(args[1])


def read_columns(f, cols):
    """Return a DataFrame of the requested numeric columns (float64, Stata missing -> NaN)
    from a binary stream positioned at the start of a Stata 118 file."""
    k, n, vtypes, names, labels = read_header(f)
    missing = [c for c in cols if c not in names]
    if missing:
        raise KeyError(f"columns not in file: {missing}")
    fields, offset = [], 0
    spec = {}
    for nm, t in zip(names, vtypes):
        if t in TYPES:
            dt, w = TYPES[t]
        elif t <= 2045:
            dt, w = f"S{t}", t
        elif t == 32768:
            dt, w = "S8", 8
        else:
            raise ValueError(f"unknown type {t} for {nm}")
        if nm in cols:
            spec[nm] = (dt, offset)
        offset += w
    width = offset
    dtype = np.dtype({"names": list(spec), "formats": [v[0] for v in spec.values()],
                      "offsets": [v[1] for v in spec.values()], "itemsize": width})
    chunk_rows = max(1, 200_000_000 // width)
    parts, done = [], 0
    while done < n:
        m = min(chunk_rows, n - done)
        arr = np.frombuffer(read_exact(f, m * width), dtype=dtype)
        part = pd.DataFrame({c: arr[c].astype("f8") for c in spec})
        for c, (dt, _) in spec.items():
            part.loc[part[c] > MISS[dt], c] = np.nan
        parts.append(part)
        done += m
        print(f"rows {done}/{n}", file=sys.stderr)
    out = pd.concat(parts, ignore_index=True)
    if len(out) != n:
        raise ValueError(f"header says N={n}, read {len(out)} rows")
    return out


if __name__ == "__main__":
    main()
