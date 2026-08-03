# GRAiNITA ECAL — proof-of-concept Key4hep simulation

A minimal standalone GRAiNITA module in DD4hep, sized to match the
17 x 17 x 40 cm³ demonstrator described on slide 94 of the ALFA deck.

**Status: untested.** The XML is well-formed and the Python compiles, but
nothing here has been run against a real Key4hep stack. Treat it as a
starting draft to argue with, not working code.

---

## Start from the existing implementation, not from this

`qwert2333/DD4hep_Grainita` already contains a GRAiNITA ECAL geometry
(`Grainita_ECAL`), a dedicated sensitive-detector action
(`GrainitaCaloSDAction`), custom segmentations (`detectorSegmentations`),
digitisation (`DigiCalo`), and a `k4Clue` submodule for clustering. It
builds against the Key4hep nightlies and links `simsipm`, so the
digitisation chain already models SiPM response.

That is much further along than anything in this directory. The sensible
first move is:

```bash
git clone git@github.com:qwert2333/DD4hep_Grainita.git
cd DD4hep_Grainita
mkdir build install
source setup.sh          # nightlies -r 2026-07-03 + simsipm + k4_local_repo
cd build && cmake .. -DCMAKE_INSTALL_PREFIX=../install -Wno-dev && make install -j8
cd ../run && ddsim --steeringFile fullsim_steering.py
```

Use this directory for two things only:

1. **The material definitions** (`grainita_materials.xml`), which are
   derived and cross-checked below, and which you should compare against
   whatever the existing repo assumes.
2. **A stripped-down cross-check geometry**, if you want a second
   independent implementation to validate the first against. Two
   independent geometries agreeing on shower containment is a much
   stronger statement than one geometry running without crashing.

The standalone `qwert2333/Grainita_Module` repo is a plain Geant4
application (`main.cc`, `src/`, `include/`, `macro/`) rather than DD4hep.
That is almost certainly the optical-transport study — explicit grains,
optical photons, WLS fibres, validated against the cosmic-bench and SPS
prototype data. Read it before writing any optical code yourself.

---

## The material model, and why it is probably right

GRAiNITA is ~1 mm ZnWO₄ grains in a heavy transparent liquid, 80% / 20%
**by mass**. To turn that into a DD4hep material you need the volume
packing fraction, which follows from the mass split and the two densities:

```
f / (1 - f) = 4 ρ_liq / ρ_ZnWO4
```

With ρ_ZnWO4 = 7.87 and ρ_liq = 2.80 g/cm³ this gives **f = 0.587** — a
plausible random packing fraction for ~1 mm grains, which is the first
sign the numbers hang together.

| quantity | value |
|---|---|
| grain packing fraction | 0.587 |
| effective density | 5.78 g/cm³ |
| effective X₀ | **1.60 cm** |
| effective Molière radius | 2.56 cm |
| effective Z | 51 |

**The cross-check that matters:** 25 X₀ × 1.60 cm = **40.0 cm**, exactly
the depth of the demonstrator that slide 94 describes as "25 X₀ in depth".
The mixture model reproduces a number the deck states independently.

Method validation: the same calculation applied to pure ZnWO₄ gives
X₀ = 1.17 cm and R_M = 1.90 cm, against the deck's quoted 1.2 cm and
1.98 cm. Agreement at the few-percent level, which is what the Tsai
approximation is good for.

A useful thing to notice: ZnWO₄ and the liquid have nearly the same X₀ in
g/cm² (9.17 vs 9.6), because both are tungstate-dominated. So the
effective X₀ *in cm* is set almost entirely by the packing fraction. If
you want to reduce the uncertainty on the geometry, that is the one
number to pin down — not the liquid chemistry.

### One thing to check with the GRAiNITA group

