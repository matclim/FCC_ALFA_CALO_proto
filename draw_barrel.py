#!/usr/bin/env python3
"""
Nicer rendering of the GRAiNITA barrel.
 
    python draw_barrel.py EcalBarrelModular.xml              # interactive OpenGL
    python draw_barrel.py EcalBarrelModular.xml --png        # headless image
    python draw_barrel.py EcalBarrelModular.xml --png --cut  # cutaway
    python draw_barrel.py EcalBarrelModular.xml --png --flat # no raytrace
 
--png needs no display, so it works over plain ssh.
If the raytraced image comes out blank, try --flat: raytracing is fussy and
the plain painter always works.
"""
 
import sys
from array import array
 
import ROOT
 
ROOT.gSystem.Load("libDDCore")
ROOT.gErrorIgnoreLevel = ROOT.kError
 
args = sys.argv[1:]
want_png = "--png" in args
want_cut = "--cut" in args
want_flat = "--flat" in args
compact = next((a for a in args if a.endswith(".xml")), "EcalBarrelModular.xml")
 
if want_png:
    ROOT.gROOT.SetBatch(True)
 
det = ROOT.dd4hep.Detector.getInstance()
det.fromXML(compact)
gm = ROOT.gGeoManager
 
# ---- polish -------------------------------------------------------------
# Default is 20 segments per circle, so every tube looks like a polygon.
# This is the single biggest visual improvement.
gm.SetNsegments(120)
gm.SetVisLevel(4)
gm.SetVisOption(0)          # 0 = draw leaf volumes
 
# ---- colours ------------------------------------------------------------
# All 2430 modules share ONE logical volume, so colouring it colours every
# placement. Per-module colour would need distinct volumes in the
# constructor. The two radial layers are what carry the structure here.
for i in range(gm.GetListOfVolumes().GetEntries()):
    v = gm.GetListOfVolumes().At(i)
    n = v.GetName()
    if "layer0" in n:
        v.SetLineColor(ROOT.kAzure + 1); v.SetFillColor(ROOT.kAzure + 1)
        v.SetTransparency(30); v.SetVisibility(True)
    elif "layer1" in n:
        v.SetLineColor(ROOT.kOrange - 3); v.SetFillColor(ROOT.kOrange - 3)
        v.SetTransparency(30); v.SetVisibility(True)
    elif "module" in n:
        v.SetVisibility(False)          # shell only; its layers are drawn
    elif "envelope" in n or "world" in n:
        v.SetVisibility(False)
 
# ---- cutaway ------------------------------------------------------------
# SetClippingShape KEEPS what is inside the shape, so the box must be
# OFF-CENTRE to remove a quadrant. A box centred on the origin clips nothing.
clipbox = None
if want_cut:
    origin = array("d", [-250.0, -250.0, 0.0])
    clipbox = ROOT.TGeoBBox("clipbox", 400.0, 400.0, 400.0, origin)
    gm.SetClippingShape(clipbox)
 
# ---- draw ---------------------------------------------------------------
top = gm.GetTopVolume()
 
if want_png:
    c = ROOT.TCanvas("c", "GRAiNITA barrel", 1600, 1200)
    c.SetFillColor(ROOT.kWhite)
 
    top.Draw()                       # draw the TOP volume, not a hidden one
 
    view = ROOT.gPad.GetView()
    if view:
        view.SetPerspective()
        view.RotateView(65.0, 30.0)  # theta, phi in degrees
    ROOT.gPad.Modified()
    ROOT.gPad.Update()
 
    if not want_flat:
        top.Raytrace()               # software; shadows and depth, no display
        ROOT.gPad.Modified()
        ROOT.gPad.Update()
 
    suffix = "_cut" if want_cut else ""
    suffix += "_flat" if want_flat else ""
    out = compact.replace(".xml", f"{suffix}.png")
    c.SaveAs(out)
    print(f"\nwrote {out}")
    print("If it is blank, re-run with --flat to skip raytracing.")
 
else:
    top.Draw("ogl")
    print("""
OpenGL viewer open. Worth doing inside it:
 
  * View > Ray trace         shadows, much better depth
  * 'Clipping' tab           Box or Plane, drag to cut the barrel open
  * 'Guides' tab             turn the axes off once framed
  * Camera > Orthographic    clean r-phi / r-z projections
  * Ctrl+P                   save a vector PDF
""")
    if not ROOT.gROOT.IsBatch():
        ROOT.gApplication.Run()

