#!/usr/bin/env python3
"""
Dump the actual shape parameters and placement matrix of the first few
modules, so we can see what the geometry really is rather than what the
constructor was supposed to produce.
 
    python inspect_modules.py EcalBarrelModular.xml
"""
 
import sys
import math
from array import array
 
import ROOT
 
ROOT.gSystem.Load("libDDCore")
ROOT.gErrorIgnoreLevel = ROOT.kError
 
compact = sys.argv[1] if len(sys.argv) > 1 else "EcalBarrelModular.xml"
det = ROOT.dd4hep.Detector.getInstance()
det.fromXML(compact)
gm = ROOT.gGeoManager
 
top = gm.GetTopVolume()
env = None
for i in range(top.GetNdaughters()):
    v = top.GetNode(i).GetVolume()
    if "envelope" in v.GetName():
        env = v
        break
if env is None:
    sys.exit("no envelope volume found")
 
print(f"envelope: {env.GetName()}, {env.GetNdaughters()} daughters")
 
# ---- shape of the shared module logical volume --------------------------
shape = env.GetNode(0).GetVolume().GetShape()
print(f"\nmodule shape class: {shape.ClassName()}")
if shape.ClassName() == "TGeoTrap":
    print(f"  Dz   = {shape.GetDz():8.3f} cm   <- should be half the RADIAL depth")
    print(f"  H1   = {shape.GetH1():8.3f} cm   H2  = {shape.GetH2():8.3f} cm   (half-y)")
    print(f"  Bl1  = {shape.GetBl1():8.3f} cm   Tl1 = {shape.GetTl1():8.3f} cm  (half-x at -Dz)")
    print(f"  Bl2  = {shape.GetBl2():8.3f} cm   Tl2 = {shape.GetTl2():8.3f} cm  (half-x at +Dz)")
    print(f"  Theta= {shape.GetTheta():8.3f}    Phi = {shape.GetPhi():8.3f}")
 
# ---- where the first few modules actually sit ---------------------------
print("\nplacements (global):")
print(f"{'node':<28} {'x':>9} {'y':>9} {'z':>9} {'r':>9} {'phi[deg]':>9}")
for i in list(range(3)) + [30, 31, 60]:
    if i >= env.GetNdaughters():
        continue
    node = env.GetNode(i)
    t = node.GetMatrix().GetTranslation()
    x, y, z = t[0], t[1], t[2]
    r = math.hypot(x, y)
    phi = math.degrees(math.atan2(y, x))
    print(f"{node.GetName():<28} {x:9.3f} {y:9.3f} {z:9.3f} {r:9.3f} {phi:9.3f}")
 
# ---- what does the local z axis map to? ---------------------------------
print("\nlocal axis directions for module 0 (the critical check):")
node0 = env.GetNode(0)
m = node0.GetMatrix()
for name, local in (("local x", (1.0, 0.0, 0.0)),
                    ("local y", (0.0, 1.0, 0.0)),
                    ("local z", (0.0, 0.0, 1.0))):
    lv = array("d", local)
    g = array("d", [0.0, 0.0, 0.0])
    m.LocalToMasterVect(lv, g)
    print(f"  {name} -> ({g[0]:6.3f}, {g[1]:6.3f}, {g[2]:6.3f})")
 
print("""
Expected for a correct barrel module at phi=0:
    local x -> ( 0,  1,  0)   azimuthal
    local y -> ( 0,  0,  1)   along the beam
    local z -> ( 1,  0,  0)   radial, the shower depth
 
If local z does NOT come out radial, the rotation is wrong and that is the
whole bug: the 40.5 cm depth is pointing sideways, which both shortens the
radial path and makes neighbouring modules collide.
""")
 
# ---- global bounding box of module 0 ------------------------------------
bb = env.GetNode(0).GetVolume().GetShape()
print(f"module local bounding box half-lengths: "
      f"dx={bb.GetDX():.3f} dy={bb.GetDY():.3f} dz={bb.GetDZ():.3f} cm")

