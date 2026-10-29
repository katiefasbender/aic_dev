# hdps_catalogs

A package with functionality to build the Argus Input Catalog (AIC), which is a catalog of minipix that contain pre-selected science targets (sources for which we want to save observations at full cadence).

Sky tiling scheme functinality is handled by `hdps_skymap` (see documentation for overview of minipix and sky tiling).  `hdps-archive` handles minipix activation.  `hdps_catalogs` maintains a catalog of active minipix, updating on a nightly basis from several sources (see below).  


## Modules

- **[`aic/`](src/hdps/catalogs/aic/README.md)** — builds AIC collections (including AIC Refcat, AIC Base, AIC SSOs).  See the [module README](src/hdps/catalogs/aic/README.md) for guidance on building each collection.
- **[`movers/`](src/hdps/catalogs/movers/README.md)** — solar-system object (asteroid / comet) association: the nightly ephemeris service that generates predicted moving-object detections (feeds **AIC SSOs**) and a per-image finder that annotates images with the movers in their FoV. See the [module README](src/hdps/catalogs/movers/README.md) for usage.