import threading
import time
import logging
import threading

from chimera.core.event import event
from chimera.core.lock import lock

from chimera.instruments.filterwheel import FilterWheelBase

from chimera.instruments.ebox.fsupolarimeter.polarizerdrv import FSUPolDriver

log = logging.Logger(__name__)


class FsuPolarimeter(FilterWheelBase):
    """
    High level class for the Solunia ebox fit with both filter wheels.
    """

    __config__ = dict(
        filter_wheel_model="Solunia",
        waitMoveStart=0.5
    )

    def __init__(self):
        """Constructor."""
        FilterWheelBase.__init__(self)
        # Get me the polarizer wheel.
        self.pwhl = FSUPolDriver()
        self._abort = threading.Event()
        print("Filter wheels acquired")

    def __stop__(self):
        self.stopWheel()

    def stopWheel(self):
        print('Abort requested')
        self._abort.set()
        # self.fwhl.move_stop()

    @lock
    def setFilter(self, filter):
        """
        Set the current filter.

        .. method:: setFilter(filter)
            Sets the filter wheel(s) to the position defined for the filter
            name.
            :param str filter: Name of the filter to use.
        """
        self._abort.clear()
        print(self._getFilterPosition(filter))
        # Set wheels in motion.
        self.fwhl.move_pos(self._getFilterPosition(filter))
        # This call returns immediately, hence loop for an abort request.
        time.sleep(self["waitMoveStart"])
        timeout = 0
        while not (self.fwhl.fwheel_is_moving() and
                       self.fwhl.awheel_is_moving()):
            time.sleep(0.1)
            if self._abort.isSet():
                break
            if timeout > 250:
                # Longer than 25s have passed; something is wrong...
                self.fwhl.check_hw()

    def getFilter(self):
        """
        Return the current filter.

        .. method:: getFilter()
            Return the current filter position (by name).
        :return: Current filter.
        :rtype: int.
        """
        return self._getFilterName(self.fwhl.get_pos())

    @event
    def filterChange(self, newFilter, oldFilter):
        """
        Fired when the wheel changes the current filter.

        @param newFilter: The new current filter.
        @type  newFilter: str

        @param oldFilter: The last filter.
        @type  oldFilter: str
        """

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
        return [("FWHEEL", self['filter_wheel_model'], 'Filter Wheel Model'),
                ("FILTER", self.getFilter(), 'Filter for this observation')]
