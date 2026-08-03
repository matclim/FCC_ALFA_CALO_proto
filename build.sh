#!/bin/bash
#
# Build the GRAiNITA PoC plugin. Run from the directory containing
# CMakeLists.txt, on a machine with CVMFS (lxplus works):
#
#     source build.sh
#
# Use `source`, not `./build.sh` — the script exports LD_LIBRARY_PATH,
# which has to survive into your shell for DD4hep to find the plugin.
#

# Match the stack the upstream Grainita repo uses.
source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${HERE}/build" "${HERE}/install"
cd "${HERE}/build" || return 1

cmake .. -DCMAKE_INSTALL_PREFIX="${HERE}/install" -Wno-dev || return 1
make install -j8 || return 1

cd "${HERE}" || return 1

# DD4hep finds detector constructors by scanning LD_LIBRARY_PATH.
export LD_LIBRARY_PATH="${HERE}/install/lib:${HERE}/install/lib64:${LD_LIBRARY_PATH}"

echo
echo "Built. Plugin library:"
ls -1 "${HERE}"/install/lib*/libGrainitaPoC* 2>/dev/null
echo
echo "Now try:  geoPluginRun -input GrainitaModule.xml -plugin DD4hep_CheckOverlaps -tolerance 0.0001"
