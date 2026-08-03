#!/usr/bin/env python3
"""
Geometry and material sanity checks for the GRAiNITA PoC.
 
Does what DD4hep_CheckOverlaps was supposed to do, plus dumps the material
properties, which are the numbers the whole PoC rests on.
 
    python check_geometry.py GrainitaModule.xml
"""
 
import sys
import ROOT
 
ROOT.gSystem.Load("libDDCore")
ROOT.gErrorIgnoreLevel = ROOT.kWarning
 
compact = sys.argv[1] if len(sys.argv) > 1 else "GrainitaModule.xml"
 
det = ROOT.dd4hep.Detector.getInstance()
det.fromXML(compact)
 
# ---------------------------------------------------------------- materials
print("\n=== materials ===")
print(f"{'name':<22} {'rho [g/cm3]':>12} {'X0':>10} {'lambda_I':>10}")
 
for name, expect_rho, expect_x0 in [
    ("ZnWO4",               7.87, 1.17),
    ("GrainitaHeavyLiquid", 2.80, 3.42),
    ("Grainita",            5.78, 1.60),
    ("WLSFibreCore",        1.05, None),
]:
    try:
        m = det.material(name)
        # DD4hep/TGeo report lengths in cm for TGeoMaterial, but dd4hep::Material
        # wraps them in dd4hep units. Print raw; compare by ratio, not absolute.
        print(f"{name:<22} {m.density():>12.4f} {m.radLength():>10.4f} {m.intLength():>10.4f}"
              f"   (expect rho={expect_rho}"
              + (f", X0~{expect_x0} cm)" if expect_x0 else ")"))
    except Exception as exc:
        print(f"{name:<22}  FAILED: {exc}")
 
print("""
NOTE ON UNITS: DD4hep's internal length unit is cm for TGeo-backed materials
but the Python binding may report in mm. Do not panic if X0 comes back as
16.0 rather than 1.60 -- check the ratio against ZnWO4 (should be ~1.37)
rather than the absolute value.
 
THE CHECK THAT MATTERS: Grainita density must be 5.78 g/cm3 and its X0 must
be ~1.37x that of pure ZnWO4. If either is off, the mixture is being
interpreted differently than intended and every downstream number is wrong.
""")
 
# ---------------------------------------------------------------- overlaps
print("=== overlap check (tolerance 1 um) ===")
gm = ROOT.gGeoManager
gm.CheckOverlaps(0.0001)
overlaps = gm.GetListOfOverlaps()
n = overlaps.GetEntries()
if n == 0:
    print("No overlaps found.")
else:
    print(f"{n} overlap(s) found:")
    gm.PrintOverlaps()
    print("""
If these are fibres against the module boundary, the fix is in
GrainitaModule_geo.cpp: reduce nHalfX / nHalfY by one.""")
 
# ---------------------------------------------------------------- counts
print("\n=== volume counts ===")
top = gm.GetTopVolume()
print(f"top volume: {top.GetName()}")
for node_idx in range(top.GetNdaughters()):
    node = top.GetNode(node_idx)
    vol = node.GetVolume()
    print(f"  {vol.GetName():<28} daughters = {vol.GetNdaughters()}")
    print(f"  {'':28} material  = {vol.GetMaterial().GetName()}")

