import threading
import time
import logging
import itertools
# from chimera.core.event import event
from chimera.core.lock import lock

from chimera.instruments.filterwheel import FilterWheelBase
from chimera_t80cam.instruments.ebox.fsuexceptions import FilterPositionFailure, FSUInitializationException
from chimera_t80cam.instruments.ebox.fsupolarimeter.polarizerdrv import FSUPolDriver

log = logging.Logger(__name__)


class FsuPolarimeter(FilterWheelBase):
    """
    High level class for the Solunia ebox fit with both filter wheels.
    """

    __config__ = dict(
        filter_wheel_model="Solunia",
        waitMoveStart=0.5,
        plc_ams_id="5.18.26.30.1.1",
        plc_ams_port=801,
        plc_ip_adr="192.168.100.1",
        plc_ip_port=48898,
        pc_ams_id="5.18.26.31.1.1",
        pc_ams_port=32788,
        plc_timeout=5,
        device=None)

    def __init__(self):
        """Constructor."""
        FilterWheelBase.__init__(self)
        # Get me the filter wheel.
        self._abort = threading.Event()
        self.fwhl = None

    def __start__(self):
        self.open()
        self._wheels = [self.getManager().getProxy(wheel, lazy=True) for wheel in self["device"].split(',')]
        for wheel in self._wheels:
            wheel.fwhl = self.fwhl
        filters = [wheel["filters"].split() for wheel in self._wheels]
        self["filters"] = ' '.join([','.join(comb) for comb in itertools.product(*filters)])


    def __stop__(self):
        self.stopWheel()

    @lock
    def open(self):
        return self.connectTWC()

    def setFilter(self, filters):
        f = filters.split(',')
        for wheel_num in range(self.nwheels):
            # Todo: Check that filter is in the list
            self._wheels[wheel_num].setFilter(f[wheel_num])
        return True

    def getFilter(self):
        filters = ""
        for wheel_num, wheel in enumerate(self._wheels):
            filters += "," + self._wheels[wheel_num].getFilter()
        return filters[1:]

    def connectTWC(self):
        self.log.debug('Opening Filter Wheel')
        self.fwhl = FSUPolDriver(self)
        return True

    def getMetadata(self, request):
        """
        Return info for image headers.

        .. method:: getMetadata(request)
            Collects information to go into the image being exposed with the
            current settings,
            :param dict request: the image request passed down.
            :return: list of tuples, key-value pairs.
        """
        # NOTE: "FWHEEL" is not in the header keywords list on
        # UPAD-ICD-OAJ-9400-2 v. 9
        # return [("FWHEEL", self['filter_wheel_model'], 'Filter Wheel Model'),
        # ("FILTER", self.getFilter(), 'Filter for this observation')]
        pass

class PolarimeterWheelBase(FilterWheelBase):
    def __init__(self):
        FilterWheelBase.__init__(self)
        self.fwhl = None
        self["id"] = 0

    def setFilter(self, flt):

        fwhl = self.fwhl
        if fwhl is None:
            raise FSUInitializationException("Polarimeter wheel not properly initialized.")

        self._abort.clear()

        if self.getFilter() == flt:
            return

        self.log.debug("Moving to filter %s." % flt)

        fwhl[self['id']](self._getFilterPosition(flt))
        # This call returns immediately, hence a loop for an abort request.
        timeout = 0
        start_time = time.time()
        while self.getFilter() != flt:
            if self._abort.isSet():
                self.stopWheel()
                break
            if time.time()-start_time > 25:
                self.log.warning("Longer than 25s have passed; something is wrong...")
                # Todo: Check wheel for errors
                fwhl.check_hw()
                raise FilterPositionFailure('Positioning filter timed-out! Check Filter Wheel!')
            time.sleep(0.1)



class FSUPolarimeterFilterWheel(PolarimeterWheelBase):
    def __init__(self):
        PolarimeterWheelBase.__init__(self)
        self["device"] = None
        self['filter_wheel_model'] = "Fake Polarimeter Filter Wheel"
        self["filters"] = "CLEAR B V R I"

    # def getMetadata(self, request):
    #     return [('FILTER', str(self.getFilter()), 'Filter used for this observation')]
        # ('FWHEEL', str(self['filter_wheel_model']), 'FilterWheel Model'),


class FSUPolarimeterAnalyzerWheel(PolarimeterWheelBase):
    def __init__(self):
        PolarimeterWheelBase.__init__(self)
        self["device"] = None
        self['filter_wheel_model'] = "Fake Polarimeter Analyzer Wheel"
        self["filters"] = "CLEAR CALCITE VIS RED"

    # def getMetadata(self, request):
    #     return [('POLARIZER_TYPE', str(self.getFilter()), 'Polarizer type')]
        # ('FWHEEL', str(self['filter_wheel_model']), 'FilterWheel Model'),


class FSUPolarimeterWavePlate(PolarimeterWheelBase):
    def __init__(self):
        PolarimeterWheelBase.__init__(self)
        self["device"] = None
        self['filter_wheel_model'] = "Fake Polarimeter Wave Plate Wheel"
        self["filters"] = "0.0 22.5 45.0 67.5 90.0 112.5 135.0 157.5 180.0 202.5 225.0 247.5 270.0 292.5 315.0 337.5"

    # def getMetadata(self, request):
    #     return [('HWAVE_PLATE', str(self.getFilter()), 'Wave Plate position')]
        # ('FWHEEL', str(self['filter_wheel_model']), 'FilterWheel Model'),


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