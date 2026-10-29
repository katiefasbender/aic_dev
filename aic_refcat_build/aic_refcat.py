"""Container and Builder for Argus Input Catalog Reference Catalog (AIC Refcat).

Classes:
--------
AICRefcat - Container for HATS-ed AIC Refcat, once it has been built and saved
AICRefcatBuilder - Builds AICRefcat from constituent catalogs (defaults: Gaia Source, PanSTARRS OTMO)

Examples:
---------
>>> from hdps.catalogs import AICRefcat,AICRefcatBuilder,ATLASRefcat2,PanSTARRS,GaiaSource

#Load AIC Refcat (if already built saved to disk):
>>> aic_refcat = AICRefcat.load(path="/path/to/aic_refcat")

#Build AIC Refcat and save to disk (use a Dask client for speed!):
>>> with Client(n_workers=4,threads_per_worker=1,memory_limit="20GiB") as client:
>>>     AICRefcatBuilder().build(catalog_outpath="/path/to/aicrefcat/output",catalogs=[ATLASRefcat2("/path/to/alas"),PanSTARRS("/path/to/panstarrs"),GaiaGalaxyCandidates("/path/to/gaiagals")]).write()

"""

from dataclasses import dataclass
from functools import cached_property, reduce
import logging
import lsdb
import pandas as pd
import os

from hdps.skymap import TanSegmentLookup, SegmentationScheme

logger = logging.getLogger(__name__)



@dataclass
class AICRefcat:  
    """
    Container for AIC Refcat, which has previously been built & saved to disk.

        - Opens (lazily) AIC Refcat from disk with LSDB
        - TODO: build functionality to apply filters and only open certain partitions

    Attributes
    ----------
    catalog (lsdb.Catalog object) - holds AIC Refcat data
    path (str) - location of HATS-ed catalog on disk

    Methods
    -------
    load() - Lazily load AIC Refcat, which has been built & saved to disk

    Examples:
    ---------
    # load pre-built AIC Refcat:
    >>> aicrefcat = AICRefcat.load(path="/path/to/aicrefcat",columns=["column","name","list"],filters=[["col1",<,value],["col2",=,"value"]])

    # create AICRefcat instance with an existing lsdb.Catalog object and a path for it to be saved to later:
    >>> import lsdb
    >>> catalog = lsdb.open_catalog("/path/to/catalog")
    >>> aicrefcat = AICRefcat(catlog=catalog,path="/path/to/save/aicrefcat")

    """

    NAME = "aicrefcat"
    FULL_NAME = "AIC Refcat"
    DEFAULT_PATH = "/net/scratch/kmfas/atlas_refcat2/atlas_0_01"  # placeholder
    MINIMUM_COLUMNS = ["ra", "dec", "tanseg_id", "local_idx"]

    def __init__(
        self,
        catalog: lsdb.Catalog,
        path: str,
    ):
        self.catalog = catalog
        necessary_columns = self.MINIMUM_COLUMNS
        for col in necessary_columns:
            if col not in self.catalog.columns:
                err = f"Necessary column {col} not in AIC Refcat columns"
                raise RuntimeError(err)
        self.path = path
        if not os.path.exists(path):
            err = f"Path {path} does not exist"
            raise RuntimeError(err)

    @classmethod
    def open(
        cls,
        path: str,
        columns: list = None,
        filters: list = None,
    ):
        """
        Lazily load all sources from AIC Refcat, if it has already been built & saved to disk in HATS format, and return AIC Refcat as an lsdb.Catalog object.

        Parameters
        ----------
        path (str) Path to HATS-ed catalog
        columns (list[str]) Columns to load ("ra","dec" will always be returned)
        filters (list[tuple[str]]) Filters to apply to rows when opening catalog

        Returns
        -------
        AICRefcat An instance of AICRefcat, which holds a lazily-loaded lsdb.Catalog object.

        Example:
        --------
        >>> aic_refcat = AICRefcat.open(aicrefcat_path="/path/to/aic_refcat",columns=["ra","dec","g","hello"],filters=[["dec",">",-20],["g","<",19]])

        """

        # Lazily load AICRefcat
        logger.debug("\n----------------\nLazily-loading AIC Refcat")
        if not os.path.exists(path):
            err = f"Path {path} does not exist"
            raise RuntimeError(err)
        if columns is None:
            columns = "all"
        # if filters == None:
        #    filters = []
        aic_refcat = lsdb.open_catalog(path, filters=filters, columns=columns)
        logger.debug("    AIC Refcat lazily loaded\n----------------\n")

        # Check that AICRefcat looks like it's supposed to:
        # - At minimum, contains RA, Dec, tile and minipix columns
        necessary_columns = cls.MINIMUM_COLUMNS
        for col in necessary_columns:
            if col not in aic_refcat.columns:
                err = f"Necessary column {col} not in AIC Refcat columns"
                raise RuntimeError(err)

        return cls(aic_refcat, path)


