"""

Minipix Accumulator

Manages minipix activation/deactivation requests;
adds "toggle" minipix to the base catalog of "always-on" active minipix.

Saves catalog of active toggle minipix to disk in HATS format.

Assumes a catalog of "always-on" active minipix are
stored in a HATS format somewhere on disk.

"""

from hdps.core import (
    FullFrameImage,
    Catalog,
    unix_to_argus_epoch,
)  # -> whatever time format sso detections come in
from hdps.skymap import SegmentationScheme, TanSegmentActivationManager


class MinipixAccumulator:
    """
    A class to handle active minipix for a given night ("toggle" cases)
    - accumulate toggle minipix for this night
    - activate/deactivate toggle minipix

    Parameters
    ----------
    night: int
        the night for which you want to get active minipix




    """

    def __init__(self, night: int):
        """Initialize the MinipixAccumulator

        Parameters
        ----------
        night : int

        """

        # Parameters
        self.night = night

        # Lazy-initialized manager for minipix activation
        self.tanseg_storage_path = "./data/minipix/"
        # manager = TanSegmentActivationManager(tanseg_storage_path)
        self._manager = None

    @property
    def manager(self):
        """
        TanSegmentActivationManiger for minipix activation.

        The lookup is created lazily on first access and cached for reuse.

        Returns
        -------
        TanSegmentLookup
            Lookup table configured for this scheme
        """
        if self._manager is None:
            from hdps.skymap import TanSegmentActivationManager

            self._manager = TanSegmentLookup(
                spacing_deg=self.spacing_deg,
                pixel_scale_deg=self.pixel_scale / 3600.0,  # Convert arcsec to deg
            )
        return self._manager

    def get_active_minipix(self):
        """
        Load in all active minipix visible tonight (both "always-on" and "toggle")
        """

        always_active = get_always_active_minipix()
        toggle_active = get_toggle_active_minipix()

    def get_toggle_active_minipix():
        """
        Load in "toggle" minipix to activate/deactivate tonight
        (effectively updates active minipix list)
        """

        # Load minipix with SSO detections for tonight
        sso_minipix = get_sso_minipix(self.night, images, scheme)

        # Load minipix from transients flagged by pipeline (diffim sources)
        # diffim_minipix = get_diffim_minipix(self.night,images,scheme)

        # Load minipix from external input (i.e. requests from science team)
        # requested_minipix = get_requested_minipix(self.night,images,scheme)

    # for SSOs
    def get_sso_minipix(self, night, scheme):
        """
        Retrieve coordinates & timestamps of SSOs that appear in a given night's images
        and activate appropriate minipix for just the time that SSOs appear in them.
        Currently expects SSO detections to be in a parquet file named in the "<night>_whatever.parquet" format,
        containing "ra", "dec", "time", "objectid" columns.
        Eventually, it will be able to alternatively accept a Python object with the necessary SSO detection info.

        Parameters
        ----------
        night : int
        images : list

        Returns
        -------


        """
        # get coords & timestamps for last night's SSOs
        detections_file = (
            str(night) + "_file_name_whatever.parquet"
        )  # output of Donovan's code
        ssos = read_file_of_format_whatever(detections_file)

        # get minipix from coords
        tile_ids, minipix_ids = lookup.query_batch(ssos["ra"], ssos["dec"])

        # get times in argus epoch if necessary
        ssos["time_argus"] = whatevertimeformat_to_argus_epoch(
            sso["time"]
        )  # will need to import appropriate "_to_argus_epoch" function

        # activate minipix for appropriate times

    def get_diffim_minipix(
        self,
    ):
        """
        How/where will the output for this process be stored?  What info will be included?
        """

    def get_requested_minipix(self):
        """
        How will people request minipix?  See requested_minipix_handler.py for more! (no solutions, just questions)
        I'm thinking a list of requested sources/minipix with activation time&duration will be the input here.
        Probably in a file that this func can read in.
        """
