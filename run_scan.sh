#!/bin/bash
#
# Energy scan for resolution studies, with geometry and gun acceptance
# chosen automatically for the particle type.
#
#     ./run_scan.sh e-        electrons -> ECAL only, full azimuth
#     ./run_scan.sh gamma     photons   -> ECAL only, full azimuth
#     ./run_scan.sh pi-       pions     -> ECAL+HCAL, aimed into the HCAL sector
#     ./run_scan.sh mu-       muons     -> ECAL+HCAL, aimed into the HCAL sector
#
# Overrides (environment variables):
#     NEVT=200 ./run_scan.sh e-              events per point
#     ENERGIES="5 10 50" ./run_scan.sh e-    energy points
#     COMPACT=ALFA_barrel.xml ./run_scan.sh e-   force a geometry
#     OUTDIR=/tmp/mine ./run_scan.sh e-
#
# WHY THE GEOMETRY DIFFERS BY PARTICLE
#
#   Electrons and photons are fully contained in 25 X0 of GRAiNITA, so the
#   ECAL-only geometry is both correct and fast. Building the HCAL tube
#   barrel for them would cost hours and change nothing.
#
#   Pions and muons must see the HCAL. 25 X0 of GRAiNITA is only 1.57
#   interaction lengths: most of a pion shower would leave out the back and
#   any "resolution" measured on the ECAL alone is leakage, not calorimetry.
#
# WHY THE AZIMUTH IS RESTRICTED FOR HADRONS
#
#   ALFA_barrel.xml builds the HCAL over a limited phi range by default
#   (HcalEndCaloPhi, 90 deg out of the box) because a full 360 deg tube
#   barrel is tens of millions of volumes and hours of construction. The
#   ECAL is full azimuth either way.
#
#   So hadrons must be fired INTO the sector that exists. The gun is aimed
#   at its centre with a narrow spread. A hadronic shower spreads about one
#   interaction length laterally, ~25 cm, which at 3.5 m radius is only a
#   few degrees -- so a 90 deg sector leaves ample margin.
#
#   IF YOU CHANGE HcalEndCaloPhi, CHANGE HADRON_PHI_MIN/MAX TO MATCH.
#   Firing into a region where the HCAL was not built gives a silently
#   wrong answer: the hits simply are not there.
 
set -e
 
PARTICLE="${1:-e-}"
 
# ---- geometry and acceptance per particle -------------------------------
case "${PARTICLE}" in
    e-|e+|gamma)
        DEFAULT_COMPACT="EcalBarrelModular.xml"
        PHI_MIN="0*deg";  PHI_MAX="360*deg"
        NEEDS_HCAL=0
        ;;
    pi-|pi+|pi0|kaon-|kaon+|kaon0L|neutron|proton|mu-|mu+)
        DEFAULT_COMPACT="ALFA_barrel.xml"
        # centre of the default 0-90 deg HCAL sector, +-5 deg spread
        PHI_MIN="40*deg"; PHI_MAX="50*deg"
        NEEDS_HCAL=1
        ;;
    *)
        echo "Unknown particle '${PARTICLE}'. Defaulting to the combined"
        echo "geometry and a narrow azimuth. Check this is what you want."
        DEFAULT_COMPACT="ALFA_barrel.xml"
        PHI_MIN="40*deg"; PHI_MAX="50*deg"
        NEEDS_HCAL=1
        ;;
esac
 
COMPACT="${COMPACT:-${DEFAULT_COMPACT}}"
NEVT="${NEVT:-500}"
OUTDIR="${OUTDIR:-/tmp/alfa_scan}"
ENERGIES="${ENERGIES:-1 2 5 10 20 50}"
 
# Theta 90 deg: perpendicular incidence, shortest path, worst containment.
# A pessimistic and reproducible choice. Scan theta separately.
THETA_MIN="${THETA_MIN:-90*deg}"
THETA_MAX="${THETA_MAX:-90*deg}"
 
# ---- sanity checks ------------------------------------------------------
if [ -z "${DD4hepINSTALL}" ]; then
    echo "ERROR: run 'source env.sh' first."
    exit 1
fi
 
if [ ! -f "${COMPACT}" ]; then
    echo "ERROR: ${COMPACT} not found."
    exit 1
fi
 
if [ "${NEEDS_HCAL}" = "1" ]; then
    if ! grep -q "DRBarrelTubes" "${COMPACT}"; then
        echo "ERROR: ${PARTICLE} needs the HCAL, but ${COMPACT} does not"
        echo "       contain a DRBarrelTubes detector."
        echo "       Use ALFA_barrel.xml, or set COMPACT= explicitly if you"
        echo "       really do want an ECAL-only hadron run."
        exit 1
    fi
    SECTOR=$(grep -o 'HcalEndCaloPhi"[^/]*value="[^"]*"' "${COMPACT}" \
             | grep -o 'value="[^"]*"' | cut -d'"' -f2)
    echo "NOTE: HCAL sector in ${COMPACT} ends at ${SECTOR}."
    echo "      Gun aimed at phi ${PHI_MIN} to ${PHI_MAX}. Make sure that"
    echo "      sits inside the sector that was actually built."
    echo
fi
 
mkdir -p "${OUTDIR}"
 
echo "particle : ${PARTICLE}"
echo "geometry : ${COMPACT}"
echo "phi      : ${PHI_MIN} to ${PHI_MAX}"
echo "theta    : ${THETA_MIN} to ${THETA_MAX}"
echo "events   : ${NEVT} per point"
echo "energies : ${ENERGIES}"
echo "output   : ${OUTDIR}"
echo
 
for E in ${ENERGIES}; do
    OUT="${OUTDIR}/${PARTICLE}_${E}GeV.root"
    LOG="${OUTDIR}/${PARTICLE}_${E}GeV.log"
    echo "=== ${E} GeV ==="
    /usr/bin/time -f "    %E elapsed, %M kB peak" \
    ddsim --steeringFile grainita_barrel_steer.py \
          --compactFile "${COMPACT}" \
          --gun.particle "${PARTICLE}" \
          --gun.energy "${E}*GeV" \
          --gun.phiMin "${PHI_MIN}" \
          --gun.phiMax "${PHI_MAX}" \
          --gun.thetaMin "${THETA_MIN}" \
          --gun.thetaMax "${THETA_MAX}" \
          --numberOfEvents "${NEVT}" \
          --outputFile "${OUT}" \
          > "${LOG}" 2>&1 \
      || { echo "    FAILED - see ${LOG}"; continue; }
    echo "    -> ${OUT}"
done
 
echo
echo "Analyse with:"
echo "    python fit_resolution.py ${OUTDIR}/${PARTICLE}_*GeV.root"
echo "    python plot_resolution.py --label '${PARTICLE}' \\"
echo "           --out ${PARTICLE}_resolution.png ${OUTDIR}/${PARTICLE}_*GeV.root"
 
if [ "${NEEDS_HCAL}" = "1" ]; then
    echo
    echo "WARNING for hadrons: fit_resolution.py currently reads only the"
    echo "FIRST hit collection, so it will report the ECAL alone and ignore"
    echo "the HCAL entirely. It also sums scintillation and Cherenkov"
    echo "signals together, which discards the dual-readout information."
    echo "Do not quote a hadronic resolution from it yet."
fi

