cmake_minimum_required(VERSION 3.16)
project(GrainitaPoC LANGUAGES CXX)
 
#-----------------------------------------------------------------------------
# Builds GrainitaModule_geo.cpp into a DD4hep plugin library.
#
# DD4hep discovers plugins by scanning LD_LIBRARY_PATH at runtime, so after
# `make install` you must put install/lib on LD_LIBRARY_PATH (see build.sh).
#-----------------------------------------------------------------------------
 
set(CMAKE_CXX_STANDARD 20 CACHE STRING "")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
 
find_package(DD4hep REQUIRED COMPONENTS DDCore DDRec)
find_package(ROOT  REQUIRED COMPONENTS Core Geom GenVector)
 
include(DD4hep)
dd4hep_set_compiler_flags()
dd4hep_configure_output()
 
dd4hep_add_plugin(GrainitaPoC
  SOURCES GrainitaModule_geo.cpp GrainitaBarrel_geo.cpp GrainitaBarrelModular_geo.cpp
  USES    DD4hep::DDCore DD4hep::DDRec ROOT::Core ROOT::Geom
)
 
install(TARGETS GrainitaPoC
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
 
install(FILES
  GrainitaModule.xml
  GrainitaBarrel.xml
  EcalBarrelModular.xml
  grainita_materials.xml
  DESTINATION compact
)
 

