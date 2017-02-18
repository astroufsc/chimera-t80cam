import logging
from chimera_t80cam.instruments.ebox.fsupolarimeter.fsupolarimeter import PolarimeterWheelBase

log = logging.Logger(__name__)


class FSUPolarimeterFilterWheel(PolarimeterWheelBase):
    def __init__(self):
        PolarimeterWheelBase.__init__(self)
        self["device"] = None
        self['filter_wheel_model'] = "Fake Polarimeter Filter Wheel"
        self["filters"] = "CLEAR B V R I"

    # def getMetadata(self, request):
    #     return [('FILTER', str(self.getFilter()), 'Filter used for this observation')]
        # ('FWHEEL', str(self['filter_wheel_model']), 'FilterWheel Model'),
