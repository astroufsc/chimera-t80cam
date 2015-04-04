import logging
import time

# from chimera.instruments.ebox.fsuconn import FSUConn
from chimera.instruments.ebox.fsufwheels import FSUFWheels

log = logging.getLogger(name=__name__)


class FSUPolDriver(FSUFWheels):
    """
        Solunia class to interface with the polarimeter component.
    """

    def __init__(self):
        """
        Class constructor.
        """
        FSUFWheels.__init__(self)
        #
        # Initialize vectors
        #
        # Reset error flag: vec20 bit1 -> 0.
        self._vread20.write(self._vread20.read() | (1 << 1))
        # "Enable" the polarimeter (?); vec20 bit0 -> 1. This powers on the M4
        # axis motor.
        self._vread20.write(self._vread20.read() | (1 << 0))
        # Set mode bit to "position" as opposed to "coordinate".
        self._vread21.write(self._vread20.read() & ~(1 << 1))
        #
        # Homing procedures.
        #
        # Polarimeter homed: vec20bit3
        # try:
        # self._vwrite20.read() & (1 << 3) and
        # log.info('Polarimeter wheel homed')
        # except:
        # log.warning('homing polarimeter wheel')
        # while not self._vread20.read() & (1 << 3):
        #         self._vread21.write(self._vread21.read() | (1 << 0))
        #         time.sleep(0.1)
        #         continue
        #     log.info('Polarimeter wheel homed')
        ########################################################
        # Reverse logic
        # try:
        #     not self._vwrite20.read() & (1 << 3) and
        #     log.warning('homing polarimeter wheel')
        #     # Not homed, start homing
        #     self._vread21.write(self._vread21.read() | (1 << 0))
        #     while not self._vread20.read() & (1 << 3):
        #         time.sleep(0.1)
        #         continue
        #     log.info('Polarimeter wheel homed')
        # except:  # already homed, cool
        # log.info('Polarimeter wheel homed')
        # TODO: see above, define an exception that can be raised to warn via console and trigger the except clause.
        if not self._vwrite20.read() & (1 << 3) and \
                log.warning('homing polarimeter wheel'):
            # Not homed, start homing
            # TODO: timeout?
            self._vread21.write(self._vread21.read() | (1 << 0))
            while not self._vread20.read() & (1 << 3):
                time.sleep(0.1)
            log.info('Polarimeter wheel homed')
        else:
            # already homed, cool
            log.info('Polarimeter wheel homed')


def get_pos(self):
    """
    Return polarimeter position.
    """
    return self._vread22.read()


def move_pos(self, pos):
    """
    Move the polarimeter to passed position.
    .. method:: move_pos(pos)
        Moves both wheels to the compound position requested.
        .. param int pos:: requested position, values 1 - 17.
    """
    # Set the position to move to (1 -> 17).
    self._vread22.write(pos)
    time.sleep(0.1)
    # Enter wait loop...
    while (self._vwrite20.read() & (1 << 1) == 0):
        time.sleep(0.5)
        continue
        # TODO: there should be a timeout here in case pos is never reached...
        # and a check on the status vector for specific errors.


def move_stop(self):
    """
    Abruptly stop any motion.
    """
    # Vector 20 bit5 0 -> 1.
    self._vread20.write(self._vread20.read() | (1 << 4))
    # How  to check if it's moving or not?


def check_hw(self):
    # .wDWORD_WRITE[20] bit 0: polarimeter step motor enabled flag
    # .wDWORD_WRITE[20] bit 1: polarimeter step motor error flag
    # .wDWORD_WRITE[20] bit 2: polarimeter position reached flag
    # .wDWORD_WRITE[20] bit 3: polarimeter homed flag
    # .wDWORD_WRITE[20] bit 4: polarimeter encoder disconnected or inverted
    # .wDWORD_WRITE[20] bit 5: polarimeter motor disconnected flag
    #
    # .wDWORD_WRITE[21]: error number of the function block M4 servomotor
    # .wDWORD_WRITE[22]: error number for the axis M4 servomotor
    #
    # self._vwrite20 is the one
    errors = ('polarimeter: step motor enabled',
              'polarimeter: step motor error',
              'polarimeter: position reached',
              'polarimeter: homed',
              'polarimeter: encoder disconnected or inverted',
              'polarimeter: motor disconnected')
    # Let's start
    for statbit in range(0, 5):
        if (self._vwrite20.read() & (1 << statbit)) != 0:
            print errors[statbit]
