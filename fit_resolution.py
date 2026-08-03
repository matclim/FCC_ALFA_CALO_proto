#!/usr/bin/env python3
"""
Fit the energy resolution from a ddsim energy scan.
 
    python fit_resolution.py /tmp/alfa_scan/e-_*GeV.root
 
Reads the beam energy from each filename, sums calorimeter hits per event,
applies the GRAiNITA light-collection model, fits a Gaussian to the peak
and then fits
 
    (sigma/E)^2 = a^2/E + b^2
 
which is linear in 1/E, so no minimiser is needed.
 
WHAT THE TWO COLUMNS MEAN
  raw       Geant4 deposited energy only. In a homogeneous medium this has
            almost no stochastic term -- it reflects leakage and shower
            fluctuations, nothing else. A small number here is NOT a good
            resolution, it just means the shower was contained.
  smeared   raw, with photostatistics (10k p.e./GeV) and non-uniformity
            (0.6%) applied per readout cell. This is the number to compare
            against the deck's targets of <2% stochastic, <1% constant.
 
If you only quote one number, quote the smeared one, and say what light
yield it assumed.
"""
 
import math
import re
import sys
 
import numpy as np
from podio import root_io
 
PE_PER_GEV = 10000.0   # ALFA deck slide 93
CONST_TERM = 0.006     # ALFA deck slide 93, from the 1 mm surface scan
 
rng = np.random.default_rng(12345)
 
 
def beam_energy(filename):
    m = re.search(r"_(\d+(?:\.\d+)?)GeV", filename)
    if not m:
        raise ValueError(f"cannot read beam energy from {filename}")
    return float(m.group(1))
 
 
def read_events(filename):
    """Return per-event (raw sum, smeared sum, n cells) in GeV."""
    reader = root_io.Reader(filename)
    events = reader.get("events")
 
    raw, smeared, ncell = [], [], []
    coll = None
 
    for event in events:
        if coll is None:
            # "Contributions" collections also match "Hits" but hold
            # MutableCaloHitContribution, which has no getCellID.
            names = [n for n in event.getAvailableCollections()
                     if "Hits" in n and "Contribution" not in n]
            if not names:
                avail = list(event.getAvailableCollections())
                raise RuntimeError(f"no calorimeter hit collection in {filename}\n"
                                   f"available: {avail}")
            coll = names[0]
 
        cells = {}
        for hit in event.get(coll):
            cid = hit.getCellID()
            cells[cid] = cells.get(cid, 0.0) + hit.getEnergy()
 
        total = sum(cells.values())
        raw.append(total)
 
        # Photostatistics is INDEPENDENT per readout channel: different
        # fibres, different photons. Summing independent Poissons gives
        # Poisson of the total, so this contributes exactly
        # 1/sqrt(PE_PER_GEV * E) = 1.0%/sqrt(E) at 10k p.e./GeV.
        sm = 0.0
        for e in cells.values():
            if e > 0:
                sm += rng.poisson(PE_PER_GEV * e) / PE_PER_GEV
 
        # Non-uniformity is COHERENT across the event: it comes from where
        # the shower sits relative to the fibre grid, so it shifts the whole
        # event one way. Applying it per cell instead would average it down
        # by sqrt(N_cells) and understate the constant term by ~30x.
        sm *= (1.0 + rng.normal(0.0, CONST_TERM))
        smeared.append(sm)
        ncell.append(len(cells))
 
    return np.array(raw), np.array(smeared), np.array(ncell)
 
 
def _truncation_factor(k):
    """
    Std of a Gaussian truncated at +-k sigma, in units of the true sigma.
 
        f(k) = sqrt(1 - 2 k phi(k) / (2 Phi(k) - 1))
 
    f(2) = 0.880, so taking the plain std of a +-2 sigma window
    underestimates the width by 12%. Dividing by f removes that bias.
    """
    phi = math.exp(-0.5 * k * k) / math.sqrt(2.0 * math.pi)
    Phi = 0.5 * (1.0 + math.erf(k / math.sqrt(2.0)))
    return math.sqrt(1.0 - 2.0 * k * phi / (2.0 * Phi - 1.0))
 
 
def gaussian_core(x, n_iter=4, nsigma=2.0):
    """
    Iterative truncated mean/sigma, corrected for truncation bias.
 
    Truncation is there to reject the low-side leakage tail, which is not
    Gaussian and would inflate the width. The correction factor puts the
    surviving width back on the scale of the underlying Gaussian.
    """
    x = x[x > 0]
    if len(x) < 10:
        return float("nan"), float("nan")
    corr = _truncation_factor(nsigma)
    mu, sd = x.mean(), x.std()
    for _ in range(n_iter):
        sel = np.abs(x - mu) < nsigma * sd
        if sel.sum() < 10:
            break
        # Un-bias INSIDE the loop. If the raw truncated width is fed back
        # as the window, each pass narrows the window further and the bias
        # compounds instead of converging.
        mu, sd = x[sel].mean(), x[sel].std() / corr
    return mu, sd
 
 
def fit_curve(E, res):
    """(sigma/E)^2 = a^2/E + b^2  -> linear in 1/E."""
    E, res = np.asarray(E), np.asarray(res)
    ok = np.isfinite(res) & (res > 0)
    if ok.sum() < 2:
        return float("nan"), float("nan")
    slope, intercept = np.polyfit(1.0 / E[ok], res[ok] ** 2, 1)
    a = np.sqrt(slope) if slope > 0 else float("nan")
    b = np.sqrt(intercept) if intercept > 0 else 0.0
    return a, b
 
 
if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        sys.exit(__doc__)
 
    files.sort(key=beam_energy)
 
    print(f"\n{'E [GeV]':>8} {'<E_raw>':>10} {'res_raw':>9} "
          f"{'<E_sm>':>10} {'res_sm':>9} {'cells':>7} {'lin':>7}")
    print("-" * 66)
 
    E_list, res_raw, res_sm = [], [], []
    for fn in files:
        E = beam_energy(fn)
        raw, sm, nc = read_events(fn)
        mu_r, sd_r = gaussian_core(raw)
        mu_s, sd_s = gaussian_core(sm)
        E_list.append(E)
        res_raw.append(sd_r / mu_r if mu_r else float("nan"))
        res_sm.append(sd_s / mu_s if mu_s else float("nan"))
        print(f"{E:8.1f} {mu_r:10.4f} {100*res_raw[-1]:8.3f}% "
              f"{mu_s:10.4f} {100*res_sm[-1]:8.3f}% {nc.mean():7.0f} "
              f"{mu_r/E:7.3f}")
 
    a_r, b_r = fit_curve(E_list, res_raw)
    a_s, b_s = fit_curve(E_list, res_sm)
 
    print(f"""
Fit  sigma/E = a/sqrt(E) (+) b
 
    raw       a = {100*a_r:5.2f} %    b = {100*b_r:5.2f} %
    smeared   a = {100*a_s:5.2f} %    b = {100*b_s:5.2f} %
 
    ALFA deck targets:  a < 2 %,  b < 1 %
 
The 'lin' column is <E_raw>/E_beam. It should be flat with energy. If it
drifts, that is non-linearity from leakage and it will inflate the constant
term. It will sit below 1 because of back leakage and the fibre dead
material -- that is a calibration constant, not a problem.
""")

