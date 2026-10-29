ADR for :package:`hdps.catalogs`

# ADR-00??: HATS implementation in the Argus Input Catalog

**Status:**  
**Date:** 

## Context
The Argus Input Catalog (AIC) contains all pre-selected science targets for which single-epoch image data will be saved at the 1-minute and 1-second cadence (object catalogs).  
It also contains all unique minipix in which these sources appear (minipix catalogs).
Both types of catalog are saved and analyzed in HATS format with the LSDB framework (tools created by LINCC).




### Considered Options
Reading parquet files 


## Decision



## Consequences

### Positive

### Negative

## References


- Saving, loading, and analyzing catalogs in HATS format with lsdb
    - The main "issue" is that the constituent reference catalogs, & therefore AIC Refcat, are on the order of 1 billion rows; any analysis performed on/with these cats in a timely manner will have to be done in parallel.  LINCC's __[LSDB](https://github.com/astronomy-commons/lsdb)__ package (build around Dask) provides these tools.  Catalogs are lazily loaded as Dask __[DataFrames](https://docs.dask.org/en/stable/dataframe.html)__, and you can plan computations and execute them whenever is convenient.
    - I use LSDB to open/interact with catalogs in HATS format, separated into partitions which have roughly equal amounts of sources.  I will put whatever constituent reference catalogs we need to use into HATS format for speedy access/usage (if they are not already available in HATS format).  These constituents are either be on-disk (ATLAS-Refcat2), or accessed externally if they are available on the LSDB data cloud (Pan-STARRS and Gaia).  AIC Refcat will be saved to disk.  

- Structure - AICRefcat to load and AICRefcatBuilder to build/save
    - 