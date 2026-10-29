"""

AICRefcat

    Calls reference source catalog (in HATS format) as AIC Refcat, plus useful catalog stats; used to build AICBase
        - gathers all sources with applied filters
        - adds tile ID & minipix indices, if not already included
        - calculates useful stats 

AICBase 

    Builds a catalog of ''always-on'' active minipix from AIC Refcat
        - identifies unique minipix associated with AICRefcat sources
        - activates all unique minipix 

for now, requires lsdb to be installed (until it becomes a req for hdps)
uv pip install "lsdb[full]>=0.8.2"

"""

import astropy.units as u
from hdps.core import unix_to_argus_epoch #-> whatever time format sso detections come in
from hdps.skymap import SegmentationScheme, TanSegmentActivationManager, TanSegmentLookup
import lsdb
from lsdb.streams import CatalogStream

@dataclass
class AICRefcat:
    """
    Object for AIC Refcat
    - Reads in reference source catalog, from its HATS-ed format (either on-disk or through LSDB data cloud)
    - Adds tile & minipix ID columns if needed
    - Calculates stats and relevant values, caches them 

    Cal

    Attributes
    ----------
    catalog : lsdb.Catalog
        The reference catalog, lazily loaded in HATS format
    npartitions : int
        Number of HATS partitions 
    largest_part_ids : int
        Index of most populated "largest" partition (for applying CatalogStream)
    nsrc_largest : int
        Number of sources in largest partition (for applying CatalogStream)
    n_src : int
        Number of sources
    n_tiles : int
        Number of occupied tiles
    n_minipix : int
        Number of unique occupied minipix

    Parameters
    ----------
    refcat_path (str) Path to HATS-ed catalog 
    ra_col (str) Column name with RA values
                    Default = "ra"
    ra_min (float) Minimum RA (inclusive)
                    Default = 0
    ra_max (float) Maximum RA (inclusive)
                    Default = 360
    dec_col (str) Column name with Declination values
                    Default = "dec"
    dec_min (float) Minimum Dec (inclusive)
                    Default -20
    dec_max (float) Maximum Dec (inclusive)
                    Default 90
    mag_col (str) Column name with magnitude values for maglim
                    Default = "g"
    mag_lim (float) Max magnitude of sources in mag_col (inclusive)
                    Default = 20.5
    tile_col (str) Column name with tanseg/tile IDs
                    Default = "tanseg_id"
    minipix_col (str) Column name with minipix indices
                    Default = "local_idx" 
    """ 

    def __init__(
        self,
        refcat_path="/net/scratch/kmfas/atlas_refcat2/atlas_0_01/",
        ra_col="ra",
        ra_min=0,
        ra_max=360,
        dec_col="dec",
        dec_min=-30,
        dec_max=90,
        mag_col="g",
        mag_lim=20.5,
        tile_col="tanseg_id",
        minipix_col="local_idx",
    ):

        self.refcat_path = refcat_path
        self.ra_col = ra_col
        self.ra_min = ra_min
        self.ra_max = ra_max
        self.dec_col = dec_col
        self.dec_min = dec_min
        self.dec_max = dec_max
        self.mag_col = mag_col
        self.mag_lim = mag_lim
        self.tile_col = tile_col
        self.minipix_col = minipix_col

        self._lookup = None


    @property
    def lookup(self):
        """
        Lookup table for fast (ra, dec) -> (tanseg_id, local_idx) queries.
        The lookup is created lazily on first access and cached for reuse.

        Returns
        -------
        self._lookup (TanSegmentLookup) Lookup table for all-sky scheme
        """

        # if no lookup table, create one
        if self._lookup is None:
            from hdps.skymap import TanSegmentLookup
            self._lookup = TanSegmentLookup(
                spacing_deg=(self.tile_arcsec-self.overlap_arcsec)/3600.0, # Convert arcsec to deg
                pixel_scale_deg=self.pixel_scale_arcsec/3600.0,  # Convert arcsec to deg
                dec_min=self.dec_min,
                ra_min=self.ra_min,
            )

        return self._lookup

    def lookup_minipix_idx(self,dframe):
        """
        Get tile/tanseg IDs and minipix/local indices for sources in dframe.
        * Can be used with map_partitions()
        
        Parameters
        ----------
        dframe (DataFrame) Reference catalog of sources with RA, Dec coordinates

        Returns
        -------
        dframe (DataFrame) Reference catalog with added tile ID & minipix index columns
        """

        # Lookup tile IDs and local indices for all sources in dframe
        tanseg_ids,local_idxs = self.lookup.query_batch(dframe[self.ra_col],dframe[self.dec_col])

        # Add ID columns to dframe 
        dframe[self.tile_col] = tanseg_ids
        dframe[self.minipix_col] = local_idxs

        return dframe
    

    def load_aic_refcat(self,stats=True,verbose=False):
        """Lazily load sources from AIC refcat 
            - this catalog is on-disk in HATS format
            - select appropriate RA/Dec and magnitude limits 

        Parameters
        ----------
       stats (bool) Get number of partitions in reference catalog, and number of sources in most populated partition.
                        Use if you want to be smart about catalog streaming; takes longer to return.
                        Default = True
        verbose (bool) Whether to print out information
                        Default = False

        Returns
        -------
        refcat (lsdb.Catalog object) The AIC Refcat, lazily-loaded.  Adds "tanseg_id, "local_id" columns added if not already present
        npartitions (int) Number of partitions in AIC Refcat
                        * if smart==False, this is 0
        nsrc_in_largest_partition (int) Number of sources in most populated ''largest'' partition
                        * if smart==False, this is 0
        """
    
        # lazily load refcat 
        #refcat = lsdb.open_catalog(self.refcat_path,filters=[
        #                            [self.mag_col,"<=",self.mag_lim],
        #                            [self.ra_col,">=",self.ra_min],
        #                            [self.ra_col,"<=",self.ra_max],
        #                            [self.dec_col,">=",self.dec_min],
        #                            [self.dec_col,"<=",self.dec_max]])
        refcat = lsdb.open_catalog(self.refcat_path) # have to do it without filters b/c CatalogStream doesn't work :(

         # get name of reference catalog
        if self.refcat_path.split("/")[-3]=="atlas_refcat2":
            refcat_name = "ATLAS-Refcat2"
        else:
            refcat_name = self.refcat_path.split("/")[-2]
        if verbose: print(refcat_name," lazily loaded as AIC Refcat")

        # get stats if you want to be smart about catalog streaming
        if stats:
            npartitions,nsrc_in_largest_partition = self.get_refcat_stats(refcat,verbose)
        else:
            npartitions,nsrc_in_largest_partition = 0,0
        
        # lazily add tile/tanseg IDs and minipix/local indices if not already in refcat
        if self.tile_col and self.minipix_col not in refcat.columns:
            if verbose: print("    adding tile & minipix indices")
            refcat = refcat.map_partitions(self.lookup_minipix_idx)

        return refcat,npartitions,nsrc_in_largest_partition
    

    def get_refcat_stats(self,refcat,verbose=False):
        """
        Get number of partitions, and number of sources in most populated ''largest'' partition, for refcat.

        Parameters
        ----------
        refcat (lsdb.Catalog object) Reference catalog in HATS format with ra and dec columns
        verbose (bool) Whether to print out information 
                        Default = False
        
        Returns
        --------
        npartitions (int) Number of HATS partitions
        nsrc_in_largest_partition (int) Number of sources in most populated ''largest'' partition
        """

        # get number of partitions
        npartitions = refcat.npartitions
        if verbose: print("    ",npartitions," partitions in refcat")

        # get number of sources in most populated pixel to scale computations
        stats = refcat.per_pixel_statistics(include_columns=[self.ra_col,self.dec_col], include_stats=["row_count"])
        nsrc_in_largest_partition = stats.sort_values(["ra: row_count"], ascending=False).head(1).iloc[0][self.ra_col+': row_count']
        if verbose: print("    ",nsrc_in_largest_partition," sources in largest partition")

        return npartitions,nsrc_in_largest_partition




