"""
ddsim steering for the GRAiNITA PoC module.

Usage:
    ddsim --steeringFile grainita_steer.py \
          --compactFile GrainitaModule.xml \
          --outputFile grainita_10GeV.root

Override the gun energy from the command line for a resolution scan:
    ddsim --steeringFile grainita_steer.py --compactFile GrainitaModule.xml \
          --gun.energy "5*GeV" --outputFile grainita_5GeV.root
"""

from DDSim.DD4hepSimulation import DD4hepSimulation

SIM = DD4hepSimulation()

SIM.numberOfEvents = 1000
SIM.outputFile = "grainita_sim.root"
SIM.random.enableEventSeed = True
SIM.random.seed = 42

# --- particle gun: photons along +z into the front face ------------------
SIM.enableGun = True
SIM.gun.particle = "gamma"
SIM.gun.energy = "10*GeV"
SIM.gun.direction = (0.0, 0.0, 1.0)
SIM.gun.position = (0.0, 0.0, "-25*cm")
SIM.gun.distribution = "uniform"
SIM.gun.multiplicity = 1

# --- physics -------------------------------------------------------------
# No optical physics: the effective medium carries no optical properties
# and tracking photons here would be both wrong and ruinously slow.
# Light collection is applied at digitisation instead.
SIM.physics.list = "FTFP_BERT"

# Low production cuts: at 7 mm cells with a 2.6 cm Moliere radius the
# transverse profile matters, and the default 0.7 mm range cut is fine,
# but tighten if you start studying the shower core in detail.
SIM.physics.rangecut = 0.1  # mm

# --- output --------------------------------------------------------------
# Keep full hit contributions: needed if you later want timing for the
# pulse-shape-discrimination studies (slide 95).
SIM.part.saveProcesses = ["Decay"]
SIM.part.minimalKineticEnergy = "1*MeV"

SIM.action.calo = "Geant4CalorimeterAction"
