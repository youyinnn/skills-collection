"""Convert every PDF under inputs/papers/<venue>/ to markdown with Marker, into
derived/papers_marker/<venue>/<paper>/ (md, meta.json, extracted images). Already-converted papers are
skipped, so a rerun converts only the new PDFs.

Needs the `marker` command (`uv tool install marker-pdf==2.0.0`, or `pip install marker-pdf`). On macOS
the recognition model runs through llama.cpp, so `llama-server` must be on PATH (`brew install llama.cpp`);
on other platforms Marker runs it through torch. Marker's default mode is used.

  python scripts/convert_pdfs_marker.py            # every venue folder
  python scripts/convert_pdfs_marker.py ICSE CHI   # selected venue folders
"""
import os
import shutil
import subprocess
import sys
import time

from config import ROOT


def main(venues):
    marker = shutil.which("marker")
    if not marker:
        sys.exit("missing marker: uv tool install marker-pdf==2.0.0 (or pip install marker-pdf)")
    if sys.platform == "darwin" and not shutil.which("llama-server"):
        sys.exit("missing llama-server: brew install llama.cpp")
    src = os.path.join(ROOT, "inputs", "papers")
    out = os.path.join(ROOT, "derived", "papers_marker")
    venues = venues or sorted(d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)))
    start = time.time()
    for v in venues:
        d = os.path.join(src, v)
        if not os.path.isdir(d):
            print(f"no such venue folder: {v}")
            continue
        n = sum(1 for f in os.listdir(d) if f.lower().endswith(".pdf"))
        if not n:
            continue
        print(f"=== {v} ({n} pdf) {time.strftime('%H:%M:%S')}", flush=True)
        with subprocess.Popen([marker, d, "--output_dir", os.path.join(out, v), "--output_format", "markdown",
                               "--skip_existing", "--workers", "1"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace") as p:
            for line in p.stdout:   # printed as they come: a long run shows its errors while it runs
                if "Traceback" in line or "rror" in line:   # Error / error lines only
                    print(line, end="", flush=True)
    mds = sum(f.endswith(".md") for _, _, fs in os.walk(out) for f in fs) if os.path.isdir(out) else 0
    print(f"=== done in {int(time.time() - start)} s; md files: {mds}")


if __name__ == "__main__":
    main(sys.argv[1:])
