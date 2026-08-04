# ALFA calorimeter proof-of-concept simulation

Key4hep/DD4hep simulation of the calorimeter system for **ALFA**, the fifth
FCC-ee detector concept (emerged at the Garching workshop, January 2026):

* **ECAL** — GRAiNITA, ~1 mm ZnWO₄ grains in a heavy tungstate liquid, read
  out by WLS fibres. Built here from scratch.
* **HCAL** — dual-readout capillary tubes with iron absorber, reusing
  k4geo's `DRBarrelTubes` constructor unchanged.

Barrel only. No endcaps, no tracker, no ARC, **no coil**.

---

## Status

| | state |
|---|---|
| GRAiNITA test module, 17×17×40 cm³ | builds, 625 fibres, validated |
| GRAiNITA barrel, 2430 modules | builds, no overlaps, 25.0 X₀ |
| DR tube HCAL barrel | builds, S and C both live |
| Electron resolution | done: 1.1%/√E ⊕ 0.7% |
| Pion resolution | jobs submitted |
| Mechanical structure | not started |
| Endcaps | not started |

---

## Physics results so far

### Materials, independently confirmed

The GRAiNITA mixture is 80/20 ZnWO₄/liquid **by mass**. That fixes the grain
packing fraction at 0.587, giving ρ = 5.78 g/cm³ and X₀ = 1.595 cm. DD4hep
computes 1.5950 against 1.601 by hand, and **25 X₀ = 40.0 cm reproduces the
demonstrator depth quoted on slide 94** — a number the mixture model was not
tuned to.

Diluting 1.6% by volume with WLS fibre gives the barrel medium: ρ = 5.7022,
X₀ = 1.6199 cm as measured by `materialScan`.

The liquid is assumed to be sodium **poly**tungstate. Plain Na₂WO₄ saturates
near 1.5 g/cm³, far too light for an 80/20 split at any sensible packing.
Worth confirming with the GRAiNITA group.

### Electrons

    sigma/E = 1.1%/sqrt(E) (+) 0.7%     (deck targets: <2%, <1%)

**Read this carefully.** The stochastic and constant terms are prototype
*measurements* (10k p.e./GeV, 0.6% non-uniformity) fed into the smearing —
the simulation recovers its own inputs. What it genuinely shows is that
**the geometry costs almost nothing**: raw Geant4 resolution is 0.15% and
flat from 1 to 50 GeV, so 25 X₀ at 2.2 m contains electron showers. The
other real output is 0.3% non-linearity from back leakage.

Vary the assumption to get a genuine study:

    python plot_resolution.py --pe-per-gev 4000 ...

### Pions

Not hard-coded. S and C come out of Geant4 with Birks and attenuation
applied in `DRTubesSDAction`, calibration comes from an electron run, and
χ is fitted globally.

---

## Layout

    ECAL    2.200 - 2.605 m     40.5 cm, 25 X0, 2430 modules (81 phi x 30 z)
    coil    2.605 - 3.105 m     EMPTY - space reserved, no material
    HCAL    3.105 - 4.945 m     184 cm, 6.5 lambda, 45 towers x 72 staves

ECAL inner radius follows from the ARC vessel OD of 4.4 m (slide 4). The
z half-lengths and the coil thickness are **invented** and flagged in the
compact files.

The deck's 1.5 mm tube pitch, versus IDEA's 2 mm, drops the absorber
fraction from 68% to 50% and stretches λ from 22.9 to 28.2 cm — so the same
number of interaction lengths needs ~30 cm more depth. Set
`HcalTubeOuterRadius` back to `1.0*mm` to recover IDEA's geometry.

---

## Files

**Geometry**