def lookup_minipix_idx(
    dframe: pd.DataFrame,
    lookup: TanSegmentLookup,
    coord_cols: list = None,
):
    """
    Look up tile/tanseg IDs and minipix/local indices for sources in dframe and return dframe with added columns for those IDs.

    Parameters
    ----------
    dframe (DataFrame) Reference catalog of sources with RA, Dec coordinates
    lookup (TanSegmentLookup) Lookup for tanseg IDs and minipix/local indices
    coord_cols (lst[str]) a list of column names for RA,Dec (in that order)

    Returns
    -------
    dframe (DataFrame) Reference catalog with added tile ID & minipix index columns

    Example:
    --------
    >>> import pandas as pd
    >>> from hdps.skymap import TanSgmentLookup
    >>> dataframe = pd.DataFrame({"id":["0","1","2"],"ra":[40,12,3],"dec":[-3,50,79]})
    >>> lookup = TanSegmentLookup(spacing_deg=0.25,pixel_scale=.87,dec_min=-20,ra_min=0)
    >>> dataframe_with_minipix_cols = AICRefcat().lookup_minipix_idx(dataframe,lookup)

    """

    # Get coordinate and tile column names:
    if coord_cols is None:
        coord_cols = ["ra", "dec"]
    tile_cols = ["tanseg_id", "local_idx"]

    df = dframe.copy()  # to make sure the columns aren't added to the input dataframe, but to a new df to output [still need this?]

    # Lookup tile IDs and local indices for all sources in dframe
    # logger.debug("Looking up tile IDs & minipix indices")
    tanseg_ids, local_idxs = lookup.query_batch(np.array(df[coord_cols[0]]), np.array(df[coord_cols[1]]))

    # Add ID columns to dframe
    df[tile_cols[0]] = tanseg_ids
    df[tile_cols[1]] = local_idxs
    # logger.debug("    - Columns '", tile_cols[0], "' and '", tile_cols[1], "' added")

    return df


