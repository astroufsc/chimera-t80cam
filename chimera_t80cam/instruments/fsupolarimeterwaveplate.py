import logging
from chimera_t80cam.instruments.ebox.fsupolarimeter.fsupolarimeter import PolarimeterWheelBase

log = logging.Logger(__name__)


class FSUPolarimeterWavePlate(PolarimeterWheelBase):
    def __init__(self):
        PolarimeterWheelBase.__init__(self)
        self["device"] = None
        self['filter_wheel_model'] = "Fake Polarimeter Wave Plate Wheel"
        self["filters"] = "0.0 22.5 45.0 67.5 90.0 112.5 135.0 157.5 180.0 202.5 225.0 247.5 270.0 292.5 315.0 337.5"
        self["id"] = 2

    # def getMetadata(self, request):
    #     return [('FILTER', str(self.getFilter()), 'Filter used for this observation')]
        # ('FWHEEL', str(self['filter_wheel_model']), 'FilterWheel Model'),
