"""
Tests for AIC Base


"""

import pytest
import astropy.units as u
from hdps.core import unix_to_argus_epoch #-> whatever time format sso detections come in
from hdps.skymap import SegmentationScheme, TanSegmentActivationManager, TanSegmentLookup
import lsdb
from lsdb.streams import CatalogStream


from hdps.catalogs.basecatalogbuilder import AICRefcat, AICBase