import threading
import time
import logging

from chimera.core.event import event
from chimera.core.lock import lock
# from chimera.core.exceptions import ChimeraException, InstrumentBusyException, ChimeraObjectException

from chimera.instruments.filterwheel import FilterWheelBase

from chimera_t80cam.instruments.ebox.fsufilters.filterwheelsdrv import FSUFilterWheel

log = logging.Logger(__name__)


class FsuFilters(FilterWheelBase):
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
        plc_timeout=5)

    def __init__(self):
        """Constructor."""
        FilterWheelBase.__init__(self)
        # Get me the filter wheel.
        self._abort = threading.Event()
        self.fwhl = None

    def __start__(self):
        self.open()

    def __stop__(self):
        self.stopWheel()

    @lock
    def open(self):
        return self.connectTWC()

    def connectTWC(self):
        self.log.debug('Opening Filter Wheel')
        self.fwhl = FSUFilterWheel(self)
        self.log.debug('Current filter is: %s'%self.getFilter())
        return True

    def stopWheel(self):
        self.log.debug('Abort requested')
        self._abort.set()
        self.fwhl.move_stop()

    @lock
    def setFilter(self, flt):
        """
        Set the current filter.

        .. method:: setFilter(flt)
            Sets the filter wheel(s) to the position defined for the filter
            name.
            :param str flt: Name of the filter to use.
        """
        fwhl = self.fwhl

        self._abort.clear()

        if self.getFilter() == flt:
            return

        # print(self._getFilterPosition(flt))
        # Set wheels in motion.
        self.log.debug("QUICK AND DIRTY: Moving to position zero.")
        fwhl.move_pos(0)

        # This call returns immediately, hence loop for an abort request.
        time.sleep(self["waitMoveStart"])
        timeout = 0
        start_time = time.time()
        while not (fwhl.fwheel_is_moving() and
                       fwhl.awheel_is_moving()):
            time.sleep(0.1)
            if self._abort.isSet():
                self.stopWheel()
                break
            if time.time()-start_time > 25:
                self.log.warning("Longer than 25s have passed; something is wrong...")
                # Longer than 25s have passed; something is wrong...
                fwhl.check_hw()

        # print(self._getFilterPosition(flt))
        # Set wheels in motion.
        self.log.debug("QUICK AND DIRTY: Moving to %s." % flt)

        fwhl.move_pos(self._getFilterPosition(flt))
        # This call returns immediately, hence loop for an abort request.
        time.sleep(self["waitMoveStart"])
        timeout = 0
        start_time = time.time()
        while not (fwhl.fwheel_is_moving() and
                       fwhl.awheel_is_moving()):
            time.sleep(0.1)
            if self._abort.isSet():
                self.stopWheel()
                break
            if time.time()-start_time > 25:
                self.log.warning("Longer than 25s have passed; something is wrong...")
                # Longer than 25s have passed; something is wrong...
                fwhl.check_hw()

    def getFilter(self):
        """
        Return the current filter.

        .. method:: getFilter()
            Return the current filter position (by name).
        :return: Current filter.
        :rtype: int.
        """
        fwhl = self.fwhl
        return self._getFilterName(fwhl.get_pos())
