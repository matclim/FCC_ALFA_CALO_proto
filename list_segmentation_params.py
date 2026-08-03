#!/usr/bin/env python3
"""
Print the real XML parameter names a DD4hep segmentation accepts.
 
    python list_segmentation_params.py ProjectiveCylinder
 
Run with no argument to list every segmentation your DD4hep provides.
Use this instead of guessing attribute spellings in compact files.
"""
 
import sys
import ROOT
 
ROOT.gSystem.Load("libDDCore")
ROOT.gErrorIgnoreLevel = ROOT.kWarning
 
if len(sys.argv) < 2:
    import os
    inc = os.path.join(os.environ.get("DD4hepINSTALL", ""), "include", "DDSegmentation")
    print(f"Segmentations available in {inc}:\n")
    try:
        for f in sorted(os.listdir(inc)):
            if f.endswith(".h"):
                print("   ", f[:-2])
    except OSError as exc:
        print("   could not list:", exc)
    print("\nRe-run with one of these names to see its parameters.")
    sys.exit(0)
 
name = sys.argv[1]
 
# Segmentations require a cell-encoding string at construction. The content
# does not matter for listing parameters, only that the fields parse — but
# the total width must stay under 64 bits, so keep it minimal.
encoding = sys.argv[2] if len(sys.argv) > 2 else "system:5,layer:4,theta:11,phi:12"
 
try:
    seg = getattr(ROOT.dd4hep.DDSegmentation, name)(encoding)
except Exception as exc:
    print(f"Could not construct {name} with encoding '{encoding}':\n  {exc}")
    print("\nTry passing an encoding with the fields this segmentation needs, e.g.")
    print(f"    python {sys.argv[0]} {name} 'system:5,theta:11,phi:12'")
    sys.exit(1)
 
print(f"\n{name}  (type name in XML: {seg.type()})")
print(f"  description: {seg.description()}\n")
print(f"{'XML attribute':<24} {'unit':<10} description")
print("-" * 78)
 
 
def _try(obj, *names):
    """Return the first accessor that exists and works, else ''."""
    for n in names:
        fn = getattr(obj, n, None)
        if fn is None:
            continue
        try:
            return str(fn())
        except Exception:
            continue
    return ""
 
 
for par in seg.parameters():
    pname = _try(par, "name")
    unit = _try(par, "unitString", "unit")
    desc = _try(par, "description")
    val = _try(par, "valueString", "value")
    print(f"{pname:<24} {unit:<10} {desc}")
    if val:
        print(f"{'':<24} {'':<10} (default: {val})")
 
print("""
Use the left column verbatim as the attribute name, e.g.
 
    <segmentation type="%s" <attr>="..." <attr>="..."/>
""" % name)