| file | what |
|---|---|
| `GrainitaModule.xml` / `_geo.cpp` | test module, explicit fibres |
| `EcalBarrelModular.xml` | ECAL barrel, trapezoid modules |
| `GrainitaBarrelModular_geo.cpp` | the modular barrel constructor |
| `GrainitaBarrel.xml` / `_geo.cpp` | monolithic shell, superseded, kept for cross-checks |
| `HcalBarrelTubes.xml` | HCAL, uses k4geo's `DRBarrelTubes` |
| `ALFA_barrel.xml` | both barrels, self-contained |
| `grainita_materials.xml` | ECAL materials only |
| `hcal_materials.xml` | iron absorber |
| `drtubes_materials.xml` | generated, do not hand-edit |

**Running**

| file | what |
|---|---|
| `env.sh` | source at the start of every session |
| `build.sh` | compiles the ECAL plugin |
| `grainita_barrel_steer.py` | ddsim steering; see the warnings inside |
| `run_scan.sh` | energy scan, picks geometry per particle |
| `condor/` | batch submission, start with `validate.sub` |

**Analysis**

| file | what |
|---|---|
| `fit_resolution.py` | electron resolution |
| `plot_resolution.py` | resolution plot |
| `analyse_hadrons.py` | dual-readout hadron analysis |
| `check_geometry.py` | overlaps and material properties |
| `inspect_modules.py` | module shapes and placement matrices |
| `materialScan` | (DD4hep) the quantitative geometry check |

---

## Four traps that cost real time

Each of these fails **silently** — the run completes and produces
plausible-looking numbers.

**1. The energy-deposit filter kills Cherenkov.**
DDSim defaults to `filter.calo = "edep0"`. A detected optical photon
deposits no energy, so every Cherenkov step is discarded and `DRBTCher`
comes out empty while `DRBTScin` fills normally. Dual readout then silently
degrades to single readout.

    SIM.filter.mapDetFilter["HcalBarrelTubes"] = ""

IDEA documents this for SCEPCal but does not apply it to `DRBarrelTubes`.

**2. Sensitivity is assigned by regex, not by XML.**
Every tube component is `sensitive="false"`. Without
`SIM.geometry.regexSensitiveDetector[...] = {"Match": ["DRBT"]}` nothing in
the HCAL is sensitive and no collection appears. Note it *throws* if the
named detector is absent, unlike `mapActions`.

**3. Optical physics is not in FTFP_BERT.**
No `setupCerenkov`, no Cherenkov photons, empty C channel.

**4. The analysis reads the first collection it finds.**
With both barrels present that is `EcalBarrelHits`, so a hadron study can
report the ECAL fraction alone. Always check `getAvailableCollections()` on
a new configuration before trusting a number.

---

## What this does not simulate

* **No coil.** 50 cm of vacuum where a 3 T solenoid and cryostat belong —
  order 1 λ that hadrons would shower in. The largest known omission, and
  the reason pion numbers are an upper bound on performance.
* **No mechanical structure.** `Ecal_gap` is 0, so the barrel is seamless.
  Module walls sit in projective cracks and feed the constant term.
* **No optical transport in the ECAL.** The effective medium has no grains.
  Light collection enters as a parametrisation, which is why the electron
  resolution is partly assumption.
* **No material in front.** No beampipe, tracker or ARC.
* **HCAL is a 90° sector**, θ fixed at 90°, no endcaps.

---

## Next

1. Report the Cherenkov filter issue to the k4geo/IDEA authors — a
   two-event reproducer exists.
2. Get real coil parameters. It sets the HCAL inner radius, the tube count
   and the total detector size.
3. Replace the invented z half-lengths.
4. Derive ECAL light collection from `qwert2333/Grainita_Module` instead of
   assuming 10k p.e./GeV, then let Geant4 count photons via
   `SCINTILLATIONYIELD` rather than applying a flat p.e./GeV.
5. Module walls, then CMS-style mechanical structure.
6. Endcaps — `DREndcapTubes` already exists in k4geo.

Coordinate with `fcc-ped-detectorconcepts-alfa` before going further; much
of this is work the concept group may already be doing.
