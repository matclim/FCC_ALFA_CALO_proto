#!/usr/bin/env python3
"""
Extract the <properties> and <materials> blocks from IDEA's
DRBarrelTubes_o1_v01.xml into a standalone file we can include.
 
    python extract_drtubes_materials.py
    python extract_drtubes_materials.py --add-birks
 
Why this is needed: IDEA defines the fibre materials in the same file as
their detector and readout, so including that file directly would also
instantiate IDEA's calorimeter with a clashing detector ID.
 
Why not retype them: the DRBT materials carry refractive indices,
absorption lengths, scintillation spectra, SCINTILLATIONYIELD and the
Birks constant. The Birks value in particular is the fix for the abnormal
hadronic response that ALLEGRO hit -- copy it, do not re-derive it.
 
Re-run this after a k4geo update, in case the values change.
"""
 
import os
import re
import sys
 
DEFAULT = os.path.join(
    os.environ.get("K4GEO", ""),
    "FCCee/IDEA/compact/IDEA_o2_v01/DRBarrelTubes_o1_v01.xml",
)
 
args = sys.argv[1:]
add_birks = "--add-birks" in args
if add_birks:
    args.remove("--add-birks")
 
# Birks saturation constant for polystyrene scintillator. Value taken from
# k4geo's older fibre implementation (DR_Polystyrene in
# FiberDualReadoutCalo_o1_v01.xml), which sets 0.126*mm/MeV.
#
# Only inject this if you have confirmed that DRTubesSDAction does NOT
# already apply Birks saturation in code. Applying it twice is as wrong as
# not applying it at all.
BIRKS = '      <constant name="BirksConstant" value="0.126*mm/MeV"/>\n'
 
src = args[0] if args else DEFAULT
out = "drtubes_materials.xml"
 
if not os.path.isfile(src):
    sys.exit(f"source not found: {src}\nPass the path explicitly, or set K4GEO.")
 
text = open(src).read()
 
 
def block(tag):
    m = re.search(rf"<{tag}>.*?</{tag}>", text, re.S)
    if not m:
        sys.exit(f"no <{tag}> block found in {src}")
    return m.group(0)
 
 
props = block("properties")
mats = block("materials")
 
n_matrix = props.count("<matrix ")
n_mat = mats.count("<material ")
print(f"extracted {n_matrix} property matrices and {n_mat} materials")
 
for needed in ("DRBTDR_Polystyrene", "DRBTPMMA_Scin", "DRBTFluorinated_Polymer", "DRBTPMMA"):
    print(f"  {needed:28s} {'found' if needed in mats else 'MISSING'}")
 
if "BirksConstant" in mats:
    m = re.search(r'BirksConstant"\s+value="([^"]+)"', mats)
    print(f"  Birks constant: {m.group(1) if m else 'present'}")
elif add_birks:
    # insert just before the closing tag of the scintillating core material
    pat = re.compile(r'(<material name="DRBTDR_Polystyrene"\s*>.*?)(\s*</material>)', re.S)
    mats, n = pat.subn(r"\1\n" + BIRKS + r"\2", mats, count=1)
    if n:
        print("  Birks constant: INJECTED 0.126*mm/MeV into DRBTDR_Polystyrene")
        print("    (only correct if DRTubesSDAction does not apply Birks itself)")
    else:
        print("  WARNING: --add-birks given but DRBTDR_Polystyrene not matched")
else:
    print("  WARNING: no Birks constant in the tubes materials.")
    print("    Check whether DRTubesSDAction applies Birks saturation in code:")
    print("      grep -rn -i birks k4geo/plugins/DRTubesSDAction.cpp")
    print("    If it does not, re-run with --add-birks. Without Birks the")
    print("    scintillation response to dense hadronic showers is too high.")
 
with open(out, "w") as fh:
    fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fh.write("<lccdd>\n\n")
    fh.write(f"  <!-- Extracted verbatim from {src}\n")
    fh.write("       by extract_drtubes_materials.py. Do not hand-edit;\n")
    fh.write("       re-run the script instead. -->\n\n")
    fh.write(props)
    fh.write("\n\n")
    fh.write(mats)
    fh.write("\n\n</lccdd>\n")
 
print(f"\nwrote {out}")

