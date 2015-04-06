import logging
import time

from chimera.instruments.ebox.fsufwheels import FSUFWheels

log = logging.getLogger(name=__name__)


class FSUPolDriver(FSUFWheels):
    """
        Solunia class to interface with the polarimeter and wave plate
        components.
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
        # self._vread21.write(self._vread21.read() | (1 << 0))
        # time.sleep(0.1)
        # continue
        # log.info('Polarimeter wheel homed')
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
        if not (self._vwrite20.read() & (1 << 3) and
                    log.warning('homing polarimeter wheel')):
            # Not homed, start homing
            # TODO: timeout?
            self._vread21.write(self._vread21.read() | (1 << 0))
            while not self._vread20.read() & (1 << 3):
                time.sleep(0.1)
            log.info('Polarimeter wheel homed')
        else:
            # already homed, cool
            log.info('Polarimeter wheel homed')

    def get_pwheel_pos(self):
        """
        Return polarimeter wheel position.
        :return: polarimeter wheel reference position.
        :rtype : int
        """
        return self._vread22.read()

    def get_plate_pos(self):
        """
        Return wave plate position.
        :return: wave plate current position.
        """
        return self._vread12.read()

    def move_pwheel_pos(self, whlpos):
        """
        Move the polarimeter to the requested position.
        :param int whlpos:
            Moves both wheels to the compound position requested.
        """
        # Set the position to move to (1 -> 17).
        time.sleep(0.1)
        log.info("Requested polarimeter position {}".format(whlpos))
        # Ensure the motion bit is set to zero
        if (self._vread20.read() & (1 << 4)) != 0:
            self._vread20.write(self._vread1.read() ^ (1 << 4))
        # reset the stop movement request bit if set.
        if (self._vread20.read() & (1 << 5)) != 0:
            self._vread20.write(self._vread20.read() & ~(1 << 5))
        # Set the filter position vector
        self._vread22.write(whlpos)
        while self._wPOS_REQ.read() != whlpos:
            time.sleep(0.1)
        # Move it
        self._vread20.write(self._vread20.read() ^ (1 << 4))
        return

    def move_plate_pos(self, plpos):
        """
        Move the wave plate to the requested position.
        :type plpos: int
        """
        time.sleep(0.1)
        log.info("Requested wave plate position {}".format(plpos))
        # Motion bit to 0
        if (self._vread10.read() & (1 << 4)) != 0:
            self._vread10.write(self._vread10.read() ^ (1 << 4))
        # Stop motion request bit
        if (self._vread10.read() & (1 << 5)) != 0:
            self._vread10.write(self._vread10.read() & ~(1 << 5))
        # Set position
        self._vread12.write(plpos)
        # Move
        self._vread10.write(self._vread10.read() ^ (1 << 4))

    def jog_pwheel(self, mode):
        """
        Jog the polarimeter in '+' or '-' direction
        :param mode: Jog direction
        :type mode: str
        :return:
        """
        # Validate mode
        if mode is '+':
            self._vread20.write(self._vread20.read() | (1 << 2))
        elif mode is '-':
            self._vread20.write(self._vread20.read() | (1 << 3))
        else:  # mode not in ('+', '-')
            log.error("Invalid option; must be '+' or '-'")
            return None

    def jog_plate(self, mode):
        """
        Jog the wave plate in the specified direction.

        :param mode: jog direction
        :type mode: object
        :return:
        """
        # Validate mode
        if mode is '+':
            self._vread10.write(self._vread10.read() | (1 << 2))
        elif mode is '-':
            self._vread10.write(self._vread10.read() | (1 << 3))
        else:  # mode not in ('+', '-')
            log.error("Invalid option; must be '+' or '-'")
            return None

    def stop_pwheel(self):
        """
        Stop polarimeter motion.
            Aborts any current rotation of the polarimeter.
        """
        time.sleep(0.1)
        print('Stop request received')
        # Check if polarimeter already stopped
        if ((self._vwrite20.read() & (1 << 2) != 0) and
                (self._vwrite20.read() & (1 << 3) != 0)):
            log.warn("Wheels already stopped.")
        else:
            # This is accomplished by flipping bit 5
            self._vread1.write(self._vread1.read() | (1 << 5))
            log.info('Filter wheels stopped')

    def stop_plate(self):
        """
        Stop wave plate motion.
        """
        log.info("Wave plate stop request received")
        # Already stopped?
        if (self._vread10.read() & (1 << 4)) != 0:
            log.info("Wave plate already stopped")
        else:
            self._vread10.write(self._vread10.read() | (1 << 5))

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
        pol_errs = ('polarimeter: step motor enabled',
                    'polarimeter: step motor error',
                    'polarimeter: position reached',
                    'polarimeter: homed',
                    'polarimeter: encoder disconnected or inverted',
                    'polarimeter: motor disconnected')
        wpl_errs = ('wave plate: enabled',
                    'wave plate: error',
                    'wave plate: position reached',
                    'wave plate: homed',
                    'wave plate: encoder disconnected or inverted',
                    'wave plate: motor disconnected'
                    )
        # Let's start
        for statbit in range(0, 5):
            if (self._vwrite10.read() & (1 << statbit)) != 0:
                print pol_errs[statbit]
        for statbit in range(0, 5):
            if (self._vwrite10.read() & (1 << statbit)) != 0:
                print wpl_errs[statbit]
