Argus Input Catalog
===================

Build and load the collections of the Argus Input Catalog (AIC). 

Argus Input Catalog
-------------------

The Argus Input Catalog (AIC) contains all pre-selected, "high-cadence" science targets for which to save single-epoch image data at the 1 minute & 1 second cadences.
`hdps.catalogs` contains the general functionality to (a) build reference catalogs of science targets, and (b) select unique minipix containing the science targets.  
Minipix activation is handled by `hdps.skymap`.


Background
~~~~~~~~~~
**Minipix and Sky Tiling**
The sky is divided into "tiles", each with a unique ID.
Each tile is divided into 4096 "minipix", each with a local index.  
See `hdps/docs/source/components/skymap/explanation/sky-tiling.rst` for sky tiling and minipix definitions.

Coaddition is performed at the tile-level; coadded image segments are saved at the 15-minute cadence, and by nature all sources down to the 15-min limiting magnitude are saved at 15-minute cadence.
Single-epoch image cutouts of "active" minipix are saved only for pre-selected science targets. (see `hdps/docs/source/components/core/explanation/image-storage-architecture.rst` for description of minipix activation system)


**Pre-selected Science Targets**
Only certain sources will need to be saved at the 1-minute and 1-second cadence; these sources are designated "pre-selected science targets."
For a given pre-selected science target, the minipix(es) in which it appears is(are) activated, either for the entire duration of the survey or for more specific periods of time.  



AIC Collections
---------------

Because astronomical sources exhibit a diverse range of complex behavior which informs minipix selection, the AIC is divided into several collections.

.. list-table::
   :widths: 30 30 40 40 40
   :header-rows: 1

   * - Collection
     - Catalog Type
     - Inputs from:
     - Outputs to:
     - Notes
   * - **AIC Refcat**
     - object catalog
     - Constituent reference catalogs (ATLAS, PanSTARRS, etc.)
     - AIC Base
     - Contains all "static" pre-selected science targets
   * - **AIC Base**
     - minipix catalog
     - AIC Refcat
     - Minipix-activation part of hdps (:package:`hdps.skymap`)
     - Contains "always-active" minipix?
   * - **AIC SSO Refcat**
     - object catalog
     - MPC objects database
     - SSO prediction part of pipeline (:package:`hdps.catalogs.movers`)
     - Essentially built each night by hdps.catalogs.movers; do we need/want to try to predict every known SSO that Argus will observe?  Why would that be useful/necessary?
   * - **AIC SSOs**
     - minipix catalog
     - SSO prediction part of pipeline (:package:`hdps.catalogs.movers`)
     - Minipix-activation part of hdps (:package:`hdps.skymap`)
     - Contains "toggle" minipix
   * - **AIC Transients**
     - minipix/object?
     - difference imaging part of pipeline
     - Minipix-activation part of hdps (:package:`hdps.skymap`)
     - 
   * - **AIC Requests**
     - minipix/object?
     - Source/minipix activation requests from science team
     - Minipix-activation part of hdps (:package:`hdps.skymap`)
     - 


AIC Refcat-Base
~~~~~~~~~~~~~~~

AIC Refcat-Base is an object catalog constructed from constituent reference catalogs (ATLAS-Refcat2, PanSTARRS, Gaia Galaxy Candidates, and NGC).
It contains all "static" targets, which:
  - will appear in the same minipix in every image
  - can be point-like or extended sources  

Build and save with :class:`hdps.catalogs.AICRefcatBuilder`:
.. code-block:: python
    from hdps.catalogs import AICRefcatBuilder
    builder = AICRefcatBuilder()
    builder.build(out_path="/net/scratch/kmfas/aic_refcat",catalogs=[ATLASRefcat2(),PanSTARRS()]).write()

Loaded from disk with :class:`hdps.catalogs.AICRefcat`:
.. code-block:: python
    from hdps.catalogs import AICRefcat
    # Lazily load AIC Refcat 
    aic_refcat = AICRefcat().load("/net/scratch/kmfas/aic_refcat/aic_refcat")


AIC Base
~~~~~~~~

AIC Base is a minipix catalog which contains each minipix that contains a pre-selected static science target from AIC Refcat.


AIC SSO Refcat
~~~~~~~~~~~~~~

AIC Refcat-SSOs is an object catalog containing all known solar system objects (SSOs) that will be observed by Argus.


AIC SSOs
~~~~~~~~

AIC SSOs is a minipix catalog that is refreshed each night to include SSOs predicted to appear in that night's Argus images.
Required functionality:
- retrieve all predicted positions of all SSOs that make the cut at the time of every Argus epoch 
- identify all tile/minipix indices and associated timestamps of each epoch position
- determine activation time/duration for each minipix
- send list to hdps.skymap
- save list?

AIC Transients
~~~~~~~~~~~~~~

AIC Transients will handle transient events detected in difference images by the pipeline, post real/bogus cut.  
Required functionality: 
- retrieve tile/minipix index and timestamp of all incoming transients
- determine activation time/duration for each minipix
- send list to to hdps.skymap
- save list?  add source / minipix to AIC Refcat-Base / AIC Base?

AIC Requests 
~~~~~~~~~~~~

AIC Requests will handle minipix activation requests from the Argus Science Team during survey operations.  