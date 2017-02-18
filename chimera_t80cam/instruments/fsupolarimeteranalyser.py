import logging
from chimera_t80cam.instruments.ebox.fsupolarimeter.fsupolarimeter import PolarimeterWheelBase

log = logging.Logger(__name__)

class FSUPolarimeterAnalyser(PolarimeterWheelBase):
    # Maybe this one should override the method setFilter to a float number which is the dither position in mm

    def __init__(self):
        PolarimeterWheelBase.__init__(self)
        self["device"] = None
        self['filter_wheel_model'] = "Fake Polarimeter Dithering position"
        self["filters"] = "0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17"

    # def getMetadata(self, request):
    #     return [('POL_DITHER', str(self.getFilter()), 'Polarimeter Dither position')]
        # ('FWHEEL', str(self['filter_wheel_model']), 'FilterWheel Model'),