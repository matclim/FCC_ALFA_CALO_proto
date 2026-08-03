#!/usr/bin/env python3
"""
Combined ECAL + dual-readout HCAL resolution, as the experiment would see it.
 
    python analyse_hadrons.py \
        --calib-hcal /tmp/alfa_scan/hcalcal_e-_20GeV.root \
        --calib-ecal /tmp/alfa_scan/e-_20GeV.root \
        --plot pion_resolution.png \
        /tmp/alfa_scan/pi-_*GeV.root
 
THREE SIGNALS, THREE UNITS
 
  EcalBarrelHits   GeV            GRAiNITA, homogeneous, NOT dual readout
  DRBTScin         photoelectrons scintillation, Birks applied in the SD
  DRBTCher         photoelectrons Cherenkov, real optical photons tracked
 
  DRTubesSDAction stores p.e. in the energyDeposit field on purpose (it
  multiplies by CLHEP::GeV so EDM4hep's MeV->GeV division returns the raw
  count). So getEnergy() on an HCAL hit is a PHOTOELECTRON COUNT.
 
WHY TWO CALIBRATION FILES
 
  S and C must be calibrated where the EM fraction is known to be 1. In the
  full detector electrons never reach the HCAL -- the ECAL contains them,
  which is what the electron scan showed. So calibrate the HCAL channels
  with electrons fired at HcalBarrelTubes.xml, the HCAL-only geometry. That
  is the simulation equivalent of a test-beam calibration, and it is how
  IDEA calibrates too.
 
  The ECAL gets its own scale from electrons on EcalBarrelModular.xml.
 
THE DUAL-READOUT CORRECTION
 
      E = (S - chi*C) / (1 - chi),     chi = (1 - h/e|S) / (1 - h/e|C)
 
  Scintillation sees the whole shower (h/e ~ 0.8); Cherenkov sees mostly the
  EM part (h/e ~ 0.3). Combining them solves for the EM fraction event by
  event and removes the dominant source of hadronic resolution: fluctuation
  in that fraction. chi ~ 0.3 for fibre calorimeters; it is extracted here
  by scanning for the value that minimises the resolution.
 
THREE ESTIMATORS ARE REPORTED
 
  S only    ECAL + S. No dual readout. The baseline to beat.
  DR HCAL   ECAL + (S - chi*C)/(1 - chi). Correction applied to the HCAL
            alone, ECAL added as measured. Defensible: GRAiNITA is a
            separate device with its own calibration.
  DR all    (ECAL + S - chi*C)/(1 - chi). Treats the ECAL signal as
            scintillation-like and corrects the whole system together.
            Better when the pion showers early, since then the uncorrected
            ECAL term dominates. Not rigorous -- GRAiNITA's own e/h differs
            from the fibres' -- but it brackets the achievable performance.
 
  Quoting the better of the two DR numbers is fine as long as which one is
  stated.
"""
 
import math
import re
import sys
 
import numpy as np
from podio import root_io
 
ECAL_COLL = "EcalBarrelHits"
SCIN_COLL = "DRBTScin"
CHER_COLL = "DRBTCher"
 
 
def beam_energy(fn):
    m = re.search(r"_(\d+(?:\.\d+)?)GeV", fn)
    if not m:
        raise ValueError(f"cannot read beam energy from {fn}")
    return float(m.group(1))
 
 
def read(fn, quiet=False):
    """Per-event (ECAL GeV, S p.e., C p.e.)."""
    reader = root_io.Reader(fn)
    ecal, scin, cher = [], [], []
    checked = False
 
    for event in reader.get("events"):
        avail = set(event.getAvailableCollections())
        if not checked and not quiet:
            missing = [c for c in (ECAL_COLL, SCIN_COLL, CHER_COLL) if c not in avail]
            if missing:
                print(f"    note: {fn} has no {', '.join(missing)}")
            checked = True
 
        def tot(name):
            return sum(h.getEnergy() for h in event.get(name)) if name in avail else 0.0
 
        ecal.append(tot(ECAL_COLL))
        scin.append(tot(SCIN_COLL))
        cher.append(tot(CHER_COLL))
 
    return np.array(ecal), np.array(scin), np.array(cher)
 
 
def core(x, n_iter=4, k=2.0):
    """Truncated mean/sigma with the truncation bias divided out."""
    phi = math.exp(-0.5 * k * k) / math.sqrt(2 * math.pi)
    Phi = 0.5 * (1 + math.erf(k / math.sqrt(2)))
    corr = math.sqrt(1 - 2 * k * phi / (2 * Phi - 1))
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return float("nan"), float("nan")
    mu, sd = x.mean(), x.std()
    for _ in range(n_iter):
        sel = np.abs(x - mu) < k * sd
        if sel.sum() < 10:
            break
        mu, sd = x[sel].mean(), x[sel].std() / corr
    return mu, sd
 
 
