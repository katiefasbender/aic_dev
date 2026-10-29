"""Build toy AIC Refcat"""
from astropy.coordinates import Distance,SkyCoord
from astropy.time import Time

from astropy import units as astro_unit
import astropy.units as u
import astropy.units.cds as ucds
from astropy.table import *
from dask.distributed import Client
from dataclasses import dataclass, field
from itertools import combinations
import lsdb
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


import mocpy
from mocpy import MOC
from hdps.skymap import SegmentationScheme,TanSegmentLookup

import warnings
from erfa import ErfaWarning
from astropy.utils.exceptions import AstropyWarning


warnings.filterwarnings('ignore', category=ErfaWarning)
warnings.simplefilter('ignore', category=AstropyWarning)



# Silence runtime invalid warnings locally
#with warnings.catch_warnings():
#    warnings.filterwarnings('ignore', message='invalid value encountered in pmsafe')




def get_synphot_and_propagate(dframe):

    if len(dframe) == 0:
        col_type = np.array([], dtype=float)
        return dframe[["ra", "dec"]].assign(ra_corr=col_type, dec_corr=col_type)

    def linear_func(x,a,b):
        return a+(x*b)

    # synthetic photometry

    a_grho = -0.2144863922451342
    b_grho = 0.5185776973884502
    a_gbeta = -0.01588226688060276
    b_gbeta = 0.5185776973884502

    gaia_g = np.array(dframe['phot_g_mean_mag'])#[0]
    gaia_bp_rp = np.array(dframe['bp_rp'])#[0]
    argus_rho = gaia_g - linear_func(gaia_bp_rp,a_grho,b_grho)
    argus_beta = gaia_g - linear_func(gaia_bp_rp,a_gbeta,b_gbeta)

    # propagate 

    sources = SkyCoord(
        ra=np.array(dframe['ra'])* u.deg, 
        dec=np.array(dframe['dec']) * u.deg, 
        pm_ra_cosdec=np.array(dframe['pmra']) * u.mas / u.yr, # Proper motion in RA (including cos(dec) factor)
        pm_dec=np.array(dframe['pmdec']) * u.mas / u.yr,       # Proper motion in Dec
        #radial_velocity=np.array(dframe['radial_velocity'])*u.km/u.second,
        #distance=Distance(parallax=np.array(dframe['parallax'])*u.marcsec,allow_negative=True),
        obstime=Time('J2016.0'),           # Original catalog/observation epoch
        frame='icrs'
    )

    target_epoch = Time('J2026.0')
    propagated_sources = sources.apply_space_motion(new_obstime=target_epoch)

    #delta_yr = 2026.0-np.array(dframe['ref_epoch'])[0]
    #ra_new = np.array(dframe['ra'])+(dframe['pmra']*delta_yr/1000.0/np.cos(np.deg2rad(gaia2['dec'])))
    #dec_new = np.array(dframe['dec'])+(dframe['pmdec']*delta_yr/1000.0)


    dframe = dframe.drop(columns=["ref_epoch"])
    dframe['argus_beta_synth'] = argus_beta
    dframe['argus_rho_synth'] = argus_rho
    dframe['ra_prop'] = propagated_sources.ra.value
    dframe['dec_prop'] = propagated_sources.dec.value
    dframe['epoch'] = 2026.0

    dframe.dropna(subset=["ra","dec"], inplace=True)

    return(dframe)

if __name__=="__main__":

    scheme = SegmentationScheme.all_sky()

    # define sky tiling parameters
    tile_size_arcsec = scheme.DEFAULT_TILE_SIZE_ARCSEC
    overlap_arcsec = scheme.DEFAULT_OVERLAP_ARCSEC
    pixel_scale = scheme.DEFAULT_PIXEL_SCALE 

    # define the lookup
    lookup = TanSegmentLookup(
        spacing_deg=(tile_size_arcsec-overlap_arcsec)/3600, # (tile_size - overlap) in degrees
        pixel_scale_deg=pixel_scale/3600,                    # arcsec to degrees
        dec_min=-90.0,
        ra_min=0
    ) 

    # get MOC 
    tiles = pd.read_parquet("/home/kmfas/aic_dev/argus_segments.parquet")
    id_set = set(tiles['seg'])
    tile_matches = [(i, d) for i, d in enumerate(scheme.tiles) if d["tile_id"] in id_set]#[:8]

    mocs = []
    for idx,tile in tile_matches:
        corners = scheme._calculate_tile_footprint(tile,idx)
        #print(corners)
        moc = MOC.from_polygon(corners[:,0]*u.degree, corners[:,1]*u.degree, max_depth=7)
        mocs.append(moc)

    union_moc = MOC.union(*mocs)

    # Lazily load Gaia
    gaia = lsdb.open_catalog("/net/scratch/kmfas/gaia",
                         columns=["source_id","ref_epoch","ra", "dec", "phot_g_mean_mag", "bp_rp","pmra","pmdec","radial_velocity",'parallax'],
                         filters=[["phot_g_mean_mag","<=",20]])
    gaia_field = gaia.moc_search(union_moc)

    # make meta for map_partitions()
    gaia_synprop_dtypes = np.array(["int64[pyarrow]", "double[pyarrow]", "double[pyarrow]",
        "float[pyarrow]", "float[pyarrow]",
        "double[pyarrow]", "double[pyarrow]", "float[pyarrow]", "double[pyarrow]",
        'float32', 'float32', 'float64',
        'float64', 'float64'])
    gaia_synprop_columns = np.array(['source_id', 'ra', 'dec', 'phot_g_mean_mag',
        'bp_rp', 'pmra', 'pmdec', 'radial_velocity',
        'parallax', 'argus_beta_synth', 'argus_rho_synth', 'ra_prop',
        'dec_prop', 'epoch'])

    scratch_meta_gaia_synprop = pd.DataFrame({col: pd.Series(dtype=dtp) for col,dtp in zip(gaia_synprop_columns,gaia_synprop_dtypes)})



    # get synthetic photometry & propagate
    gaia_field_withsynth = gaia_field.map_partitions(get_synphot_and_propagate,meta=scratch_meta_gaia_synprop)

    # write to HATS-ed catalog
    with Client(n_workers=4,memory_limit="20GB") as client:
        gaia_field_withsynth.write_catalog(base_catalog_path="/tank/catalogs/aic_refcat_sample/",catalog_name="aic_refcat",as_collection=False,overwrite=True)


