#!/bin/bash
#
# Export a DD4hep geometry to formats you can view on your laptop, avoiding
# X11 forwarding from lxplus entirely.
#
#     ./export_geometry.sh EcalBarrelModular.xml
#     ./export_geometry.sh GrainitaModule.xml
#
# Defaults to EcalBarrelModular.xml. The output is named after the compact
# file, so exporting several geometries does not overwrite anything.
#
# Requires the environment to be set up first:  source env.sh
 
set -e
 
COMPACT="${1:-EcalBarrelModular.xml}"
STEM="$(basename "${COMPACT}" .xml)"
 
if [ ! -f "${COMPACT}" ]; then
    echo "ERROR: ${COMPACT} not found."
    exit 1
fi
 
if [ -z "${DD4hepINSTALL}" ]; then
    echo "ERROR: Key4hep not set up. Run 'source env.sh' first."
    exit 1
fi
 
# The flag is -compact2tgeo, NOT -compact2root.
# -volmgr must come BEFORE -output, or the output plugin swallows it as part
# of the filename. It populates the volume manager and checks for duplicate
# volume IDs on the way through.
echo "=== ROOT: view in JSROOT, nothing to install ==="
geoConverter -compact2tgeo -input "${COMPACT}" -volmgr -output "${STEM}_geom.root"
echo "    -> ${STEM}_geom.root"
 
echo
echo "=== GDML: for FreeCAD, standalone Geant4, CAD exchange ==="
geoConverter -compact2gdml -input "${COMPACT}" -output "${STEM}_geom.gdml" \
    && echo "    -> ${STEM}_geom.gdml" \
    || echo "    (gdml export failed - not critical, the ROOT file is the useful one)"
 
echo
echo "----------------------------------------------------------------"
echo "On your laptop:"
echo
echo "    scp ${USER}@$(hostname -s).cern.ch:$(pwd)/${STEM}_geom.root ."
echo
echo "Then open  https://root.cern/js/  and drag the file in."
echo
echo "In the viewer:"
echo "  * clip on z  -> r-phi view: check the 81 wedges close the ring"
echo "  * clip on x  -> r-z view:   check the 30 rows and 2 radial layers"
echo "  * drop the opacity, or the outer modules hide everything inside"
echo "----------------------------------------------------------------"
 

