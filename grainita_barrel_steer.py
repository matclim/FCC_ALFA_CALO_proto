"""
ddsim steering for the ALFA calorimeter barrels.
 
Works for the ECAL alone, the HCAL alone, or both:
 
    ddsim --steeringFile grainita_barrel_steer.py \
          --compactFile EcalBarrelModular.xml \
          --gun.particle e- --gun.energy "10*GeV" \
          --outputFile /tmp/e10.root
 
    ddsim --steeringFile grainita_barrel_steer.py \
          --compactFile ALFA_barrel.xml \
          --gun.particle pi- --gun.energy "20*GeV" \
          --gun.phiMin "40*deg" --gun.phiMax "50*deg" \
          --outputFile /tmp/pi20.root
 
The gun sits at the origin and fires outward, so particles cross 2.2 m of
vacuum before reaching the ECAL.
 
TWO THINGS HERE ARE LOAD-BEARING FOR THE HCAL
=============================================
 
1. THE SENSITIVE ACTION MUST BE MAPPED BY DETECTOR NAME.
 
   DRBarrelTubes_o1_v01.xml declares no <sensitive type="..."/> in its
   detector block, unlike the older fibre implementation. So the action is
   attached from here, keyed on the detector NAME in the compact file.
   IDEA does the same thing (SteeringFile_IDEA_o2_v01.py line 125).
 
   Without it the tubes are built and record NOTHING, and the run completes
   without a single warning. That failure is silent and expensive: the
   output looks fine and the numbers are meaningless.
 
2. SENSITIVITY IS ASSIGNED BY REGEX ON VOLUME NAMES.
 
   Every tube component is sensitive="false" in the compact file. The
   constructor names the fibre volumes DRBT_cher_core, DRBT_cher_clad and
   DRBT_scin_core, and DD4hep is told to make anything matching "DRBT"
   sensitive via SIM.geometry.regexSensitiveDetector. Without that line NO
   volume in the HCAL is sensitive and no collection appears, whatever the
   action mapping says.
 
3. OPTICAL PHYSICS PROBABLY MUST BE ADDED BY HAND.
 
   FTFP_BERT contains no optical processes, so no Cherenkov photons are
   generated at all. DRTubesSDAction counts real optical photons arriving
   at the SiPM for the C channel, so without this the Cherenkov collection
   is empty, the dual-readout correction becomes a no-op, and the reported
   resolution silently equals the scintillation-only one.
 
   The scintillation channel does NOT need optical physics: DRTubesSDAction
   parameterises it from the energy deposit with Birks and attenuation.
 
   NOTE: IDEA's own SteeringFile_IDEA_o2_v01.py does NOT enable optical
   physics -- setupCerenkov appears there only inside a comment block. So
   either their default runs have an empty Cherenkov channel, or photons
   arrive by some route not visible in that file. Worth testing directly:
   run five events with and without setupCerenkov and compare the size of
   DRBTCher. If it is populated either way, drop this and save the CPU.
 
   COST: Cherenkov photon generation and tracking is the dominant CPU term
   for hadron runs. MaxNumPhotonsPerStep caps the per-step burst.
"""
 
from DDSim.DD4hepSimulation import DD4hepSimulation
 
SIM = DD4hepSimulation()
 
SIM.numberOfEvents = 200
SIM.outputFile = "barrel_sim.root"
SIM.random.enableEventSeed = True
SIM.random.seed = 42
 
# --- particle gun ---------------------------------------------------------
SIM.enableGun = True
SIM.gun.particle = "e-"
SIM.gun.energy = "10*GeV"
SIM.gun.multiplicity = 1
SIM.gun.position = (0.0, 0.0, 0.0)
SIM.gun.distribution = "uniform"
SIM.gun.thetaMin = "90*deg"
SIM.gun.thetaMax = "90*deg"
SIM.gun.phiMin = "0*deg"
SIM.gun.phiMax = "360*deg"
 
