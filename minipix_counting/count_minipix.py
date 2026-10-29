#/usr/bin/env python 

# Imports

import lsdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from hdps.skymap import SegmentationScheme


if __name__=="__main__":

    # Inputs





    atlas = lsdb.open_catalog()

    ps1 = lsdb.open_catalog()

    gaia_galaxies = lsdb.open_catalog()