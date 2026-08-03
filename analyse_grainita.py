#!/usr/bin/env python3
"""
GRAiNITA PoC analysis.

Reads the edm4hep output of ddsim, sums the calorimeter hits, and applies
a light-collection model on top of the Geant4 energy deposit.

The point of the smearing step: the raw Geant4 sum in a homogeneous
effective medium has essentially NO stochastic term — it only shows
leakage. GRAiNITA's actual resolution is set by photostatistics and
non-uniformity, which live outside the Geant4 geometry. So the honest
PoC is "Geant4 gives containment, a parametrisation gives resolution",
and this script keeps the two visibly separate.

Measured inputs (ALFA deck slide 93, arXiv:2312.07365):
    light yield         ~10000 p.e. / GeV   -> 1.0% / sqrt(E) stochastic
    non-uniformity      -> ~0.6% constant term

Usage:
    python analyse_grainita.py grainita_*.root
"""

import sys
import math
import numpy as np
from podio import root_io

# ---- light-collection model --------------------------------------------
PE_PER_GEV = 10000.0   # slide 93
CONST_TERM = 0.006     # slide 93, from the 1 mm surface scan
COLLECTION = "GrainitaEcalHits"

rng = np.random.default_rng(12345)


def smear(e_dep_gev):
    """Apply photostatistics + non-uniformity to a deposited energy."""
    if e_dep_gev <= 0.0:
        return 0.0
    n_pe = rng.poisson(PE_PER_GEV * e_dep_gev)
    e_pe = n_pe / PE_PER_GEV
    return e_pe * (1.0 + rng.normal(0.0, CONST_TERM))


def analyse(filename):
    reader = root_io.Reader(filename)
    events = reader.get("events")

    raw, smeared, ncells = [], [], []

    for event in events:
        hits = event.get(COLLECTION)
        cells = {}
        for hit in hits:
            cid = hit.getCellID()
            cells[cid] = cells.get(cid, 0.0) + hit.getEnergy()  # GeV
        total = sum(cells.values())
        raw.append(total)
        # smear per cell, then sum: photostatistics is per readout channel
        smeared.append(sum(smear(e) for e in cells.values()))
        ncells.append(len(cells))

    return np.array(raw), np.array(smeared), np.array(ncells)


def summarise(tag, arr):
    mu, sd = arr.mean(), arr.std()
    print(f"    {tag:10s}  mean = {mu:8.4f} GeV   sigma/mean = {100*sd/mu:6.3f} %")
    return mu, sd


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    print(f"\n{'file':<32} {'<E_raw>':>10} {'res_raw':>9} {'res_smeared':>12} {'<cells>':>8}")
    print("-" * 76)

    for fn in sys.argv[1:]:
        raw, sm, nc = analyse(fn)
        print(f"{fn:<32} {raw.mean():10.4f} "
              f"{100*raw.std()/raw.mean():8.3f}% "
              f"{100*sm.std()/sm.mean():11.3f}% "
              f"{nc.mean():8.1f}")

    print("""
Reading the output:
  res_raw      -> leakage + Geant4 fluctuation only. Should be small
                  (<1%) for a contained shower. If it is large, the
                  module is too short or too narrow, not "GRAiNITA is
                  bad".
  res_smeared  -> the number to compare against the deck's targets of
                  <2% stochastic and <1% constant.

Next step once this runs: scan gun energy over 1-50 GeV, fit
  sigma/E = a/sqrt(E) (+) b
and compare a, b against the <2% / <1% goals.
""")