# --- physics --------------------------------------------------------------
SIM.physics.list = "FTFP_BERT"
SIM.physics.rangecut = 0.1  # mm
 
 
def setupCerenkov(kernel):
    """
    Add Cherenkov generation and optical photon transport.
 
    Needed only for the dual-readout HCAL. Harmless but wasteful for
    ECAL-only runs, since the GRAiNITA effective medium carries no optical
    properties and so produces no photons.
    """
    from DDG4 import PhysicsList
 
    seq = kernel.physicsList()
 
    cerenkov = PhysicsList(kernel, "Geant4CerenkovPhysics/CerenkovPhys")
    cerenkov.MaxNumPhotonsPerStep = 10
    cerenkov.MaxBetaChangePerStep = 10.0
    cerenkov.TrackSecondariesFirst = True
    cerenkov.VerboseLevel = 0
    cerenkov.enableUI()
    seq.adopt(cerenkov)
 
    optical = PhysicsList(kernel, "Geant4OpticalPhotonPhysics/OpticalGammaPhys")
    optical.addParticleConstructor("G4OpticalPhoton")
    optical.VerboseLevel = 0
    optical.enableUI()
    seq.adopt(optical)
 
    return None
 
 
SIM.physics.setupUserPhysics(setupCerenkov)
 
# --- particle handling ----------------------------------------------------
SIM.part.minimalKineticEnergy = "1*MeV"
 
# --- sensitive detectors --------------------------------------------------
# Scintillator-aware default: applies Birks saturation in scintillating
# volumes. IDEA uses the same for its calorimeters.
SIM.action.calo = "Geant4ScintillatorCalorimeterAction"
SIM.action.calorimeterSDTypes = ["calorimeter"]
 
# Keyed on the detector NAME in the compact file. mapActions is pattern
# matching, so naming a detector that is not present is harmless.
SIM.action.mapActions["HcalBarrelTubes"] = "DRTubesSDAction"
 
# ---------------------------------------------------------------------------
# THE LINE THAT MAKES CHERENKOV WORK
# ---------------------------------------------------------------------------
# DDSim applies filter.calo = "edep0" by default: the sensitive action only
# runs for steps with a non-zero energy deposit.
#
# An optical photon DETECTED at a SiPM deposits no energy -- detection is a
# boundary process, not an energy loss. So every Cherenkov step is discarded
# before DRTubesSDAction ever sees it, and DRBTCher comes out EMPTY while
# DRBTScin fills normally (scintillation is driven by charged particles that
# do deposit energy).
#
# The failure is total, not statistical: 6309 p.e. of scintillation against
# exactly 0 Cherenkov in the same 20 GeV event. And it is silent -- the run
# completes, the collection exists, and any dual-readout correction built on
# it becomes a no-op that quietly reports scintillation-only performance.
#
# IDEA documents this exact trap in SteeringFile_IDEA_o2_v01.py, for SCEPCal:
#   "Do not add filter to crystal calorimeter (e.g. edep1kev) otherwise
#    optical photons will not be processed by its SDAction and corresponding
#    collections are empty"
# They clear it for SCEPCal but NOT for DRBarrelTubes, which suggests their
# default configuration has the same problem.
SIM.filter.mapDetFilter["HcalBarrelTubes"] = ""
 
# THE LINE THAT ACTUALLY CREATES THE HITS.
# Tube components are sensitive="false" in XML; sensitivity is assigned by
# matching volume names. DRTubesconstructor names the fibre volumes
# DRBT_cher_core, DRBT_cher_clad and DRBT_scin_core, so "DRBT" catches the
# three that matter. Copied verbatim from IDEA.
# CAREFUL: unlike mapActions, this one LOOKS UP the DetElement by name and
# throws if it is absent:
#     runtime_error: DetElement::child Unknown child with name: ...
# So list only detectors that actually exist in the compact file being run.
# Harmless for ECAL-only runs, because the key is only consulted when the
# named detector is there... no: it is consulted unconditionally. Keep this
# list in sync with your compact files.
SIM.geometry.regexSensitiveDetector["HcalBarrelTubes"] = {
    "Match": ["DRBT"],
    "OutputLevel": 4,
}

