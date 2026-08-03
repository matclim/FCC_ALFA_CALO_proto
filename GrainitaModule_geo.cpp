//==========================================================================
//  GRAiNITA module — minimal DD4hep constructor for a proof-of-concept
//--------------------------------------------------------------------------
//
//  A rectangular block of the effective GRAiNITA medium (sensitive),
//  penetrated along z by a square grid of passive WLS fibres.
//
//  Deliberately minimal:
//    * no optical physics — the block is a homogeneous effective medium
//    * fibres are passive; they displace active medium and create the
//      geometric non-uniformity, nothing more
//    * readout is a plain CartesianGridXYZ, so NO custom segmentation
//      class is needed. grid_size_x/y should match the fibre pitch;
//      grid_size_z sets the number of longitudinal sections.
//
//  Geometry matches the 17 x 17 x 40 cm3 demonstrator described on
//  slide 94 of the ALFA deck, so the output can be compared against
//  the module currently under construction.
//
//  UNTESTED — this has not been compiled. Expect to fix small things.
//==========================================================================

#include "DD4hep/DetFactoryHelper.h"
#include "DD4hep/Printout.h"

#include <cmath>
#include <string>

using namespace dd4hep;

static Ref_t create_element(Detector& theDetector, xml_h e, SensitiveDetector sens) {

  xml_det_t x_det = e;
  const std::string detName = x_det.nameStr();
  DetElement sdet(detName, x_det.id());

  sens.setType("calorimeter");

  // ---- envelope dimensions (full sizes) --------------------------------
  xml_dim_t dim = x_det.dimensions();
  const double sizeX = dim.x();
  const double sizeY = dim.y();
  const double sizeZ = dim.z();

  Material activeMat = theDetector.material(x_det.attr<std::string>(_Unicode(material)));

  Box    envShape(sizeX / 2.0, sizeY / 2.0, sizeZ / 2.0);
  Volume envVol(detName + "_active", envShape, activeMat);
  envVol.setVisAttributes(theDetector, x_det.visStr());
  envVol.setSensitiveDetector(sens);

  // ---- WLS fibre grid --------------------------------------------------
  // <fibres pitch="7*mm" radius="0.5*mm" material="WLSFibreCore" vis="..."/>
  int nFibresPlaced = 0;
  if (x_det.hasChild(_Unicode(fibres))) {
    xml_comp_t x_fib = x_det.child(_Unicode(fibres));
    const double pitch  = x_fib.attr<double>(_Unicode(pitch));
    const double radius = x_fib.attr<double>(_Unicode(radius));
    Material fibMat = theDetector.material(x_fib.attr<std::string>(_Unicode(material)));

    Tube   fibShape(0.0, radius, sizeZ / 2.0);
    Volume fibVol(detName + "_fibre", fibShape, fibMat);
    fibVol.setVisAttributes(theDetector, x_fib.visStr());
    // NOT sensitive: energy deposited in the fibre is lost.

    // Centred grid: fibre at (0,0), extending symmetrically outwards.
    const int nHalfX = static_cast<int>(std::floor((sizeX / 2.0 - radius) / pitch));
    const int nHalfY = static_cast<int>(std::floor((sizeY / 2.0 - radius) / pitch));

    for (int ix = -nHalfX; ix <= nHalfX; ++ix) {
      for (int iy = -nHalfY; iy <= nHalfY; ++iy) {
        const double px = ix * pitch;
        const double py = iy * pitch;
        // No addPhysVolID here: the fibre is not sensitive, and any
        // physVolID must appear in the readout <id> descriptor or DD4hep
        // aborts when it encodes a cellID.
        envVol.placeVolume(fibVol, Position(px, py, 0.0));
        ++nFibresPlaced;
      }
    }
    printout(INFO, "GrainitaModule",
             "placed %d WLS fibres, pitch %.2f mm, radius %.2f mm",
             nFibresPlaced, pitch / mm, radius / mm);
  }

  // ---- place the module ------------------------------------------------
  const double zOffset = x_det.hasAttr(_Unicode(z_offset)) ? x_det.attr<double>(_Unicode(z_offset)) : 0.0;

  Volume       mother = theDetector.pickMotherVolume(sdet);
  PlacedVolume pv     = mother.placeVolume(envVol, Position(0.0, 0.0, zOffset));
  pv.addPhysVolID("system", x_det.id());
  sdet.setPlacement(pv);

  return sdet;
}

DECLARE_DETELEMENT(GrainitaModule, create_element)
