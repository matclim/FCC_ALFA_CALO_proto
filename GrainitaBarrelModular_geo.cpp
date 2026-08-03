//==========================================================================
//  GRAiNITA ECAL barrel, built from discrete modules
//--------------------------------------------------------------------------
//
//  Replaces the monolithic shell with a real module tiling: n_phi modules
//  around the azimuth, n_z along the beam, each a trapezoid tapering with
//  radius so the ring closes exactly.
//
//  Why this matters: a monolithic shell has no cracks, so there is nowhere
//  to put walls, alveolar structure or supports. Getting the module
//  geometry right first means the CMS-style mechanical structure can be
//  added later without redoing the readout.
//
//  All modules are geometrically identical, so ONE logical volume is built
//  and placed n_phi*n_z times. Cheap in memory and in navigation.
//
//  Local module frame:
//      local z -> radially outward     (shower depth, fibre direction)
//      local x -> azimuthal            (tapers with radius)
//      local y -> along the beam       (constant)
//
//  Readout: physVolIDs give module (phi), row (z) and layer (depth); a
//  CartesianGridXY on the layer volume gives the 7 mm cells in local x,y.
//
//  UNTESTED — not compiled.
//==========================================================================
 
#include "DD4hep/DetFactoryHelper.h"
#include "DD4hep/Printout.h"
#include "DDRec/DetectorData.h"
 
#include <cmath>
#include <string>
 
using namespace dd4hep;
 
