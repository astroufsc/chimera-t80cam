import logging
from chimera_t80cam.instruments.ebox.fsupolarimeter.fsupolarimeter import PolarimeterWheelBase

log = logging.Logger(__name__)


class FSUPolarimeterAnalyzerWheel(PolarimeterWheelBase):
    def __init__(self):
        PolarimeterWheelBase.__init__(self)
        self["device"] = None
        self['filter_wheel_model'] = "Fake Polarimeter Analyzer Wheel"
        self["filters"] = "CLEAR CALCITE VIS RED"
        self["id"] = 1
    # def getMetadata(self, request):
    #     return [('POLARIZER_TYPE', str(self.getFilter()), 'Polarizer type')]
        # ('FWHEEL', str(self['filter_wheel_model']), 'FilterWheel Model'),