class AICRefcatBuilder:
    """Builds AIC Refcat from constituent reference catalogs.

        - Lazily loads in reference source catalog(s) with LSDB & appropriate filters on columns, rows
            - Assumes refcats are in HATS-ed format, either saved on disk or available at data.lsdb.io
        - If needed (usually the case), looks up tile/minipix IDs add adds two columns (tile ID, minipix index) to each refcat
        - If building from multiple reference catalogs, concatenates those refcats
        - Resulting catalog is AIC Refcat and can be written to disk
            ****** A re-import to HATS is probably needed at this point if concatenating cats, will add this functionality later

    Attributes:
    -----------
    tile_arcsec (float) - Tile size [arcsec] for building TanSegmentLookup to retrieve tile/minipix indices
    overlap_arcsec (float) - Tile overlap [arcsec] for building TanSegmentLookup to retrieve tile/minipix indices
    pixel_scale_arcsec (float) - Pixel scale [arcsec/pixel] for building TanSegmentLookup to retrieve tile/minipix indices
    dec_min (float) - Minimum Dec [degree] for building TanSegmentLookup to retrieve tile/minipix indices
    ra_min (float) - Minimum RA [degree] for building TanSegmentLookup to retrieve tile/minipix indices


    Methods:
    --------

    _make_meta() - Create a meta information object [an empty pandas dataframe] for a given dataframe

    _open_refcats() - Lazily load constituent reference catalogs as lsdb.Catalog objects

    build() - Build AIC Refcat from given constituent refrerence catalogs

    write() - Save AIC Refcat to disk with lsdb and a Dask Client after building

    """

    def __init__(
        self,
        tile_arcsec: float = None,
        overlap_arcsec: float = None,
        pixel_scale_arcsec: float = None,
        dec_min: float = -90.0,
        ra_min: float = 0.0,
    ):
        # get sky tiling parameters
        if tile_arcsec is not None:
            self.tile_arcsec = tile_arcsec
        else:
            self.tile_arcsec = SegmentationScheme.DEFAULT_TILE_SIZE_ARCSEC
        if overlap_arcsec is not None:
            self.overlap_arcsec = overlap_arcsec
        else:
            self.overlap_arcsec = SegmentationScheme.DEFAULT_OVERLAP_ARCSEC
        if pixel_scale_arcsec is not None:
            self.pixel_scale_arcsec = pixel_scale_arcsec
        else:
            self.pixel_scale_arcsec = SegmentationScheme.DEFAULT_PIXEL_SCALE
        self.dec_min = dec_min
        self.ra_min = ra_min
        self._catalog = None

    @cached_property
    def lookup(self):
        """Create tanseg lookup with default sky tiling parameter"""
        return TanSegmentLookup(
            spacing_deg=(self.tile_arcsec - self.overlap_arcsec) / 3600.0,
            pixel_scale_deg=self.pixel_scale_arcsec / 3600.0,
            dec_min=self.dec_min,
            ra_min=self.ra_min,
        )

    def _make_meta(
        self,
        dframe: pd.DataFrame,
        add_tanseg_columns: bool = False,
    ):
        """
        Create and return a meta information object for a given dataframe (empty pandas dataframe)

        Parameters
        ----------
        dframe (pandas.DataFrame or lsdb.Catalog object)
        add_tanseg_columns (bool) add columns for tile/minipix indices; Default = False

        Returns
        -------
        meta (empty pandas.DataFrame) Column names and dtypes (for passing to lsdb.map_partition())

        Example:
        --------
        >>> import pandas as pd
        >>> dataframe = pd.DataFrame({"id":["0","1","2"],"ra":[40,12,3],"dec":[-3,50,79]})
        >>> meta = AICRefcatBuilder()._make_meta(datafame)

        """
        tanseg_columns = ["tanseg_id", "local_idx"]
        tanseg_dtypes = ["int32", "int16"]

        df_cols = list(dframe.columns)
        df_dtypes = list(dframe.dtypes)
        if add_tanseg_columns:
            df_cols = df_cols + tanseg_columns
            df_dtypes = df_dtypes + tanseg_dtypes
        meta = pd.DataFrame(
            {col: pd.Series(dtype=dtp) for col, dtp in zip(df_cols, df_dtypes)}
        )

        return meta

    def _open_refcats(
        self,
        catalogs: list,
    ):
        """
        Lazily load a number of Reference Catalogs to build AIC Refcat, build a meta for each, return a list of lsdb.Catalog objects and a list of metas.

        Parameters
        ----------
        catalogs (list) a list Reference Catalog Class Instance

        Returns
        -------
        refcats (list) a list of Reference Catalog Class Instance with catalog and meta information assigned

        Example:
        --------
        >>> catalogs = AICRefcatBuilder()._load_refcats(catalogs=[ATLASRefcat2(path="/path/to/atlas"),PanSTARRS(path="/path/to/panstarrs"),GaiaGalaxyCandidates(path="/path/to/gaiagals")])

        """

        # Load refcats with appropriate columns, filters
        # -----------------------------------------------
        logger.debug(f"Lazily-loading {len(catalogs)} reference catalogs to build AIC Refcat:")
        for cat in catalogs:
            # Check that cat is a class with attributes:
            if not hasattr(cat, "__dict__"):
                err = f"Catalog {cat} must be a Reference Catalog class instance"
                raise RuntimeError(err)
            for attr in ["FULL_NAME", "catalog", "meta"]:
                if not hasattr(cat, attr):
                    err = f"Reference Catalog class {cat} missing attribute {attr}"
                    raise RuntimeError(err)
            # Load catalog
            logger.debug(f"    - Opening {cat.FULL_NAME}")
            lazy_cat = lsdb.open_catalog(
                cat.path, columns=cat.columns, filters=cat.filters
            )
            # Rename RA,Dec columns if needed, for concatenation:
            if (lazy_cat.columns[1] != "ra") or (lazy_cat.columns[2] != "dec"):
                # expect column name elements [1,2] of Refcat Objects to be RA,Dec
                ra_col_name = cat.columns[1]
                dec_col_name = cat.columns[2]
                lazy_cat = lazy_cat.rename(
                    columns={ra_col_name: "ra", dec_col_name: "dec"}
                )
            # Create meta
            cat_meta = self._make_meta(lazy_cat, add_tanseg_columns=True)
            cat.catalog = lazy_cat
            cat.meta = cat_meta

        return catalogs

    def build(
        self,
        catalog_outpath: str,
        catalogs: list,
    ):
        """
        Build AIC Refcat: lookup tile/minipix indices, concatenate constituent catalogs

        Assigns built catalog to self._catalog as an AICRefcat Object:
        Catalog is lazily-loaded, with the following planned computations (to be executed upon writing catalog to disk):
            - for each individual catalog, tile/minipix lookup applied with map_partitions()
            - individual catalogs concatenated into aic_refcat with lsdb.concatenate()

        Parameters
        ----------
        catalog_outpath (str) full path to location on disk to save AICRefcat
        catalogs (list) list of Reference Catalog Class Instances

        Returns
        -------
        self

        Example:
        --------
        >>> refcat_builder = AICRefcatBuilder().build(catalog_outpath="/path/to/aicrefcat/",catalogs=[ATLASRefcat2(path="/path/to/atlas",columns=["ra","dec"],filters=[["ra",">",10]])])

        """

        # Lazily load reference catalogs
        logger.debug("\n----------------\nBuilding AIC Refcat")
        logger.debug("\nStarting catalog loading...")
        cats = self._open_refcats(catalogs=catalogs)

        # Look up tile/minipix indices
        logger.debug("\nStarting minipix lookups and catalog concatenation...")
        concatted_catalog = reduce(
            lambda acc, c: acc.concat(c),
            (
                cat.catalog.map_partitions(
                    lookup_minipix_idx, self.lookup, meta=cat.meta
                )
                for cat in cats
            ),
        )
        self._catalog = AICRefcat(catalog=concatted_catalog, path=catalog_outpath)
        logger.debug("\nAIC Refcat built\n----------------\n")

        return self

    def write(self):
        """
        Save AIC Refcat to path location, after building with AICRefcatBuilder().build()

        Things to be aware of:
            - this should probably be implemented with a Dask Client (see Example)
            - If tile/minipix ID and catalog concatenation have been planned with Dask/LSDB, these will be performed now.
            - It may be necessary to re-import AIC Refcat to HATS format, if it is comprised of multiple catalogs (functionality coming soon)

        Example:
        --------
        >>> with Client(n_workers=4,threads_per_worker=1,memory_limit="20GiB") as client:
        >>>     AICRefcatBuilder().build(catalog_outpath="/path/to/aicrefcat/output",[ATLASRefcat2("/path/to/atlas"),PanSTARRS("/path/to/panstarrs")]).write()
        """

        logger.debug(
            f"\nWriting AIC Refcat to {self._catalog.path + self._catalog.NAME}"
        )
        self._catalog.catalog.write_catalog(
            catalog_name=self._catalog.NAME, base_catalog_path=self._catalog.path,as_collection=False
        )
        logger.debug("AIC Refcat saved\n----------------\n")
