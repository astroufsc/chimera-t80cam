import logging
import time

from adshli.hli import ads_var_single
from chimera.instruments.fsu.fsuconn import FSUConn

log = logging.getLogger(name=__name__)


class FSUPolarizer(FSUConn):

    """
        Solunia class to interface with the polarizer wheel component.
    """

    def __init__(self):
        """
        Class constructor.
        """
        FSUConn.__init__(self)
        # Useful variables
        # All ok, get current ADS vectors' state
        # Polarizer control vectors, bits 0 to 5 and 0 to 1
        self._vread20 = ads_var_single(self.conn, '.wDWORD_READ[20]', 'i')
        self._vread21 = ads_var_single(self.conn, '.wDWORD_READ[21]', 'i')
        # Polarizer position vector.
        self._vread22 = ads_var_single(self.conn, '.wDWORD_READ[22]', 'i')
        # Polarizer status vector
        self._vwrite20 = ads_var_single(self.conn, '.wDWORD_WRITE[20]', 'i')

    def __start__(self):
        """
        Chimera initialization of the object.
        """
        # Reset error flag: vec20 bit1 -> 0.
        self._vread20.write(self._vread20.read() | (1 << 1))
        # "Enable" the polarizer (?); vec20 bit0 -> 1. This powers on the M4
        # axis motor.
        self._vread20.write(self._vread20.read() | (1 << 0))

    def get_pos(self):
        """
        Return polarizer position.
        """
        return self._vread22.read()

    def move_pos(self, pos):
        """
        Move the polarizer to passed position.
        .. method:: move_pos(pos)
            Moves both wheels to the compound position requested.
            .. param int pos:: requested position, values 1 - 17.
        """
        # Set mode bit to "position" as opposed to "coordinate" (?? Check!)
        # That is set vec20 bit4 -> 0
        self._vread20.write(self._vread20.read() & ~(1 << 3))
        # ...and now set the position to move to.
        self._vread22.write(pos)
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
        # .wDWORD_WRITE[20] bit 0: polarizer step motor enabled flag
        # .wDWORD_WRITE[20] bit 1: polarizer step motor error flag
        # .wDWORD_WRITE[20] bit 2: polarizer position reached flag
        # .wDWORD_WRITE[20] bit 3: polarizer homed flag
        # .wDWORD_WRITE[20] bit 4: polarizer encoder disconnected or inverted
        # .wDWORD_WRITE[20] bit 5: polarizer motor disconnected flag
        #
        # .wDWORD_WRITE[21]: error number of the function block M4 servomotor
        # .wDWORD_WRITE[22]: error number for the axis M4 servomotor

        # self._vwrite20 is the one
        errors = ('Polarizer: step motor enabled',
                  'Polarizer: step motor error',
                  'Polarizer: position reached',
                  'Polarizer: homed',
                  'Polarizer: encoder disconnected or inverted',
                  'Polarizer: motor disconnected')
        # self.pd_regs = ads_var_group()
        # for idx in [20]:
        #     self.pd_regs.add_variable(
        #         self, '.wDWORD_WRITE[{0}]'.format(str(idx)), 'i')
        # self._vwrite20.connect(self.conn)
        # self._vwrite20.read()
        # as of here, we should have all the status vectors loaded into
        # d_regs.plc_variables...
        # Let's start
        for statbit in range(0, 5):
            if (self._vwrite20.read() & (1 << statbit)) != 0:
                print errors[statbit]