The deck says "sodium tungstate water solution", but plain Na₂WO₄
saturates near 1.5 g/cm³, far too light to give an 80/20 mass split at a
sensible packing fraction. Reaching ~2.8–3.1 g/cm³ needs sodium
**poly**tungstate, Na₆(H₂W₁₂O₄₀) — the standard dense-media heavy liquid.
That is what `grainita_materials.xml` assumes. Worth confirming before
anyone quotes a resolution from this. The sensitivity is mild:

| ρ_liq | f | ρ_eff | X₀ | R_M |
|---|---|---|---|---|
| 2.80 | 0.587 | 5.78 | 1.60 cm | 2.56 cm |
| 3.00 | 0.604 | 5.94 | 1.55 cm | 2.50 cm |
| 3.10 | 0.612 | 6.02 | 1.53 cm | 2.47 cm |

---

## What this PoC does and does not simulate

**Does:** shower development in the correct effective medium, longitudinal
and transverse containment, leakage, the geometric effect of the passive
WLS fibre grid, and cell occupancy at 7 mm pitch.

**Does not:** anything optical. The effective medium has no optical
properties and no grains. Tracking optical photons through it would be
both wrong and impossibly slow.

This split is deliberate, and it is the central design decision. GRAiNITA's
resolution is dominated by photostatistics (~10k p.e./GeV → 1%/√E) and
non-uniformity (~0.6% constant), neither of which lives in the Geant4
geometry. `analyse_grainita.py` therefore applies them as an explicit
per-cell smearing on top of the Geant4 deposit, and reports the raw and
smeared resolutions separately so the two never get confused.

If you skip that step you will get a beautiful sub-percent "resolution"
that is pure Geant4 sampling fluctuation and means nothing.

---

## Files

| file | what it is |
|---|---|
| `grainita_materials.xml` | ZnWO₄, heavy liquid, effective Grainita medium, WLS fibre |
| `GrainitaModule_geo.cpp` | DD4hep constructor: sensitive block + passive fibre grid |
| `GrainitaModule.xml` | compact file, 17×17×40 cm³, 7 mm fibre pitch |
| `grainita_steer.py` | ddsim steering, photon gun |
| `analyse_grainita.py` | sums hits, applies light-collection model, prints resolution |

The readout is a plain `CartesianGridXYZ` with `grid_size_x/y` = fibre
pitch and `grid_size_z` controlling the longitudinal segmentation. No
custom segmentation class is needed, which is the main reason this is
short. `Grainita_seg_z` in the compact file is the knob for the "at least
two sections" question on slide 96 — set it to 40 cm, 20 cm, 10 cm to scan
1, 2, 4 sections.

## Running it

```bash
source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh

# build the constructor into a local plugin library, then:
ddsim --steeringFile grainita_steer.py --compactFile GrainitaModule.xml \
      --gun.energy "10*GeV" --outputFile grainita_10GeV.root

python analyse_grainita.py grainita_*.root
```

First things to look at, in order:

1. **Geometry sanity.** `dd4hep2root` the compact file and view it. Check
   the fibre count is 24×24 = 576 and that nothing overlaps.
2. **Containment.** Raw resolution at 10 GeV should be well under 1%. If
   not, the module is too small, not the medium wrong.
3. **Longitudinal profile.** Shower max should sit near 5–6 X₀ ≈ 8–10 cm
   for 10 GeV photons. This is the check that the material is right.
4. **Then** scan energy 1–50 GeV and fit σ/E = a/√E ⊕ b against the <2% /
   <1% targets.

## Known gaps

- The C++ has not been compiled. Expect small API fixes.
- No box walls, no reflective wrapping, no barrel/endcap geometry — the
  dead-material questions from slide 96 are entirely absent.
- Fibres are perfectly straight, full-depth, and passive. Real light
  collection is 75% into the nearest four fibres (slide 93); that
  position dependence is not modelled here and is exactly what the
  standalone optical study should provide.
- `analyse_grainita.py` smears each cell independently, which ignores the
  fact that neighbouring cells share light through the same fibres.
