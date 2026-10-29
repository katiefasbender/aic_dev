hdps.catalogs.aicrefcat 
=======================

The Argus Input Catalog (AIC) - Refcat
--------------------------------------

AIC Refcat includes all the "static" non-moving, non-transient, point sources from various constituent reference catalogs; it will be used to build AIC Base.  Transients & moving objects & requests from sci team are covered by other parts of AIC.

AIC Refcat is a reference source catalog that contains all of the pre-selected targets for which single-epoch image data will be saved at the 1 minute/second cadence.

**AIC Refcat** is a catalog of known sources that will be observed by Argus; minipix cutouts of these sources will be saved long-term (this minipix list is AIC Base, which is also built/handled by this package.)
- contains only the "constant" "static" point sources & extended objects to save in Argus observations
- will be constructed from multiple constituent reference catalogs (further testing required as of 2026/05):
    - ATLAS-Refcat2 Stellar Reference Catalog
        - for sources g <= 19 mag
        - only contains stars (with some galaxy contamination)
    - Gaia Galaxy Candidates
        - for sources G <= 19 mag (still needs testing)
        - to supplement ATLAS-Refcat2, which does not contain galaxies
    - PanSTARRS
        - for sources g > 19 mag
        - contains both stars and galaxies
- Built by the :class:`AICRefcatBuilder` class, loaded by :class:`AICRefcat` class.  :class:`AICRefcatBuilder` does the following:
    - loads all sources of interest with lsdb
    - identifies minipix/tile IDs for each source, if not already calculated & saved
    - writes catalog with IDs to disk, if not already saved








Examples
--------

Loading a pre-built/saved AIC Refcat

.. code-block:: python
        from hdps.catalogs import AICRefcat