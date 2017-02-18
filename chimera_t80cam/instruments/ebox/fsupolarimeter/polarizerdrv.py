import logging
import time

from chimera_t80cam.instruments.ebox.fsuconn import FSUConn
from chimera_t80cam.instruments.ebox.fsufwheels import FSUFWheels
from chimera_t80cam.instruments.ebox.fsuexceptions import FilterPositionFailure

class FSUPolDriver(FSUConn, FSUFWheels):
    """
        Solunia class to interface with the polarimeter and wave plate
        components.
    """

    def __init__(self, fsu):
        """

        :param fsu:
        :return:
        """
        self.log = fsu.log
        self.timeout = fsu['plc_timeout']

        self.log.debug('Connecting to TwinCat server @ %s:%s'%(fsu['plc_ip_adr'],
                                                               fsu['plc_ip_port']))

        FSUConn.__init__(self, fsu)
        FSUFWheels.__init__(self)

    def setup_wheel(self, wheel):
        """

        :param wheel:
        :return:
        """

        if wheel == 0:
            vread1 = self._vread1
            vread2 = self._vread2
            #get_required_pos = self.get_required_pos_fw
            start_movement_bit = 1
            stop_movement_bit = (1 << 5)
            enable_bit = None
            req_pos = self._wPOS_REQU_T80_POL_BOX_FILTER_WHEEL1
        elif wheel == 1:
            vread1 = self._vread1
            vread2 = self._vread3
            #get_required_pos = self.get_required_pos_aw
            start_movement_bit = 1
            stop_movement_bit = (1 << 5)
            enable_bit = None
            req_pos = self._wPOS_REQU_T80_POL_BOX_FILTER_WHEEL2
        elif wheel == 2:
            vread1 = self._vread10
            vread2 = self._vread12
            #get_required_pos = self.get_required_pos_wp
            start_movement_bit = (1 << 4)
            stop_movement_bit = (1 << 5)
            enable_bit = 1
            req_pos = self._wPOS_REQU_T80_POL_BOX_FILTER
        elif wheel == 3:
            vread1 = self._vread20
            vread2 = self._vread22
            #get_required_pos = self.get_required_pos_pa
            start_movement_bit = (1 << 4)
            stop_movement_bit = (1 << 5)
            enable_bit = 1
            req_pos = self._wPOS_REQU_T80_POL_BOX_WHEEL
        else:
            return None

        return vread1, vread2, start_movement_bit, stop_movement_bit, enable_bit, req_pos

    def move_element(self, filterpos, wheel=0):
        """
        Move specified wheel to the specified position. This function do the setup of the movement, send the start
        movement command and returns. The user should check externaly when the wheel arrives at the specified location
        and if any errors occur.

        :param filterpos:
        :param wheel:
        :return:
        """
        vread1, vread2, start_movement_bit, \
        stop_movement_bit, enable_bit, get_required_pos = self.setup_wheel(wheel)

        self.log.debug('Requested filter position {0} on {1} wheel'.format(filterpos, wheel))
        self.log.debug('VREAD {0}'.format(vread2.read()))

        # Todo: Check wheel for errors

        # Ensure the motion bit is set to zero
        if (vread1.read() & start_movement_bit) != 0:
            vread1.write(vread1.read() ^ start_movement_bit)
        self.log.debug('VREAD {0}'.format(vread1.read()))

        # reset the stop movement request bit if set.
        if (vread1.read() & stop_movement_bit) != 0:
            vread1.write(vread1.read() & ~stop_movement_bit)

        # check if enable bit is set, if not, make sure wheel is enable
        if enable_bit is not None and (vread1.read() & enable_bit) == 0:
            self.log.debug('Enabling wheel')
            vread1.write(enable_bit)

        self.log.debug('VREAD {0}'.format(vread1.read()))

        # Set the filter position vector
        self.log.debug('Setting filter position...')

        # Todo: Check that position is within limits!
        vread2.write(filterpos)
        start_time = time.time()
        # Waiting for position to be set at the wheel controller
        while get_required_pos.read() != filterpos:
            self.log.debug('Filter position on wheel %i: %s/%s' % (wheel, get_required_pos.read(), filterpos))
            if time.time()-start_time > self.timeout:
                raise FilterPositionFailure("Could not set filter position.")
            # Todo: Check for errors
            time.sleep(0.5)
        self.log.debug('Filter position: %s/%s' % (get_required_pos.read(), filterpos))

        # Move it
        vread1.write(self._vread1.read() ^ start_movement_bit)
        self.log.debug('VREAD1 {0}'.format(vread1.read()))

        # End of function. Will not wait for movement to complete! This just starts the movement!

    def get_pos(self, wheel=0):
        """
        Get current filter position.


        :param wheel:
        :return:
        """
        vread1 = self.setup_wheel(wheel)

        return vread1[1].read()

    def __getitem__(self, item):
        """

        :param item:
        :return:
        """
        wheels = [self.move_filter_wheel,
                  self.move_analyser_wheel,
                  self.move_wave_plate,
                  self.move_polarimeter_analyser]

        return wheels[item]

    def move_filter_wheel(self, filterpos):
        """

        :param filterpos:
        :return:
        """
        return self.move_element(filterpos=filterpos,
                                 wheel=0)

    def move_analyser_wheel(self, filterpos):
        """

        :param filterpos:
        :return:
        """
        return self.move_element(filterpos=filterpos,
                                 wheel=1)

    def move_wave_plate(self, filterpos):
        """

        :param filterpos:
        :return:
        """
        return self.move_element(filterpos=filterpos,
                                 wheel=2)

    def move_polarimeter_analyser(self, filterpos):
        """

        :param filterpos:
        :return:
        """
        return self.move_element(filterpos=filterpos,
                                 wheel=3)

    def wp_position_reached(self):
        return (self._vwrite10.read() & (1 << 2)) == 0

    def pa_position_reached(self):
        return self._vwrite20.read() & (1 << 2) != 0

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
            self._vread10.write(self._vread10.read() | (1 << 2))
            self._vread10.write(self._vread10.read() & ~(1 << 1))
        elif mode is '-':
            self._vread10.write(self._vread10.read() | (1 << 3))
            self._vread10.write(self._vread10.read() & ~(1 << 1))
        else:  # mode not in ('+', '-')
            # log.error("Invalid option; must be '+' or '-'")
            print("Invalid option; must be '+' or '-'")
            return None

    def stop_polarizer(self):
        if (self._vread20.read() & (1 << 5)) != 0: # if stop is already set, unset it
            self._vread20.write(self._vread20.read() ^ (1 << 5))
        self._vread20.write(self._vread20.read() ^ (1 << 5))

    def stop_wave_plate(self):
        # log.info("Wave plate stop request received")
        if (self._vread10.read() & (1 << 5)) != 0: # if stop is already set, unset it
            self._vread10.write(self._vread10.read() ^ (1 << 5))
        self._vread10.write(self._vread10.read() ^ (1 << 5))

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
