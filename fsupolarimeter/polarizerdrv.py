import logging
import time

from chimera.instruments.ebox.fsuconn import FSUConn
from chimera.instruments.ebox.fsufwheels import FSUFWheels

log = logging.getLogger(__name__)


class FSUPolDriver(FSUConn, FSUFWheels):
    """
        Solunia class to interface with the polarimeter and wave plate
        components.
    """

    def __init__(self):
        """
        Class constructor.
        """
        FSUConn.__init__(self)
        FSUFWheels.__init__(self)

        self._vread20.write(self._vread20.read() | (1 << 0))
        self._vread10.write(self._vread10.read() | (1 << 0))
        self._vread21.write(self._vread21.read() & ~(1 << 0))
        self._vread11.write(self._vread11.read() & ~(1 << 0))

    def get_calpol_pos(self):
        return self._vread22.read()

    def get_wplate_pos(self):
        return self._vread12.read()

    def move_calpol_pos(self, clpos):
        self._vread20.write(self._vread20.read() & ~(1 << 4))
        self._vread22.write(clpos)
        # Time to acknowledge request
        # while self._wPOS_REQ.read() != whlpos:
        #     time.sleep(0.1)
        # Move it: bit 4 to 1
        print(bin(self._vread20.read()))
        raw_input('ok?')
        # Move
        self._vread20.write(self._vread20.read() & ~(1 << 1))
        self._vread20.write(self._vread20.read() | (1 << 4))
        while self._vwrite20.read() & (1 << 2) != 0:
            time.sleep(1.0)
            # TODO: timeout
        return

    def move_wplate_pos(self, plpos):
        self._vread10.write(self._vread10.read() & ~(1 << 4))
        self._vread12.write(plpos)
        # print(bin(self._vread10.read()))
        self._vread10.write(self._vread10.read() & ~(1 << 1))
        self._vread10.write(self._vread10.read() | (1 << 4))
        # print(bin(self._vread10.read()))
        while self._vwrite10.read() & (1 << 2) != 0:
            time.sleep(1.1)
            # TODO: timeout
        return

    def fwheel_is_moving(self):
        return self._vwrite20.read() & (1 << 2) != 0

    def awheel_is_moving(self):
        return self._vwrite1.read() & (1 << 3) != 0

    def jog_calpol(self, mode):
        if mode is '+':
            self._vread20.write(self._vread20.read() | (1 << 2))
        elif mode is '-':
            self._vread20.write(self._vread20.read() | (1 << 3))
        else:  # mode not in ('+', '-')
            # log.error("Invalid option; must be '+' or '-'")
            print("Invalid option; must be '+' or '-'")
            return None

    def jog_wplate(self, mode):
        if mode is '+':
            self._vread10.write(self._vread10.read() & ~(1 << 1))
            self._vread10.write(self._vread10.read() | (1 << 2))
        elif mode is '-':
            self._vread10.write(self._vread10.read() & ~(1 << 1))
            self._vread10.write(self._vread10.read() | (1 << 3))
        else:  # mode not in ('+', '-')
            # log.error("Invalid option; must be '+' or '-'")
            print("Invalid option; must be '+' or '-'")
            return None

    def stop_calpol(self):
        print('Stop request received')
        if ((self._vwrite20.read() & (1 << 2) != 0) and
                (self._vwrite20.read() & (1 << 3) != 0)):
            # log.warn("Wheels already stopped.")
            print("Wheels already stopped.")
        else:
            self._vread1.write(self._vread1.read() | (1 << 5))
            # log.info('Filter wheels stopped')
            print('Filter wheels stopped')

    def stop_wplate(self):
        # log.info("Wave plate stop request received")
        if (self._vread10.read() & (1 << 4)) != 0:
            # log.info("Wave plate already stopped")
            print("Wave plate already stopped")
        else:
            self._vread10.write(self._vread10.read() | (1 << 5))

    def check_hw(self):
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

    def reset_wplate(self):
        # Panic button!
        self._vread10.write(self._vread10.read() | (1 << 1))

    def reset_calpol(self):
        self._vread20.write(self._vread20.read() | (1 << 1))
