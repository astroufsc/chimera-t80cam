import threading
import time
import logging
import socket

from chimera.core.event import event
from chimera.core.lock import lock

from chimera_t80cam.instruments.ebox.fsuexceptions import FilterPositionFailure, FSUException
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
        move_filter_timeout=25,
        plc_ams_id="5.18.26.30.1.1",
        plc_ams_port=801,
        plc_ip_adr="192.168.100.1",
        plc_ip_port=48898,
        pc_ams_id="5.18.26.31.1.1",
        pc_ams_port=32788,
        plc_timeout=5,
        wheel1_home = 0.,
        wheel2_home = 0.)

    def __init__(self):
        """Constructor."""
        FilterWheelBase.__init__(self)
        # Get me the filter wheel.
        self._abort = threading.Event()
        self.fwhl = None

    def __start__(self):
        self.open()
        self.set_home_position()

    def __stop__(self):
        self.stopWheel()

    def control(self):
        self.log.debug("[control] Checking filter wheel.")
        try:
            msg = ""
            check = self.fwhl.check_hw()
            for item in check:
                self.log.error('%s error flag is set' % item['flag'])
        except socket.timeout:
            self.log.warning('Communication timed-out. Trying to reconnect...')
            self.connectTWC()
            self.set_home_position()
        except Exception, e:
            self.log.exception(e)

        return True

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

        current_filter = self.getFilter()
        if current_filter == flt:
            return

        self.log.debug("Moving to filter %s." % flt)

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
            if time.time()-start_time > self["move_filter_timeout"]:
                # Todo: Check wheel for errors
                fwhl.check_hw()
                raise FilterPositionFailure('Positioning filter timed-out! Check Filter Wheel!')

        self.filterChange(flt, current_filter)

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

    def set_home_position(self):
        '''
        Set home position.
        :return:
        '''

        self.log.debug('Set home position: %f/%f' % (self["wheel1_home"],
                                                     self["wheel2_home"]))

        self.fwhl.set_home_position_wheel(self["wheel1_home"],
                                          self["wheel2_home"])
