#!/usr/bin/env python3
"""
Export a STYLED geometry file for interactive viewing in JSROOT.
 
    python export_styled.py EcalBarrelModular.xml
 
Writes <stem>_styled.root. scp it to your laptop and drag it onto
https://root.cern/js/ -- you get full interactivity (rotate, zoom, clipping
sliders, a volume tree with checkboxes) with the styling already applied.
 
Why not just geoConverter? Because that exports the raw geometry with
ROOT's default 20 segments per circle, so every tube renders as a polygon.
This script bakes in the segment count, colours and visibility flags before
writing, so the file looks right the moment it loads.
"""
 
import sys
import ROOT
 
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libDDCore")
ROOT.gErrorIgnoreLevel = ROOT.kError
 
compact = sys.argv[1] if len(sys.argv) > 1 else "EcalBarrelModular.xml"
stem = compact.rsplit(".", 1)[0]
 
det = ROOT.dd4hep.Detector.getInstance()
det.fromXML(compact)
gm = ROOT.gGeoManager
 
# ---- smoothness ---------------------------------------------------------
# The default 20 segments per circle is what makes DD4hep geometries look
# faceted in every viewer. This is stored in the file.
gm.SetNsegments(120)
gm.SetVisLevel(5)
gm.SetVisOption(0)
 
# ---- colours and visibility --------------------------------------------
# All modules share one logical volume, so the two radial layers are what
# carry the visible structure. Keeping the module shell and envelope hidden
# means JSROOT does not have to draw 2430 redundant outer surfaces, which
# also makes it a great deal more responsive.
styled = 0
for i in range(gm.GetListOfVolumes().GetEntries()):
    v = gm.GetListOfVolumes().At(i)
    n = v.GetName()
    if "layer0" in n:
        v.SetLineColor(ROOT.kAzure + 1)
        v.SetFillColor(ROOT.kAzure + 1)
        v.SetTransparency(25)
        v.SetVisibility(True)
        styled += 1
    elif "layer1" in n:
        v.SetLineColor(ROOT.kOrange - 3)
        v.SetFillColor(ROOT.kOrange - 3)
        v.SetTransparency(25)
        v.SetVisibility(True)
        styled += 1
    elif "module" in n:
        v.SetVisibility(False)
    elif "envelope" in n or "world" in n:
        v.SetVisibility(False)
 
print(f"styled {styled} sensitive volumes, {gm.GetListOfVolumes().GetEntries()} total")
 
out = f"{stem}_styled.root"
gm.Export(out)
print(f"\nwrote {out}")
print(f"""
On your laptop:
 
    scp {__import__('os').environ.get('USER','you')}@lxplus940.cern.ch:{__import__('os').getcwd()}/{out} .
 
Then open https://root.cern/js/ and drag the file in.
 
In the JSROOT viewer:
  * the left tree has checkboxes: hide layer1 to see layer0 alone
  * 'Clipping' in the settings menu gives x/y/z sliders - drag z for the
    r-phi view, x for the r-z view
  * click any volume to see its name and dimensions
  * 'Highlight' shows what you hover over
""")