def chi_from_correlation(S, C, E):
    """
    Measure chi from the S-C correlation, the standard DREAM method.
 
    For a shower with electromagnetic fraction f,
        S/E = f + h_S (1 - f)
        C/E = f + h_C (1 - f)
    Eliminating f gives C/E linear in S/E with slope
 
        m = (1 - h_C) / (1 - h_S) = 1 / chi
 
    so chi = 1/m.
 
    CAVEAT, and it is a big one: ordinary least squares is biased when the
    x variable carries noise (regression dilution). The fitted slope is
    attenuated by var(signal)/(var(signal)+var(noise)), so chi comes out too
    HIGH. With realistic resolutions the bias is tens of percent. A closure
    test with h_S=0.80, h_C=0.30 (true chi=0.286) returns 0.43.
 
    So this value is reported as a DIAGNOSTIC only. The chi actually applied
    is obtained by minimising the resolution globally, below.
    """
    S, C = np.asarray(S, float), np.asarray(C, float)
    ok = np.isfinite(S) & np.isfinite(C) & (S > 0.05 * E) & (C > 0)
    if ok.sum() < 20:
        return float("nan"), float("nan")
    m, q = np.polyfit(S[ok] / E, C[ok] / E, 1)
    if m <= 0:
        return float("nan"), float("nan")
    # crude uncertainty from a two-fold split of the sample
    half = ok.sum() // 2
    idx = np.where(ok)[0]
    ms = []
    for sub in (idx[:half], idx[half:]):
        if len(sub) > 10:
            ms.append(np.polyfit(S[sub] / E, C[sub] / E, 1)[0])
    spread = abs(ms[0] - ms[1]) / 2 if len(ms) == 2 else 0.0
    chi = 1.0 / m
    return chi, chi * spread / m if m else 0.0
 
 
def fit_curve(E, res):
    """(sigma/E)^2 = a^2/E + b^2, linear in 1/E."""
    E, res = np.asarray(E, float), np.asarray(res, float)
    ok = np.isfinite(res) & (res > 0)
    if ok.sum() < 2:
        return float("nan"), float("nan")
    slope, inter = np.polyfit(1.0 / E[ok], res[ok] ** 2, 1)
    return (math.sqrt(slope) if slope > 0 else float("nan"),
            math.sqrt(inter) if inter > 0 else 0.0)
 
 
