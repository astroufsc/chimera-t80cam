import logging
import time

from chimera_t80cam.instruments.ebox.fsuconn import FSUConn
from chimera_t80cam.instruments.ebox.fsufwheels import FSUFWheels
from chimera_t80cam.instruments.ebox.fsuexceptions import FilterPositionFailure

log = logging.getLogger(name=__name__.replace('chimera_t80cam','chimera'))

class FSUFilterWheel(FSUConn, FSUFWheels):
    """
    Solunia class to interface with the filter wheels component.
    """

    def __init__(self, fsu):
        """
        Initialize object from Chimera.

        :param fsu:
        :return:
        """
        log.debug('Connecting to TwinCat server @ %s:%s'%(fsu['plc_ip_adr'],
                                                          fsu['plc_ip_port']))
        self.log = fsu.log
        self.timeout = fsu['plc_timeout']
        FSUConn.__init__(self, fsu)
        FSUFWheels.__init__(self)

    def move_pos(self, filterpos):
        self.log.debug('Requested filter position {0}'.format(filterpos))
        self.log.debug('VREAD {0}'.format(self._vread1.read()))
        # Ensure the motion bit is set to zero
        if (self._vread1.read() & 1) != 0:
            self._vread1.write(self._vread1.read() ^ 1)
        self.log.debug('VREAD {0}'.format(self._vread1.read()))

        # reset the stop movement request bit if set.
        if (self._vread1.read() & (1 << 5)) != 0:
            self._vread1.write(self._vread1.read() & ~(1 << 5))
        # Set the filter position vector
        self.log.debug('Seeting filter position...')
        self._vread0.write(filterpos)
        start_time = time.time()
        while self.get_req_pos() != filterpos:
            self.log.debug('Filter position: %s/%s/%s'%(self.get_req_pos(), filterpos,self._vread0.read()))
            if time.time()-start_time > self.timeout:
                raise FilterPositionFailure("Could not set filter position.")
            time.sleep(0.1)
        self.log.debug('Filter position: %s/%s/%s'%(self.get_req_pos(), filterpos,self._vread0.read()))
        # Move it
        self._vread1.write(self._vread1.read() ^ 1)
        self.log.debug('VREAD1 {0}'.format(self._vread1.read()))

        return

    def fwheel_is_moving(self):
        """
        Return status of filter wheel.
        :return: True if moving, False otherwise.
        """
        # vwrite1.2 flags filter wheel pos reached status,
        return self._vwrite1.read() & (1 << 2) != 0

    def awheel_is_moving(self):
        """
        Return status of filter wheel.
        :return: True if moving, False otherwise.
        """
        # vwrite1.3 flags analiser wheel pos reached status.
        return self._vwrite1.read() & (1 << 3) != 0

    def move_stop(self):
        """
        Stop all filter wheels motion.

        .. method:: move_stop()
            Aborts any current rotation of all filter wheels.
        """
        print('Stop request received')
        # Check if wheels already stopped
        if ((self._vwrite1.read() & (1 << 2) != 0) and
                (self._vwrite1.read() & (1 << 3) != 0)):
            log.warn("Wheels already stopped.")
        else:
            # This is accomplished by flipping bit 5
            self._vread1.write(self._vread1.read() | (1 << 5))
            log.info('Filter wheels stopped')
            # TODO: integrate the bPOS bit status.

    def get_pos(self):
        """
        Get current filter position.

        .. method:: get_pos()
            Returns the current filter by
            :return: filter position.
            :rtype: int.
        """
        blonks = self._vread0.read()
        return blonks

    def get_req_pos(self):
        """
        Get requested position.
        """
        return self._wPOS_REQ.read()

    def set_home_position_wheel(self, wheel1, wheel2):

        # Check if wheel is on position or homing mode
        if not self._bFILTER_1_AND_2_HOME_MODE.read():
            # If bit is set, unset it
            if (self._vread1.read() & (1<<2)) != 0:
                self._vread1.write(self._vread1.read() ^ (1 << 2))

            # Request to switch to homing mode
            self._vread1.write(self._vread1.read() ^ (1 << 2))

            start_time = time.time()
            while not self._bFILTER_1_AND_2_HOME_MODE.read():
                if time.time()-start_time > self.timeout:
                    raise FilterPositionFailure("Could not switch to homing mode!")
                time.sleep(0.1)
                # wait for mode switch
        # Set home positions
        self._rlREAL_READ2.write(float(wheel1))  # make sure wheel1 is a float!
        self._rlREAL_READ3.write(float(wheel2))  # make sure wheel2 is a float!
        # If bit is set, unset it
        if (self._vread1.read() & (1 << 3)) != 0:
            self._vread1.write(self._vread1.read() ^ (1 << 3))
        self._vread1.write(self._vread1.read() ^ (1 << 3))  # Send command to set position

        # wait for PLC to acquire values
        start_time = time.time()
        while self._lrINITIAL_ANGLE_POS_M1.read() != float(wheel1) and \
                        self._lrINITIAL_ANGLE_POS_M2.read() != float(wheel2):
            if time.time()-start_time > self.timeout:
                raise FilterPositionFailure("Could not set homing positions! Tried to set "
                                            "%f/%f PLC values are %f/%f" % (float(wheel1),
                                                                            float(wheel2),
                                                                            self._lrINITIAL_ANGLE_POS_M1.read(),
                                                                            self._lrINITIAL_ANGLE_POS_M2.read()))
            time.sleep(0.1)

        self._vread1.write(self._vread1.read() ^ (1 << 3))  # Unset command to set position
        self._vread1.write(self._vread1.read() ^ (1 << 2))  # Go back to position mode



    def check_hw(self):
        log.debug('Checking filter wheel!')
        return True