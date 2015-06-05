import re
import xml.etree.ElementTree as ETree

import numpy as N
from astropy.io.fits import Header

from si.client import SIClient, AckException
from si.commands.camera import *

from chimera.interfaces.camera import (CCD, CameraFeature, ReadoutMode,
                                       InvalidReadoutMode, CameraStatus,
                                       Shutter)

from chimera.util.image import ImageUtil
from chimera.instruments.camera import CameraBase
from chimera.util.enum import Enum
from chimera.core.lock import lock
from chimera.core.exceptions import ChimeraException

from collections import defaultdict
from itertools import count

import datetime as dt
import time

ImgType = Enum("U16", "I16", "U32", "I32", "SGL", "DBL")


class SIException(ChimeraException):
    pass


class SIBase(CameraBase, object):
    """
    Spectral Instruments Base camera class. Defines functions to control the
    camera alone. This can be used as base class for cameras with different
    filterwheels, etc.

    Author: Tiago Ribeiro
    Date: April/2015
    """

    __config__ = {'device': 'ethernet', 'ccd': CCD.IMAGING, 'temp_delta': 2.0,
                  'camera_model': 'Spectral Instruments 1110 SN 105',
                  'ccd_model': 'e2V CCD 290-99',
                  'camera_host': '192.168.0.117', 'camera_port': 2055}

    def __init__(self):
        CameraBase.__init__(self)

        self.abort.clear()
        self.client = None
        self.pars = list()
        self.stats = list()
        self.sgl2 = list()

        self.ccd = 0

        # self.lastTemp = None
        #
        # self.lastFrameStartTime = None
        # self.lastFrameTemp = None
        # self.lastFrameFilename = ""

        # self._isFanning = False

        # self.setHz(1.0 / 5)

        self._supports = {CameraFeature.TEMPERATURE_CONTROL: True,
                          CameraFeature.PROGRAMMABLE_GAIN: True,
                          CameraFeature.PROGRAMMABLE_OVERSCAN: False,
                          CameraFeature.PROGRAMMABLE_FAN: False,
                          CameraFeature.PROGRAMMABLE_LEDS: True,
                          CameraFeature.PROGRAMMABLE_BIAS_LEVEL: False}

        self._nCCDs = 0  # number of installed CCDs

        self._ccds = {self.ccd: CCD.IMAGING}

        self._adcs = {"12 bits": 0}  # Check

        countBinns = count(0)
        self._binnings = defaultdict(countBinns.next)

        # self._binning_factors = {'1x1':1}

        self._gain = []

        self._ros = []

        self._readoutModes = {}

        # self._cameraParameters = {}

        self.imghdr = Header()

    def __start__(self):
        self.open()
        self.log.info("retrieving information from camera...")
        self.get_status()
        self.get_config()
        self.get_camera_settings()

    def __stop__(self):
        try:
            # self.stopFan()
            # WARNING: NEVER do this on this camera!!
            # self.stopCooling()
            self.close()
        except SIException:
            pass

    @lock
    def open(self):
        """
        Open connection with SI Camera server.

        :return:
        """
        self.log.debug("Connecting to SI Camera Server @ %s:%s" % (
            self["camera_host"], self["camera_port"]))

        self.client = SIClient(self['camera_host'], self['camera_port'])
        try:
            self.client.connect()
        except SIException as e:
            self.log.critical("Connection error: {}".format(e))
            return False
        return True

    @lock
    def close(self):
        self.client.disconnect()

    @lock
    def get_config(self):
        """
        Get the camera configuration parameters.

        .. method:: configure()

        """
        self.pars = []
        lines = self.client.executeCommand(
            GetCameraParameters()).parameterlist.splitlines()
        for i in range(len(lines)):
            self.pars += [re.split(',(.+),', lines[i])]
        for i in range(len(self.pars) - 1):
            if "Installed CCDs" in self.pars[i][1]:
                self._nCCDs = int(self.pars[i][2])
                # if "Serial Binning" in cam.pars[i][1]:
                #     self.sbin = cam.pars[i][2]
                # if "Parallel Binning" in cam.pars[i][1]:
                #     self.pbin = cam.pars[i][2]

        if self._nCCDs == 0:
            self._nCCDs = 1

        for i in range(self._nCCDs):
            self._ccds[i] = i

        self._binnings = {"1x1": 0}
        self._binning_factors = {"1x1": 1}

        # ToDo: Read gain from camera parameters
        self._gain = [0, 1]

        # ToDo: Read read-out-speed from camera parameters
        self._ros = ['101MHz', '500kHz', '250kHz', '100kHz']

        # This readoutMode stores only geometrical information.
        for ccd in self._ccds.keys():
            romode = {}
            mode = 0
            for g in self._gain:
                readoutMode = ReadoutMode()
                readoutMode.mode = mode
                readoutMode.gain = g
                readoutMode.width, readoutMode.height = self.getPhysicalSize()
                readoutMode.pixelWidth, readoutMode.pixelHeight = \
                    self.getPixelSize()
                romode[mode] = readoutMode
            self._readoutModes[ccd] = romode

    @lock
    def get_status(self):
        """
        Return camera status table.
            Generates an instance list of lists containing group,name.value
             strings.
        .. method:: get_status()
            Generates an instance list of lists containing name,value,unit
             strings.
        """
        self.stats = []
        lines = self.client.executeCommand(
            GetStatusFromCamera()).statuslist.splitlines()
        for i in range(len(lines)):
            self.stats += [re.split(',(.+),', lines[i])]

    @lock
    def get_camera_settings(self):
        """
        Return the SGLII settings.
        :return:
        """
        self.sgl2 = self.client.executeCommand(GetSIImageSGLIISettings())

    @lock
    def get_acq_modes(self):
        """

        :return:
        """
        self.acqmodes = self.client.executeCommand(
            GetAcquisitionModes()).menuinfolist.splitlines()

    @lock
    def get_xml_files(self, thefile):
        # Get the main files list
        xmlfiles = self.client.executeCommand(
            GetCameraXMLFile('files.xml')).fileslist

        # flist = []
        # root = ETree.fromstring(xmlfiles)
        #
        # for k in root.iter(tag='name'):
        #     if ‘_q’ not in k.text:
        #         flist.append(k.text)
        # flist now contains the list of all xml files; lets go pick each
        # for f in flist:
        #     pass

    @lock
    def startCooling(self, tempC):
        # TODO: works, doesn't return
        # send command
        try:
            ack = self.client.executeCommand(SetCooler(1))
        except AckException:
            return False
        else:
            return True

    @lock
    def stopCooling(self):
        # send command
        try:
            ack = self.client.executeCommand(SetCooler(0))
        except AckException:
            return False
        else:
            return True

    @lock
    def isCooling(self):
        NotImplementedError()

    def isFanning(self):
        return False

    @lock
    def getTemperature(self):
        ttpl = list()
        self.get_status()
        for i in range(len(self.stats)):
            if "CCD Temp." in self.stats[i][0]:
                ttpl.append(self.stats[i][1].replace(',', '.'))
        return float(ttpl[self.getCurrentCCD()])

    @lock
    def getSetPoint(self):
        """
        Return the CCD(s) temperature set point.
        .. Note:: the value stored in the camera's registry is in K*10.

        :return: temperature in C.
        """
        for i in range(len(self.pars)):
            if "Temperature Setpoint" in self.pars[i][1]:
                temp = (int(self.pars[i][2]) / 10.) - 273.15
        return temp

    def getCCDs(self):
        return self._ccds

    def getCurrentCCD(self):
        return self.ccd

    def getBinnings(self):
        """
        Return available binnings.

        If there is a predefined set of binnings imposed by other cameras,
        it will be returned as a dict. Otherwise a dict with the current
        values  is returned.
        :return:
        """
        # sb = str(self.sgl2.serial_binning)
        # pb = str(self.sgl2.parallel_binning)
        # return {"{0:s}x{1:s}".format(sb, pb): 0}
        return self._binnings

    def getADCs(self):
        return self._adcs

    def getPhysicalSize(self):
        length, heigth = 0, 0
        for i in range(len(self.pars)):
            if "Serial Active Pix." in self.pars[i]:
                length = int(self.pars[i][2])
            elif "Parallel Active Pix." in self.pars[i]:
                heigth = int(self.pars[i][2])

        return length, heigth

    def getPixelSize(self):
        xsize, ysize = self.getPhysicalSize()

        length, heigth = 0, 0
        for i in range(len(self.pars)):
            if "Image Area Size X" in self.pars[i]:
                length = float(self.pars[i][2])  # /xsize
            elif "Image Area Size Y" in self.pars[i]:
                heigth = float(self.pars[i][2])  # /ysize

        return length, heigth

    def getOverscanSize(self, ccd=None):
        # ToDo: Select CCD
        length, heigth = 0, 0
        for i in range(len(self.pars)):
            if "Serial Pre-Masked" in self.pars[i]:
                length = int(self.pars[i][2])
            elif "Parallel Pre-Masked" in self.pars[i]:
                heigth = int(self.pars[i][2])

        return (length, heigth)

    def getReadoutModes(self):
        return self._readoutModes

    def supports(self, feature=None):
        return self._supports[feature]

    def _expose(self, imageRequest):

        shutterRequest = imageRequest['shutter']

        if shutterRequest == Shutter.OPEN:
            shutter = self.client.executeCommand(
                SetAcquisitionType(0))  # Light
        elif shutterRequest == Shutter.CLOSE:
            shutter = self.client.executeCommand(SetAcquisitionType(1))  # Dark
        elif shutterRequest == Shutter.LEAVE_AS_IS:  # As it was
            pass
        else:
            self.log.warning("Incorrect shutter option (%s)."
                             " Leaving shutter intact" % shutterRequest)

        if not imageRequest['binning']:
            srl_bin, prl_bin = 1, 1
        else:
            try:
                srl_bin, prl_bin = imageRequest['binning'].split('x')
            except:
                self.log.error('Could not determine binning. Using 1x1')
                srl_bin, prl_bin = 1, 1
                pass

                #  (mode, binning, top, left, width, height) =
                #  self._getReadoutModeInfo(imageRequest["binning"],
                # imageRequest["window"])

        self.client.executeCommand(
            SetAcquisitionMode(0))  # Chimera will always execute SINGLE FRAMES
        self.client.executeCommand(SetExposureTime(imageRequest["exptime"]))
        # self.client.executeCommand(SetNumberOfFrames(self["frames"]))
        # self.client.executeCommand(
        # SetCCDFormatParameters(0, 4096, srl_bin, 0, 4096, prl_bin))

        # ok, start it
        self.exposeBegin(imageRequest)

        self.client.executeCommand(Acquire())

        # save time exposure started
        self.lastFrameStartTime = dt.datetime.utcnow()
        self.lastFrameTemp = self.getTemperature()

        status = CameraStatus.OK
        self.abort.clear()

        while self._isExposing():
            # [ABORT POINT]
            if self.abort.isSet():
                self.abortExposure()
                status = CameraStatus.ABORTED
                break
            # this sleep is EXTREMELY important: without it, Python would
            # stuck on this
            # thread and abort will not work.
            time.sleep(0.01)

            # end exposure and returns
        return self._endExposure(imageRequest, status)

    def _endExposure(self, request, status):
        self.exposeComplete(request, status)
        return True

    def abortExposure(self, readout=True):
        # Send temination to camera
        self.client.executeCommand(TerminateAcquisition())
        # Readout
        # self._readout(imageRequest)

    def _isExposing(self):
        status = self.client.executeCommand(InquireAcquisitionStatus())
        self.log.debug(status.exp_done_percent)
        return status.exp_done_percent < 100


    def _readout(self, imageRequest):
        self.readoutBegin(imageRequest)
        (mode, binning, top, left, width, height) = self._getReadoutModeInfo(
            imageRequest["binning"], imageRequest["window"])

        # TODO: get initial sizes from pars...
        # imgarray = N.zeros((4096, 4096), N.int32)
        #while not self.abort.isSet():
        self.abort.clear()
        while self.isReadingOut():
            imgdata = self.client.executeCommand(
                RetrieveImage(ImgType.U16.index))

            self.log.debug('Reading out data...')

            # Ship the data to the image server (via CameraBase)
            extra = {"frame_temperature": self.lastFrameTemp,
                     "frame_start_time": self.lastFrameStartTime}
            imgarray = N.ndarray(shape=(imgdata[1], imgdata[0]),
                                 buffer=imgdata[2], dtype=N.uint16)
            self._saveImage(imageRequest, imgarray, extra)
            # Got the data, lets do the header

            self.log.debug("Startinh header construction...")

            self.imghdr.append(('SIMPLE', 'T', 'conforms to FITS standard'))
            # Self. This camera delivers a very non compliant FITS header...
            camh = self.client.executeCommand(GetImageHeader(1))
            for i in range(len(camh) / 80):
                k = camh[80 * i:80 * (i + 1)][0:8].strip()
                if k == 'SIMPLE':
                    continue
                if k == 'END':
                    break
                vc = camh[80 * i:80 * (i + 1)][9:].split('/', 1)
                if len(vc) == 2:
                    v, c = vc[0].strip(), vc[1].strip().rstrip(',')
                else:
                    v, c = '', vc[0].strip().rstrip(',')
                self.imghdr.append((k, v, c))
            if self.abort.isSet():
                # We have been aborted!...
                ack = self.client.executeCommand(TerminateImageRetrieve())
                break
                # More cleanup?

    # def _getReadoutModeInfo(self, binning, window):
    #     """
    #     Check if the given binning and window could be used on the given CCD.
    #     Returns a tuple (modeId, binning, top, left, width, height)
    #     """
    #     # We need to override this method in order to handle the unrestricted
    #     # binnings of this camera.
    #     mode = None
    #
    #     if binning not in self._binnings:
    #         self._binnings.setdefault(binning,
    #                                   max(self._binnings.values()) + 1)
    #         self._binning_factors.setdefault(binning, max(
    #             self._binning_factors.values()) + 1)
    #
    #     mode = self.getReadoutModes()[self.getCurrentCCD()][binId]
    #
    #     left = 0
    #     top = 0
    #     width, height = mode.getSize()
    #
    #     if window is not None:
    #         try:
    #             xx, yy = window.split(",")
    #             xx = xx.strip()
    #             yy = yy.strip()
    #             x1, x2 = xx.split(":")
    #             y1, y2 = yy.split(":")
    #
    #             x1 = int(x1)
    #             x2 = int(x2)
    #             y1 = int(y1)
    #             y2 = int(y2)
    #
    #             left = min(x1, x2) - 1
    #             top = min(y1, y2) - 1
    #             width = (max(x1, x2) - min(x1, x2)) + 1
    #             height = (max(y1, y2) - min(y1, y2)) + 1
    #
    #             if left < 0 or left >= mode.width:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: left=%d, ccd width (in this "
    #                     "binning)=%d" % (left, mode.width))
    #
    #             if top < 0 or top >= mode.height:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: top=%d, ccd height (in this "
    #                     "binning)=%d" % (top, mode.height))
    #
    #             if width > mode.width:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: width=%d, ccd width (int this "
    #                     "binning)=%d" % (width, mode.width))
    #
    #             if height > mode.height:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: height=%d, ccd height (int this "
    #                     "binning)=%d" % (height, mode.height))
    #
    #         except ValueError:
    #             left = 0
    #             top = 0
    #             width, height = mode.getSize()
    #
    #     if not binning:
    #         binning = self.getBinnings().keys().pop(
    #             self.getBinnings().keys().index("1x1"))
    #
    #     return (mode, binning, top, left, width, height)


def getMetadata(self, request):
    return self.imghdr.items()