class AICBase:
    """
    Builds AIC Base, consisting of all "always-on" active minipix 
    that are pulled from AIC Refcat. 
    Initializes 

    Parameters
    ----------
    aic_refcat (AICRefcat object) Reference source catalog to use as AIC Refcat
    minipix_path (str) Path to directory in which to store minipix metadata


    """

    def __init__(
        self,
        aic_refcat = aic_refcat,
        minipix_path = "/net/scratch/kmfas/data/aic_base_minipix/",
    ):

        self.minipix_path = minipix_path    

        from hdps.skymap import SegmentationScheme
        self.tile_arcsec = SegmentationScheme.DEFAULT_TILE_SIZE_ARCSEC
        self.overlap_arcsec = SegmentationScheme.DEFAULT_OVERLAP_ARCSEC
        self.pixel_scale_arcsec = SegmentationScheme.DEFAULT_PIXEL_SCALE

        #self.scheme = SegmentationScheme.allsky()
        self._manager = None


    @property
    def manager(self):
        """
        TanSegment Manager activating minipix.
        The manager is created lazily on first access and cached for reuse.

        Returns
        --------
        self._manager (TanSegmentActivationManager) Tanseg Activation manager to store minipix data in self.minipix_path 
        """

        # if no manager, create one
        if self._manager is None:
            from hdps.skymap import TanSegmentActivationManager
            self._manager = TanSegmentActivationManager(self.minipix_path)

        return self._manager


    def initialize_minipix(self,quiet=True):
        """
        Initialize active minipix corresponding to sources in dframe,
        * Can't be used with map_partitions()

        Parameters
        ----------
        quiet (bool) Don't print out which tanseg/minipix have been activated.  For Katie's sanity.
                        Default = True

        Returns
        -------
        total_segments (int) Total number of unique tansegments
        total_active_minipixes (int) Total number of active minipix
        """

        # setup
        default_duration=100 * u.year # for how long are the minipixes active
        dframe = dframe[[self.tile_col,self.minipix_col]].drop_duplicates() # only want tanseg & minipix columns, and only unique pairs of tanseg+minipix 
        tanseg_ids = dframe[self.tile_col].unique() # all the unique tansegs 

        # if not quiet, use initialize_from_source_catalog()
        if not quiet:

            # initialize
            self.manager.initialize_from_source_catalog(
                dframe,
                tanseg_column=self.tile_col,
                local_idx_column=self.minipix_col,
                default_duration=default_duration,
            )

            total_segments = len(tanseg_ids)
            total_active_minipixes = len(dframe)

        # if quiet, use initialize_segment_metadata() and loop through unique tansegs 
        else:

            total_segments = 0
            total_active_minipixes = 0

            # loop through tansegs, get minipix for each and activate!  (this is what happens in initialize_source_catalog(), just without printout)
            for tanseg_id in tanseg_ids:

                # Get unique local indices for this segment
                segment_rows = dframe[dframe[self.tile_col] == tanseg_id]
                active_local_indices = set(segment_rows[self.minipix_col].unique())

                # initialize
                self.manager.initialize_segment_metadata(
                    int(tanseg_id),
                    active_minipixes=active_local_indices,
                    default_duration=default_duration,
                )

                total_segments += 1
                total_active_minipixes += len(active_local_indices)
        
        return total_segments,total_active_minipixes


    def initialize_catalog(self,smart=True,verbose=False):
        """
        Initialize AIC Base (call refcat & activate corresponding minipix)

        Parameters
        ----------
        refcat (DataFrame | None) Reference catalog 
        smart (bool) Smart-ly select number of reference catalog partitions to initialize at once (get refcat stats, takes longer)
                        Default = True
        verbose (bool) Whether to print out information
                        Default = False
        Returns
        -------

        """
        # lazily load in AIC Refcat 
        refcat,npartitions,nsrc_in_largest_partition = self.aic_refcat

        if smart:
            max_src_per_chunk = 2000000 # max sources per chunk
            parts_per_chunk = min(200,max_src_per_chunk//nsrc_in_largest_partition) # number of partitions per chunk, don't allow more than than 200 (this is basically to keep the number of sources per chunk under 2million)
        else: 
            parts_per_chunk = 2 # a safe amount, in case there's like 2million sources per partition (tryin to protect your memory here)

        # using CatalogStream, initialize all minipix
        cat_stream = CatalogStream(catalog=refcat, partitions_per_chunk=parts_per_chunk, seed=1)
        tot_tiles = 0
        tot_minipix_active = 0
        nsources = 0
        if verbose: print("Initializing refcat minipix, with ",parts_per_chunk," partitions per chunk\n***Will take 10-40 minutes, beware!")
        for chunk in cat_stream:
            chunk = chunk[(chunk[self.mag_col]<=self.mag_lim) & (chunk[self.ra_col]>=self.ra_min) & (chunk[self.ra_col]<=self.ra_max) & (chunk[self.dec_col]>=self.dec_min) & (chunk[self.dec_col]<=self.dec_max)]
            segments,minipix = self.initialize_minipix(chunk)
            nsrc_in_chunk = len(chunk)
            if verbose: print("    initialized ",minipix," minipix for ",nsrc_in_chunk," sources")
            tot_minipix_active = tot_minipix_active+minipix
            tot_tiles = tot_tiles+segments
            nsources = nsources+nsrc_in_chunk
        if verbose: print("Initialized ",tot_minipix_active," active minipix in ",tot_tiles," tiles for ",nsources," sources in reference catalog")

        ######################
        # ******************** do we want to have a list of all unique active tanseg+minipix?  If so, should it be saved to disk or kept in memory?  Important questions.....
        ######################

        return refcat,tot_tiles,tot_minipix_active
