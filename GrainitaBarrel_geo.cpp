//==========================================================================
//  GRAiNITA ECAL barrel — DD4hep constructor
//--------------------------------------------------------------------------
//
//  A cylindrical shell of the effective GRAiNITA medium, divided into a
//  configurable number of concentric radial layers.
//
//  Design choices, and why:
//
//  * NO explicit fibres. In the test module 625 tubes are fine; a barrel
//    would need several million and Geant4 navigation would crawl. The
//    fibre grid is folded into the material instead (GrainitaBarrelMix).
//
//  * Radial layers are real placed volumes carrying a "layer" physVolID.
//    In GRAiNITA the fibres run along the shower depth, i.e. RADIALLY in a
//    barrel, so longitudinal segmentation cannot simply be a slice of the
//    medium -- it needs split fibres, double-ended readout, or timing.
//    Modelling it as radial layers is the optimistic case: it tells you
//    what longitudinal segmentation would BUY, which is the question
//    slide 96 asks. It does not tell you whether it is achievable.
//
//  * Transverse segmentation is left to the readout (ProjectiveCylinder),
//    so cell size is a compact-file parameter and costs no volumes.
//
//  UNTESTED — not compiled. Expect to fix small things.
//==========================================================================

#include "DD4hep/DetFactoryHelper.h"
#include "DD4hep/Printout.h"
#include "DDRec/DetectorData.h"

#include <cmath>
#include <string>

using namespace dd4hep;

static Ref_t create_barrel(Detector& theDetector, xml_h e, SensitiveDetector sens) {

  xml_det_t x_det = e;
  const std::string detName = x_det.nameStr();
  const int         detID   = x_det.id();

  DetElement sdet(detName, detID);
  sens.setType("calorimeter");

  // ---- dimensions ------------------------------------------------------
  // <dimensions rmin="..." rmax="..." dz="..."/>   dz = HALF length
  xml_dim_t dim = x_det.dimensions();
  const double rmin = dim.rmin();
  const double rmax = dim.rmax();
  const double dz   = dim.dz();

  // <layers number="2"/>
  int nLayers = 1;
  if (x_det.hasChild(_Unicode(layers))) {
    xml_comp_t x_lay = x_det.child(_Unicode(layers));
    nLayers = x_lay.attr<int>(_Unicode(number));
  }
  if (nLayers < 1) nLayers = 1;

  Material activeMat = theDetector.material(x_det.attr<std::string>(_Unicode(material)));
  Material envMat    = theDetector.air();

  // ---- envelope --------------------------------------------------------
  Tube   envShape(rmin, rmax, dz);
  Volume envVol(detName + "_envelope", envShape, envMat);
  envVol.setVisAttributes(theDetector, x_det.visStr());

  // ---- radial layers ---------------------------------------------------
  const double layerThickness = (rmax - rmin) / nLayers;

  for (int iLayer = 0; iLayer < nLayers; ++iLayer) {
    const double r0 = rmin + iLayer * layerThickness;
    const double r1 = r0 + layerThickness;

    Tube   layerShape(r0, r1, dz);
    Volume layerVol(detName + _toString(iLayer, "_layer%d"), layerShape, activeMat);
    layerVol.setVisAttributes(theDetector, x_det.visStr());
    layerVol.setSensitiveDetector(sens);

    PlacedVolume lpv = envVol.placeVolume(layerVol);
    lpv.addPhysVolID("layer", iLayer);

    DetElement layerDE(sdet, _toString(iLayer, "layer%d"), iLayer);
    layerDE.setPlacement(lpv);
  }

  printout(INFO, "GrainitaBarrel",
           "rmin=%.1f mm rmax=%.1f mm dz=%.1f mm, %d radial layer(s) of %.2f mm",
           rmin / mm, rmax / mm, dz / mm, nLayers, layerThickness / mm);

  // ---- reconstruction metadata ----------------------------------------
  // k4RecCalorimeter clustering needs this. If it causes compile trouble,
  // it can be deleted without affecting the simulation itself.
  auto* caloData = new rec::LayeredCalorimeterData;
  caloData->layoutType = rec::LayeredCalorimeterData::BarrelLayout;
  caloData->inner_symmetry = 0;   // 0 = cylindrical
  caloData->outer_symmetry = 0;
  caloData->phi0 = 0.0;
  caloData->extent[0] = rmin;
  caloData->extent[1] = rmax;
  caloData->extent[2] = 0.0;
  caloData->extent[3] = dz;

  for (int iLayer = 0; iLayer < nLayers; ++iLayer) {
    rec::LayeredCalorimeterData::Layer layer;
    layer.distance                  = rmin + iLayer * layerThickness;
    layer.sensitive_thickness       = layerThickness;
    layer.inner_thickness           = layerThickness / 2.0;
    layer.outer_thickness           = layerThickness / 2.0;
    layer.absorberThickness         = 0.0;   // homogeneous, no absorber
    layer.inner_nRadiationLengths   = layerThickness / (2.0 * activeMat.radLength());
    layer.outer_nRadiationLengths   = layerThickness / (2.0 * activeMat.radLength());
    layer.inner_nInteractionLengths = layerThickness / (2.0 * activeMat.intLength());
    layer.outer_nInteractionLengths = layerThickness / (2.0 * activeMat.intLength());
    caloData->layers.push_back(layer);
  }
  sdet.addExtension<rec::LayeredCalorimeterData>(caloData);

  // ---- place -----------------------------------------------------------
  Volume       mother = theDetector.pickMotherVolume(sdet);
  PlacedVolume pv     = mother.placeVolume(envVol);
  pv.addPhysVolID("system", detID);
  sdet.setPlacement(pv);

  return sdet;
}

DECLARE_DETELEMENT(GrainitaBarrel, create_barrel)

// Same implementation under a neutral name: a homogeneous cylindrical
// calorimeter shell with radial layers, fully parametrised by material and
// dimensions. Used for the HCAL barrel, which needs no new code — only a
// different material and radii.
DECLARE_DETELEMENT(SimpleTubeCalorimeter, create_barrel)
