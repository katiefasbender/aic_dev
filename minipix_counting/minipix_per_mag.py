'''
For a given source catalog, calculate the number of unique minipix 
occupied by sources, down to limiting magnitudes in 0.5-mag steps, and 
fit a model to describe the fraction of occupied minipix (out of all
minipix across the sky) as a funciton of limiting magnitude.
'''



from argparse import ArgumentParser
import dask
from dask.distributed import Client
import lsdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as scistat
import scipy as sp
import time


from hdps.skymap import SegmentationScheme,TanSegmentLookup
from hdps.catalogs import ATLASRefcat2,PanSTARRS,AICRefcat,AICRefcatBuilder



def bin_mags(dframe,bin_col,bin_edges,meth,count=True):
    # establish data on which to bin
    data = dframe[bin_col]
    # define bin edges
    # bin with .....
    # - scipy
    if meth=="scipy.binstat":
        bins = scistat.binned_statistic(data, data, bins=bin_edges, statistic="count", range=(0, 1))
        bin_nums = bins.binnumber
        if count:
            counts = bins.statistic
    # - numpy
    elif meth=="numpy.dig":
        bin_nums = np.digitize(data,bin_edges,right=True)
        if count:
            counts = np.histogram(bin_nums,bins=len(bin_edges)-1)[0]
    # - or a method that is not supported
    else:
        print(f"method {meth} not supported")
    # make a column with bin number
    dframe['mag_bins'] = bin_nums
    # return dframe and, if specified, bin counts
    if count: 
        return(dframe,counts)
    else:
        return(dframe)
    

def lookup_minipix_idx(dframe,ra_col,dec_col,lookup):
    # Lookup tile IDs and local indices for all sources in dframe
    tanseg_ids, local_idxs = lookup.query_batch(dframe[ra_col], dframe[dec_col])
    # Add ID columns to dframe
    dframe["tanseg_id"] = tanseg_ids
    dframe["local_idx"] = local_idxs
    # return dframe
    return dframe

def bin_and_lookup_and_accum(dframe,bin_col,ra_col,dec_col,lookup):
    '''
    For a dataframe, 
        bin sources in magnitude, 
        look up tile/minipix ID for each source, 
        generate a list of "number of cumulative unique minipix" in each bin,
        return that list
    '''
    # - Make a copy of dframe
    dframe_copy = dframe.copy()
    # - Bin in g mag
    bin_edges = np.arange(10,22.5,0.5) # bin edges, right-most included
    bin_col = bin_col # column to bin on 
    meth = "scipy.binstat" # binning method
    dframe_copy,source_count_per_bin = bin_mags(dframe_copy,bin_col,bin_edges,meth,count=True)
    # - Look up tile/minipix idx
    dframe_copy = lookup_minipix_idx(dframe_copy,ra_col,dec_col,lookup)
    # - Loop through bins and get cumulative unique minipix count for each
    nbins = len(bin_edges)-1 # number of bins
    cumulative_unique_minipix_count_per_bin = [] # list of cumulative unique minipix count per bin
    cumulative_source_count_per_bin = np.cumsum(source_count_per_bin).tolist() # list of cumulative source count per bin
    for magbin in range(0,nbins):
        # - select sources in that bin and all brighter bins
        cum_bincat = dframe_copy[dframe_copy['mag_bins']<=(magbin+1)]
        # - generate the list of unique tile+minipix in all those bins & save the length
        cum_bin_unique_minipix = cum_bincat[['tanseg_id','local_idx']].drop_duplicates()
        cumulative_unique_minipix_count_per_bin.append(len(cum_bin_unique_minipix))
    return(cumulative_unique_minipix_count_per_bin, cumulative_source_count_per_bin)


if __name__=="__main__":

    # Define input arguments
    parser = ArgumentParser(description="For a catalog, count the minipix containing sources in each magnitude bin (0.5 mag).")
    parser.add_argument('--catalog',type=str,nargs=1,default=["atlas"],help="Name of cat.  Currently supported:\n    ''atlas'' (ATLAS-Refcat2, Default)\n    ''panstarrs' (PanSTARRS)")
    args = parser.parse_args()

    # Get inputs

    # catalog name
    catalog = args.catalog[0]


    if catalog == "panstarrs":
        magcols = ["gMeanApMag","rMeanApMag","iMeanApMag","zMeanApMag","yMeanApMag"]
        racol = "raMean"
        deccol = "decMean"
        cat = PanSTARRS("/net/scratch/kmfas/panstarrs")
        cat.columns = ["raMean","decMean"] + magcols
    elif catalog == "atlas":
        magcols = ["g"]
        racol = "ra"
        deccol = "dec"
        cat = ATLASRefcat2("/net/scratch/kmfas/atlas_refcat2/atlas_full")
        cat.columns = ['ra', 'dec', 'parallax', 'pmra', 'pmdec', 'g', 'r', 'i', 'h32', 'h64', 'h256']
    filters = "" #[] #[magcol, '>=', -20.0],[magcol, '>=', 15.0]]
    for magcol in magcols:
        filters += magcol + " <= 22.0 or " #filters.append([magcol,"<=",22.0])
    cat.filters = filters[:-4]
    catalog_full = lsdb.open_catalog(cat.path,columns=cat.columns)#,filters=cat.filters)
    cat.catalog = catalog_full.query(cat.filters)

    # define a TanSeg lookup & tiling scheme parameters
    overlap_arcsec = SegmentationScheme.DEFAULT_OVERLAP_ARCSEC
    tile_size_arcsec = SegmentationScheme.DEFAULT_TILE_SIZE_ARCSEC
    pixel_scale_arcsec = SegmentationScheme.DEFAULT_PIXEL_SCALE
    spacing_arcsec = tile_size_arcsec - overlap_arcsec
    lookup = TanSegmentLookup(
        spacing_deg=spacing_arcsec/3600.0,
        pixel_scale_deg=pixel_scale_arcsec/3600.0,
        dec_min=-90.0,
        ra_min=0.0)

    # create the delayed catalog and set up delayed dask computation:
    delayed_cat = cat.catalog.to_delayed()
    results = [dask.delayed(bin_and_lookup_and_accum)(p,magcol,racol,deccol,lookup) for p in delayed_cat]
    cum_minipix_counts = [r[0] for r in results]
    cum_source_counts = [r[1] for r in results]

    start = time.time()
    print(f"Computing cumulative unique minipix and source counts per magnitude bin for {cat.FULL_NAME} partitions...")
    with Client(n_workers=4,memory_limit="20GiB",threads_per_worker=1) as client:
        # list of computed cumulative minipix counts per partition
        compute_cum_minipix_counts,compute_cum_source_counts = dask.compute(cum_minipix_counts,cum_source_counts)
    end = time.time()
    print(f"Calculated counts in {end-start} seconds")
    
    total_cum_minipix_count_per_bin = np.sum(compute_cum_minipix_counts, axis=0).tolist()
    total_cum_source_count_per_bin = np.sum(compute_cum_source_counts, axis=0).tolist()
    print("total cumulative minipix count ber mag bin = ",total_cum_minipix_count_per_bin)
    print("total cumulative source count ber mag bin = ",total_cum_source_count_per_bin)

    # fit 2D model to fractional minipix occupancy as a func of limiting mag
    
