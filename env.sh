#!/bin/bash
#
# Set up the environment for an ALREADY BUILT GRAiNITA PoC.
#
#     source env.sh
#
# Use this at the start of every new shell / login. It does not compile
# anything -- if you have changed GrainitaModule_geo.cpp, use build.sh instead.
#
# The symptom this fixes:
#     No factory with name Create(GrainitaModule) for type GrainitaModule found
# which means LD_LIBRARY_PATH does not include the install directory. DD4hep
# discovers detector constructors by scanning LD_LIBRARY_PATH at runtime, so
# the plugin is invisible without it.
 
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
 
# ---- Key4hep -------------------------------------------------------------
if [ -z "${DD4hepINSTALL}" ]; then
    for candidate in \
        /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh \
        /cvmfs/sw.hsf.org/key4hep/setup.sh
    do
        if [ -f "${candidate}" ]; then
            echo "Sourcing ${candidate}"
            source "${candidate}"
            break
        fi
    done
fi
 
if [ -z "${DD4hepINSTALL}" ]; then
    echo "ERROR: no Key4hep stack found. See SETUP.md."
    return 1
fi
 
# ---- the PoC plugin ------------------------------------------------------
if [ ! -e "${HERE}/install/lib64/libGrainitaPoC.so" ] && \
   [ ! -e "${HERE}/install/lib/libGrainitaPoC.so" ]; then
    echo "ERROR: libGrainitaPoC.so not found under ${HERE}/install."
    echo "       Run 'source build.sh' first."
    return 1
fi
 
export LD_LIBRARY_PATH="${HERE}/install/lib64:${HERE}/install/lib:${LD_LIBRARY_PATH}"
 
# ---- k4geo source, for reading the DR tube constructor and SD action ----
# The compact files come from CVMFS via $K4GEO, but the C++ is not
# installed, so a clone is needed to read it. Adjust if yours is elsewhere.
for candidate in "${HOME}/private/k4geo" "${HERE}/k4geo" "${HOME}/k4geo"; do
    if [ -d "${candidate}/plugins" ]; then
        export K4SRC="${candidate}"
        break
    fi
done
 
echo "GRAiNITA PoC environment ready."
echo "  plugin  : ${HERE}/install/lib64/libGrainitaPoC.so"
echo "  k4geo   : ${K4GEO:-not set}"
echo "  k4geo src: ${K4SRC:-not found - clone it if you need the C++}"
echo ""
echo "Geometries:"
echo "  EcalBarrelModular.xml   GRAiNITA ECAL barrel, 2430 modules"
echo "  HcalBarrelTubes.xml     DR tube HCAL barrel"
echo "  ALFA_barrel.xml         both, HCAL sector only by default"
echo "  GrainitaModule.xml      17x17x40 cm3 test module"
echo ""
echo "Quick checks:"
echo "  materialScan EcalBarrelModular.xml 0 0 8.33 300 0 8.33"
echo "  python check_geometry.py EcalBarrelModular.xml"
echo "  ./run_scan.sh e-"
 

