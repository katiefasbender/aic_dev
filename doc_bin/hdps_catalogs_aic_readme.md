
# hdps.catalogs.aic

This module builds individual collections of the Argus Input Catalog (AIC).  

## Terminology

Any source can be classified along the following three axes:
- apparent size/shape: 
    - **point**: a point source
    - **extended**: an extended object
- apparent magnitude: 
    - **constant**
    - **transient**/**variable**
- on-sky location:
    - "**stationary**": proper motion low enough that the source will probably be in the same minipix for the duration of the survey
    - **moving**: will cross multiple minipix over time (SSOs)

Any minipix can be...
- **active**: image cutouts of that minipix are saved
- **inactive**: image cutouts are not saved

If a science target appears in a minipix, that minipix can be...
- **always-on**: minipix is always active, every image cutout is saved; this case handles "static" sources that we want to save every time they are imaged 
- **toggle**: minipix is only active sometimes, or was active in the past, or was activated after the start of the survey; this case handles solar system objects (SSOs), transient events flagged by the pipeline, and external requests for activation from science team


AIC is divided into the following sub-catalogs:

- **AIC Refcat - Base** 
    - source catalog in HATS format 
    - contains all "static" sources observed by Argus
    - constructed from a combination of existing reference catalogs (for now, ATLAS-Refcat2)
    - used to build **AIC Base**
- **AIC Refcat - SSOs**
    - object catalog
    - contains all SSOs that Argus will observe
    - used to build **AIC SSOs**
- **AIC Base**
    - minipix catalog
    - contains all minipix containing "static" sources observed by Argus (from AIC Refcat)
- **AIC SSOs**
    - minipix catalog
    - predicted detections of solar system objects (SSOs) in Argus images are generated at the beginning of each night of observing; these are the minipix that contain those detections, and the associated timestamps
- **AIC Transients**
    - minipix catalog?
    - transients flagged by the pipeline
- **AIC Requests**
    - handles requested minipix activations from the science team