static Ref_t create_modular_barrel(Detector& theDetector, xml_h e, SensitiveDetector sens) {
 
  xml_det_t x_det = e;
  const std::string detName = x_det.nameStr();
  const int         detID   = x_det.id();
 
  DetElement sdet(detName, detID);
  sens.setType("calorimeter");
 
  // ---- dimensions ------------------------------------------------------
  xml_dim_t dim  = x_det.dimensions();
  const double rmin  = dim.rmin();
  const double rmax  = dim.rmax();
  const double zhalf = dim.dz();
  const double depth = rmax - rmin;
 
  // <modules nphi="81" nz="30" gap="0.5*mm"/>
  xml_comp_t x_mod = x_det.child(_Unicode(modules));
  const int    nPhi = x_mod.attr<int>(_Unicode(nphi));
  const int    nZ   = x_mod.attr<int>(_Unicode(nz));
  const double gap  = x_mod.hasAttr(_Unicode(gap)) ? x_mod.attr<double>(_Unicode(gap)) : 0.0;
 
  int nLayers = 1;
  if (x_det.hasChild(_Unicode(layers)))
    nLayers = x_det.child(_Unicode(layers)).attr<int>(_Unicode(number));
  if (nLayers < 1) nLayers = 1;
 
  Material activeMat = theDetector.material(x_det.attr<std::string>(_Unicode(material)));
 
  // ---- module dimensions ----------------------------------------------
  // The module fills its azimuthal wedge exactly, minus the gap.
  const double dphi   = 2.0 * M_PI / nPhi;
  const double halfXi = rmin * std::tan(dphi / 2.0) - gap / 2.0;   // at rmin
  const double halfXo = rmax * std::tan(dphi / 2.0) - gap / 2.0;   // at rmax
  const double halfY  = zhalf / nZ - gap / 2.0;                    // along beam
  const double halfZ  = depth / 2.0;                               // radial
 
  // ---- one module logical volume, reused for every placement ----------
  Trap   modShape(halfZ, 0.0, 0.0,
                  halfY, halfXi, halfXi, 0.0,
                  halfY, halfXo, halfXo, 0.0);
  Volume modVol(detName + "_module", modShape, activeMat);
  modVol.setVisAttributes(theDetector, x_det.visStr());
 
  // radial sub-layers inside the module
  const double layerDepth = depth / nLayers;
  for (int iLayer = 0; iLayer < nLayers; ++iLayer) {
    const double rIn  = rmin + iLayer * layerDepth;
    const double rOut = rIn + layerDepth;
    const double hXi  = rIn  * std::tan(dphi / 2.0) - gap / 2.0;
    const double hXo  = rOut * std::tan(dphi / 2.0) - gap / 2.0;
 
    Trap   layShape(layerDepth / 2.0, 0.0, 0.0,
                    halfY, hXi, hXi, 0.0,
                    halfY, hXo, hXo, 0.0);
    Volume layVol(detName + _toString(iLayer, "_layer%d"), layShape, activeMat);
    layVol.setVisAttributes(theDetector, x_det.visStr());
    layVol.setSensitiveDetector(sens);
 
    // local z runs from -halfZ (rmin) to +halfZ (rmax)
    const double zLocal = -halfZ + (iLayer + 0.5) * layerDepth;
    PlacedVolume lpv = modVol.placeVolume(layVol, Position(0.0, 0.0, zLocal));
    lpv.addPhysVolID("layer", iLayer);
  }
 
  // ---- envelope and placements ----------------------------------------
  // A module's outer face is FLAT, so while its centre sits at rmax its
  // corners reach sqrt(rmax^2 + halfXo^2) -- the same reason a polygon's
  // vertices lie outside its inscribed circle. For 81 modules at 2.6 m that
  // is about 2 mm. The envelope has to allow for it or every module
  // "extrudes" its mother.
  //
  // The inner face needs no such margin: its closest approach to the axis
  // is rmin at the face centre, with the corners further out.
  const double envRmax = std::sqrt(rmax * rmax + halfXo * halfXo) + 0.01 * mm;
 
  Tube   envShape(rmin, envRmax, zhalf);
  Volume envVol(detName + "_envelope", envShape, theDetector.air());
  envVol.setVisAttributes(theDetector, x_det.visStr());
 
  const double rMid = 0.5 * (rmin + rmax);
  int nPlaced = 0;
 
  for (int iPhi = 0; iPhi < nPhi; ++iPhi) {
    const double phi = iPhi * dphi;
    const double cp  = std::cos(phi);
    const double sp  = std::sin(phi);
 
    // Build the rotation from the images of the local axes, rather than
    // from Euler angles -- there is no convention left to get wrong.
    //
    //   local x -> (-sin phi,  cos phi, 0)   azimuthal
    //   local y -> (       0,        0, 1)   along the beam
    //   local z -> ( cos phi,  sin phi, 0)   radial, the shower depth
    //
    // Rotation3D takes the nine matrix elements ROW-wise, so each COLUMN
    // below is the global direction of one local axis. det = +1.
    const Rotation3D rot(-sp, 0.0,  cp,
                          cp, 0.0,  sp,
                         0.0, 1.0, 0.0);
 
    for (int iZ = 0; iZ < nZ; ++iZ) {
      const double zPos = -zhalf + (iZ + 0.5) * (2.0 * zhalf / nZ);
      const Position pos(rMid * std::cos(phi), rMid * std::sin(phi), zPos);
 
      PlacedVolume mpv = envVol.placeVolume(modVol, Transform3D(rot, pos));
      mpv.addPhysVolID("module", iPhi);
      mpv.addPhysVolID("row", iZ);
      ++nPlaced;
    }
  }
 
  printout(INFO, "GrainitaBarrelModular",
           "%d modules (%d phi x %d z), %.2f x %.2f cm at rmin, %.1f cm deep, "
           "%d layer(s), gap %.2f mm",
           nPlaced, nPhi, nZ, 2 * halfXi / cm, 2 * halfY / cm, depth / cm,
           nLayers, gap / mm);
 
  // ---- reconstruction metadata ----------------------------------------
  auto* caloData = new rec::LayeredCalorimeterData;
  caloData->layoutType     = rec::LayeredCalorimeterData::BarrelLayout;
  caloData->inner_symmetry = nPhi;
  caloData->outer_symmetry = nPhi;
  caloData->phi0           = 0.0;
  caloData->extent[0] = rmin;
  caloData->extent[1] = rmax;
  caloData->extent[2] = 0.0;
  caloData->extent[3] = zhalf;
 
  for (int iLayer = 0; iLayer < nLayers; ++iLayer) {
    rec::LayeredCalorimeterData::Layer layer;
    layer.distance                  = rmin + iLayer * layerDepth;
    layer.sensitive_thickness       = layerDepth;
    layer.inner_thickness           = layerDepth / 2.0;
    layer.outer_thickness           = layerDepth / 2.0;
    layer.absorberThickness         = 0.0;
    layer.inner_nRadiationLengths   = layerDepth / (2.0 * activeMat.radLength());
    layer.outer_nRadiationLengths   = layerDepth / (2.0 * activeMat.radLength());
    layer.inner_nInteractionLengths = layerDepth / (2.0 * activeMat.intLength());
    layer.outer_nInteractionLengths = layerDepth / (2.0 * activeMat.intLength());
    caloData->layers.push_back(layer);
  }
  sdet.addExtension<rec::LayeredCalorimeterData>(caloData);
 
  Volume       mother = theDetector.pickMotherVolume(sdet);
  PlacedVolume pv     = mother.placeVolume(envVol);
  pv.addPhysVolID("system", detID);
  sdet.setPlacement(pv);
 
  return sdet;
}
 
DECLARE_DETELEMENT(GrainitaBarrelModular, create_modular_barrel)

