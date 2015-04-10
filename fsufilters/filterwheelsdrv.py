import logging
import time

from chimera.instruments.ebox.fsuconn import FSUConn
from chimera.instruments.ebox.fsufwheels import FSUFWheels


log = logging.getLogger(name=__name__)


class FSUFilterWheel(FSUConn, FSUFWheels):
    """
    Solunia class to interface with the filter wheels component.
    """

    def __init__(self):
        FSUConn.__init__(self)
        FSUFWheels.__init__(self)
        """
        Initialize object from Chimera.
        """

    def move_pos(self, filterpos):
        # log.info('Requested filter position {0}'.format(filterpos))
        # Ensure the motion bit is set to zero
        if (self._vread1.read() & 1) != 0:
            self._vread1.write(self._vread1.read() ^ 1)
        # reset the stop movement request bit if set.
        if (self._vread1.read() & (1 << 5)) != 0:
            self._vread1.write(self._vread1.read() & ~(1 << 5))
        # Set the filter position vector
        self._vread0.write(filterpos)
        while self.get_req_pos() != filterpos:
            time.sleep(0.1)
        # Move it
        self._vread1.write(self._vread1.read() ^ 1)
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

    def check_hw(self):
        vec_msgs0 = ('Filter wheel: position timeout',
                     'Analyser wheel: position timeout',
                     'Shutter: error',
                     'Shutter: opened',
                     'Filter wheel encoder: disconnected or inverted',
                     'Analyser wheel encoder: disconnected or inverted',
                     'Filter wheel: motor disconnected',
                     'Analyser wheel: motor disconnected'
                     )
        vec_msgs1 = ('Filter wheel: motor inverted',
                     'Analyser wheel: motor inverted',
                     'Filter wheel: position reached',
                     'Analyser wheel: position reached',
                     'Filter wheel: error flag',
                     'Analyser wheel: error flag',
                     '',
                     ''
                     )
        for statbit in range(0, 8):
            if (self._vwrite0.read() & (1 << statbit)) == 1:
                print vec_msgs0[statbit]
        for statbit in range(0, 8):
            if (self._vwrite1.read() & (1 << statbit)) == 1:
                print vec_msgs1[statbit]
        # for statbit in range(0, 8):
        #     if (self._vwrite10.read() & (1 << statbit)) == 1:
        #         print vec_msgs10[statbit]
        # Now take care of the full reg values : 12, 13
        # for idx in [12, 13]:
        # print('Function blk M3 servo (wplate) error number: {0}'.format(
        #     self._vwrite12.read()))
        # print('Function blk M3 servo axis (wplate)error number: {0}'.format(
        #     self._vwrite13.read()))
