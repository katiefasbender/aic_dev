

from hdps.core import FullFrameImage, Catalog, unix_to_argus_epoch #-> whatever time format sso detections come in
from hdps.skymap import SegmentationScheme, TanSegmentActivationManager

class MinipixAccumulator:
    '''
    A class to handle active minipix for a given night (both "always-on" and "toggle" cases)

    Parameters
    ----------
    night: int
        the night for which you want to get active minipix




    '''



    def __init__(
        self,
        night: int
    ):
        '''Initialize the MinipixAccumulator

        Parameters
        ----------
        night : int

        '''
      
        # Parameters
        self.night = night  

        # Set up minipix/tanseg manager
        tanseg_storage_path = "./data/minipix/"
        manager = TanSegmentActivationManager(tanseg_storage_path)


    def get_active_minipix(self):
        '''
        Load in all active minipix visible tonight (both "always-on" and "toggle")
        '''

        
        always_active = get_always_active_minipix()
        toggle_active = get_toggle_active_minipix()


    def get_always_active_minipix(self):
        '''
        Load in active "always-on" minipix visible tonight.
        Expects to access an HATS-ed catalog of always-active minipix center coordinates 
        '''

    def get_toggle_active_minipix():
        '''
        Load in "toggle" minipix to activate/deactivate tonight 
        (effectively updates active minipix list)
        '''

        # Load minipix with SSO detections for tonight
        sso_minipix = get_sso_minipix(self.night,images,scheme)

        # Load minipix from transients flagged by pipeline (diffim sources)
        diffim_minipix = get_diffim_minipix(self.night,images,scheme)

        # Load minipix from external input (i.e. requests from science team)
        requested_minipix = get_requested_minipix(self.night,images,scheme)



    # for SSOs 
    def get_sso_minipix(self,night,scheme):
        '''
        Retrieve coordinates & timestamps of SSOs that appear in previous night's images
        and activate appropriate minipix for just the time that SSOs appear in them. 
        Expects SSO detections to be in a file named in the "<night>_whatever.extension" format,
        containing "ra", "dec", "time" columns

        Parameters
        ----------
        night : int
        images : list 

        Returns
        -------


        '''
        # get coords & timestamps for last night's SSOs
        detections_file = str(night)+"file_name_whatever" # output of Donovan's code
        sso_ras, sso_decs, sso_times = read_file_of_format_whatever(detections_file)

        # get minipix from coords
        tanseg_ids, minipix_ids = scheme.query_tile_id(sso_ras,sso_decs)

        # get times in argus epoch if necessary
        sso_argus_times = [whatevertimeformat_to_argus_epoch(str(t)) for t in sso_times] # will need to import appropriate "_to_argus_epoch" function

        # activate minipix for appropriate times

    def get_diffim_minipix(self,):
        '''
        How/where will the output for this process be stored?  What info will be included?
        '''

    def get_requested_minipix(self):
        '''
        How will people request minipix?  See requested_minipix_handler.py for more! (no solutions, just questions)
        I'm thinking a list of requested sources/minipix with activation time&duration will be the input here.  
        Probably in a file that this func can read in.
        '''


class Cataloger:
    '''
    A class to create a catalog from images taken in a night.
    Given a list or something of active minipix, and a list or something of images taken that night,
    pick out all the minipix from the images and send them to hdps_skymap to save
    '''

    def __init__(
        self,
        night: int,
    ):
        '''Initialize the Cataloger

        Parameters
        -----------
        night : int
        '''

    # Grab all images from previous night




    # select active minipix from an image

    def get_minipix_from_image(image_file):
        '''
        Select activated minipix from a reprojected image

        Parameters
        ----------
        image_file (str) Path to reprojected image

        Returns
        -------


        '''

        # Load Image

        image = FullFrameImage(image_file)


    # get source catalog from image - for SSOs 
    # create catalog of SSO ID and minipix 


