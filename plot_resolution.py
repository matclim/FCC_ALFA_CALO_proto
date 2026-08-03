#!/usr/bin/env python3
"""
Plot energy resolution versus beam energy, with the fitted curve.
 
    python plot_resolution.py /tmp/alfa_scan/e-_*GeV.root
    python plot_resolution.py --label "electrons, GRAiNITA ECAL" \
                              --out ecal_electrons.png \
                              /tmp/alfa_scan/e-_*GeV.root
 
Reuses the reading and fitting code from fit_resolution.py so the plot and
the printed numbers can never disagree.
"""
 
import sys
 
import matplotlib
matplotlib.use("Agg")          # headless: works over plain ssh
import matplotlib.pyplot as plt
import numpy as np
 
from fit_resolution import beam_energy, read_events, gaussian_core, fit_curve
 
args = sys.argv[1:]
 
 
def pop_opt(name, default):
    if name in args:
        i = args.index(name)
        val = args[i + 1]
        del args[i:i + 2]
        return val
    return default
 
 
label = pop_opt("--label", "")
out = pop_opt("--out", "resolution.png")
 
# Light-collection assumptions. These are PROTOTYPE MEASUREMENTS fed into
# the smearing, not outputs of the simulation: 10000 p.e./GeV forces a
# 1.0%/sqrt(E) stochastic term and 0.006 forces a 0.6% constant term. They
# are exposed here, and annotated on the figure, so nothing is hidden.
import fit_resolution as fr
fr.PE_PER_GEV = float(pop_opt("--pe-per-gev", str(fr.PE_PER_GEV)))
fr.CONST_TERM = float(pop_opt("--const-term", str(fr.CONST_TERM)))
files = sorted([a for a in args if a.endswith(".root")], key=beam_energy)
 
if not files:
    sys.exit(__doc__)
 
E, res_raw, res_sm, lin = [], [], [], []
for fn in files:
    e = beam_energy(fn)
    raw, sm, _ = read_events(fn)
    mu_r, sd_r = gaussian_core(raw)
    mu_s, sd_s = gaussian_core(sm)
    E.append(e)
    res_raw.append(sd_r / mu_r)
    res_sm.append(sd_s / mu_s)
    lin.append(mu_r / e)
    print(f"  {e:6.1f} GeV   raw {100*res_raw[-1]:6.3f} %   "
          f"smeared {100*res_sm[-1]:6.3f} %")
 
E = np.array(E)
res_raw = np.array(res_raw)
res_sm = np.array(res_sm)
 
a_s, b_s = fit_curve(E, res_sm)
a_r, b_r = fit_curve(E, res_raw)
 
fig, (ax, axl) = plt.subplots(
    2, 1, figsize=(7.0, 7.0), sharex=True,
    gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
 
Efine = np.linspace(max(E.min() * 0.5, 0.2), E.max() * 1.1, 400)
 
ax.plot(Efine, 100 * np.sqrt(a_s**2 / Efine + b_s**2), "-", color="#185FA5",
        lw=1.6, zorder=1,
        label=rf"fit: ${100*a_s:.2f}\%/\sqrt{{E}} \oplus {100*b_s:.2f}\%$")
ax.plot(E, 100 * res_sm, "o", color="#185FA5", ms=7, zorder=3,
        label="with light collection")
ax.plot(E, 100 * res_raw, "s", color="#993C1D", ms=5, mfc="none", zorder=2,
        label="Geant4 deposit only (containment)")
 
# The deck's design targets
ax.plot(Efine, 100 * np.sqrt(0.02**2 / Efine + 0.01**2), "--",
        color="#5F5E5A", lw=1.2, zorder=0,
        label=r"target: $2\%/\sqrt{E} \oplus 1\%$")
 
ax.set_ylabel(r"$\sigma_E / E$  [%]")
ax.set_ylim(bottom=0.0)
ax.grid(alpha=0.25, which="both", lw=0.5)
ax.legend(frameon=False, fontsize=9, loc="upper right")
if label:
    ax.set_title(label, fontsize=11)
 
# State the assumptions on the figure itself.
ax.text(0.98, 0.55,
        f"light collection assumed:\n"
        f"{fr.PE_PER_GEV:.0f} p.e./GeV, {100*fr.CONST_TERM:.1f}% non-uniformity\n"
        f"(prototype measurements, not simulated)",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=7.5, color="#5F5E5A")
 
axl.plot(E, lin, "o-", color="#0F6E56", ms=5, lw=1.2)
axl.axhline(1.0, color="#5F5E5A", lw=0.8, ls=":")
axl.set_xlabel("beam energy [GeV]")
axl.set_ylabel(r"$\langle E \rangle / E_{\rm beam}$", fontsize=9)
axl.grid(alpha=0.25, which="both", lw=0.5)
 
fig.savefig(out, dpi=160, bbox_inches="tight")
print(f"""
wrote {out}
 
    smeared   a = {100*a_s:5.2f} %   b = {100*b_s:5.2f} %
    raw       a = {100*a_r:5.2f} %   b = {100*b_r:5.2f} %
 
Note for any talk: the stochastic and constant terms are prototype
MEASUREMENTS fed into the smearing, not predictions of this simulation.
What the simulation shows is that the geometry adds almost nothing on top
(the open squares), i.e. 25 X0 at this radius contains electron showers.
""")