def pop(args, name, default=None):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default
 
 
if __name__ == "__main__":
    args = sys.argv[1:]
    calib_hcal = pop(args, "--calib-hcal")
    calib_ecal = pop(args, "--calib-ecal")
    plot_out = pop(args, "--plot")
    chi_fixed = pop(args, "--chi")
    files = sorted([a for a in args if a.endswith(".root")], key=beam_energy)
 
    if not files or not calib_hcal:
        sys.exit(__doc__)
 
    # ---- HCAL channel calibration --------------------------------------
    E_h = beam_energy(calib_hcal)
    print(f"\nHCAL calibration: {calib_hcal} ({E_h:.0f} GeV electrons, no ECAL)")
    ec_h, s_h, c_h = read(calib_hcal)
    mu_s, _ = core(s_h)
    mu_c, _ = core(c_h)
    if mu_s <= 0 or mu_c <= 0:
        sys.exit("  S or C is empty. Check the geometry had no ECAL in front,\n"
                 "  and that optical photon production is enabled for C.")
    pe_s = mu_s / E_h
    pe_c = mu_c / E_h
    print(f"    S = {mu_s:10.0f} p.e.  ->  {pe_s:8.1f} p.e./GeV")
    print(f"    C = {mu_c:10.0f} p.e.  ->  {pe_c:8.1f} p.e./GeV")
    print(f"    C/S = {mu_c/mu_s:.3f}   (Cherenkov yield is normally the smaller)")
 
    # ---- ECAL scale ----------------------------------------------------
    ecal_scale = 1.0
    if calib_ecal:
        E_e = beam_energy(calib_ecal)
        ec_e, _, _ = read(calib_ecal, quiet=True)
        mu_e, _ = core(ec_e)
        ecal_scale = E_e / mu_e if mu_e > 0 else 1.0
        print(f"\nECAL calibration: {calib_ecal} ({E_e:.0f} GeV)")
        print(f"    <E> = {mu_e:.3f} GeV  ->  scale {ecal_scale:.4f}")
 
    # ---- read everything once ------------------------------------------
    data = {}
    for fn in files:
        E = beam_energy(fn)
        ec, s, c = read(fn, quiet=True)
        data[E] = (ec * ecal_scale, s / pe_s, c / pe_c)
 
    # ---- measure chi from the S-C correlation, one value per energy -----
    print("\nchi from the S-C correlation (DREAM method):")
    print(f"    {'E [GeV]':>8} {'chi':>8} {'+-':>7}")
    chi_vals, chi_wts = [], []
    for E in sorted(data):
        ec, S, C = data[E]
        chi, err = chi_from_correlation(S, C, E)
        print(f"    {E:8.1f} {chi:8.3f} {err:7.3f}")
        if np.isfinite(chi) and 0.0 < chi < 1.0:
            chi_vals.append(chi)
            chi_wts.append(1.0 / max(err, 1e-3) ** 2)
 
    if chi_vals:
        chi_corr = float(np.average(chi_vals, weights=chi_wts))
        print(f"\n    correlation estimate: chi = {chi_corr:.3f}")
        print("    (biased HIGH by regression dilution - diagnostic only)")
 
    # ---- chi by GLOBAL resolution minimisation -------------------------
    # chi is one detector constant. Fitting it separately at each energy
    # would be overfitting and would flatter the result. So minimise the
    # sum of relative resolutions over ALL energies with a single value.
    if chi_fixed:
        chi_global = float(chi_fixed)
        print(f"\n    using chi = {chi_global:.3f} (fixed on the command line)")
    else:
        scan = np.linspace(0.0, 0.7, 141)
        best = (float("inf"), 0.3)
        for chi in scan:
            if chi >= 1.0:
                continue
            tot_res = 0.0
            npts = 0
            for E in data:
                ec, S, C = data[E]
                t = (ec + S - chi * C) / (1.0 - chi)
                m, d = core(t)
                if m and np.isfinite(d):
                    tot_res += d / m
                    npts += 1
            if npts and tot_res / npts < best[0]:
                best = (tot_res / npts, chi)
        chi_global = best[1]
        print(f"\n    global chi = {chi_global:.3f}  "
              f"(one value for all energies, from resolution minimisation)")
        if chi_global <= 0.01 or chi_global >= 0.69:
            print("    WARNING: pinned at a scan boundary. Check the Cherenkov")
            print("    channel is populated before believing anything below.")
 
    # ---- resolutions at the single global chi --------------------------
    print(f"\n{'E':>6} {'ECAL':>8} {'S':>8} {'C':>8} {'C/S':>6} "
          f"{'S only':>9} {'DR HCAL':>9} {'DR all':>9}")
    print("-" * 72)
 
    E_list, r_s, r_dh, r_da = [], [], [], []
 
    for E in sorted(data):
        ec, S, C = data[E]
        mu_ec, _ = core(ec)
        mu_S, _ = core(S)
        mu_C, _ = core(C)
 
        mu0, sd0 = core(ec + S)
        res_s = sd0 / mu0 if mu0 else float("nan")
 
        th = ec + (S - chi_global * C) / (1.0 - chi_global)
        m, d = core(th)
        res_h = d / m if m else float("nan")
 
        ta = (ec + S - chi_global * C) / (1.0 - chi_global)
        m, d = core(ta)
        res_a = d / m if m else float("nan")
 
        E_list.append(E)
        r_s.append(res_s)
        r_dh.append(res_h)
        r_da.append(res_a)
 
        cs = mu_C / mu_S if mu_S else float("nan")
        print(f"{E:6.1f} {mu_ec:8.3f} {mu_S:8.3f} {mu_C:8.3f} {cs:6.3f} "
              f"{100*res_s:8.2f}% {100*res_h:8.2f}% {100*res_a:8.2f}%")
 
    a_s, b_s = fit_curve(E_list, r_s)
    a_h, b_h = fit_curve(E_list, r_dh)
    a_a, b_a = fit_curve(E_list, r_da)
 
    print(f"""
Fits, sigma/E = a/sqrt(E) (+) b
 
    S only    a = {100*a_s:5.1f} %   b = {100*b_s:5.2f} %
    DR HCAL   a = {100*a_h:5.1f} %   b = {100*b_h:5.2f} %
    DR all    a = {100*a_a:5.1f} %   b = {100*b_a:5.2f} %
 
IDEA quotes ~30 %/sqrt(E) as the dual-readout goal, against ~50 % without.
If DR here does not improve on 'S only', check that DRBTCher is populated
before concluding anything: an empty Cherenkov channel makes the correction
a no-op. A best-fit chi pinned at 0.00 or 0.70 means the scan hit its
boundary, which is also a symptom rather than a result.
""")
 
    if plot_out:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
 
        E = np.array(E_list, float)
        Ef = np.logspace(math.log10(E.min() * 0.8), math.log10(E.max() * 1.25), 200)
        fig, ax = plt.subplots(figsize=(7, 5))
        for res, a, b, col, lab in (
                (r_s, a_s, b_s, "#993C1D", "scintillation only"),
                (r_dh, a_h, b_h, "#185FA5", "dual readout, HCAL"),
                (r_da, a_a, b_a, "#0F6E56", "dual readout, whole system")):
            ax.plot(E, 100 * np.array(res), "o", color=col, ms=6, label=lab)
            if np.isfinite(a):
                ax.plot(Ef, 100 * np.sqrt(a ** 2 / Ef + b ** 2), "-", color=col, lw=1.4)
        ax.plot(Ef, 100 * np.sqrt(0.30 ** 2 / Ef), "--", color="#5F5E5A", lw=1.1,
                label=r"IDEA goal $30\%/\sqrt{E}$")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("beam energy [GeV]")
        ax.set_ylabel(r"$\sigma_E/E$  [%]")
        ax.set_title("Pions, GRAiNITA ECAL + dual-readout tube HCAL", fontsize=11)
        ax.grid(alpha=0.25, which="both", lw=0.5)
        ax.legend(frameon=False, fontsize=9)
        fig.savefig(plot_out, dpi=160, bbox_inches="tight")
        print(f"wrote {plot_out}")

