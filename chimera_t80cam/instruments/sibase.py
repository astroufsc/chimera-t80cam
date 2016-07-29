
import os
import re
import logging
import threading
import Queue

import numpy as N
from astropy.io.fits import Header
from astropy.io import fits as pyfits

import select

from si.client import SIClient, AckException
from si.commands.camera import *
from si.packet import Packet
from si.packets.ack import Ack

from chimera.interfaces.camera import (CCD, CameraFeature, ReadoutMode,
                                       InvalidReadoutMode, CameraStatus,
                                       Shutter)

from chimera.util.image import Image, ImageUtil
from chimera.instruments.camera import CameraBase
from chimera.util.enum import Enum
from chimera.core.lock import lock
from chimera.core.exceptions import ChimeraException
from chimera.core.version import _chimera_name_, _chimera_long_description_
from chimera.controllers.imageserver.util import getImageServer

from collections import defaultdict
from itertools import count

import datetime as dt
import time

ImgType = Enum("U16", "I16", "U32", "I32", "SGL", "DBL")


class SIException(ChimeraException):
    pass

log = logging.getLogger(__name__)

class SIBase(CameraBase):
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
                  'camera_host': '127.0.0.1', 'camera_port': 2055,
                  'localhost': False,
                  "local_filename" : 'tmp.fits',
                  "local_path" : '/tmp/',
                  "fast_mode" : True, # May return image with unfinished header
                  "bad_cards" : "NAXIS3,DATE-OBS,PG0_1,PG1_1,PG1_2,PG0_10,PG0_15,PG0_54,PG0_55,PG0_56",
                  "ccdtemp" : 'PG0_56',
                  "instrumentTemperature" : 'PG0_55',
                  "detectorname" : 'e2V CCD290-99',
                  "exptime" : 'PG2_0',
                  "ccdsize_x" : 'PG1_7',
                  "ccdsize_y" : 'PG1_8',
                  # WCS information
                  "parity_y" : 1., # Up is North
                  "parity_x" : 1., # Left is East
                  "max_files": 10,

                  # ITEMS to be measured on the camera
                  "OUT1_SATUR": "100000.0",  # Output 1 saturation level (e-)
                  "OUT2_SATUR": "100000.0",  # Output 2 saturation level (e-)
                  "OUT3_SATUR": "100000.0",  # Output 3 saturation level (e-)
                  "OUT4_SATUR": "100000.0",  # Output 4 saturation level (e-)
                  "OUT5_SATUR": "100000.0",  # Output 5 saturation level (e-)
                  "OUT6_SATUR": "100000.0",  # Output 6 saturation level (e-)
                  "OUT7_SATUR": "100000.0",  # Output 7 saturation level (e-)
                  "OUT8_SATUR": "100000.0",  # Output 8 saturation level (e-)
                  "OUT9_SATUR": "100000.0",  # Output 9 saturation level (e-)
                  "OUT10_SATUR": "100000.0",  # Output 10 saturation level (e-)
                  "OUT11_SATUR": "100000.0",  # Output 11 saturation level (e-)
                  "OUT12_SATUR": "100000.0",  # Output 12 saturation level (e-)
                  "OUT13_SATUR": "100000.0",  # Output 13 saturation level (e-)
                  "OUT14_SATUR": "100000.0",  # Output 14 saturation level (e-)
                  "OUT15_SATUR": "100000.0",  # Output 15 saturation level (e-)
                  "OUT16_SATUR": "100000.0",  # Output 16 saturation level (e-)


                  "OUT1_RON": "9.8900",  # Readout-noise of OUT1 at selected Gain (e-)
                  "OUT2_RON": "9.8900",  # Readout-noise of OUT2 at selected Gain (e-)
                  "OUT3_RON": "9.8900",  # Readout-noise of OUT3 at selected Gain (e-)
                  "OUT4_RON": "9.8900",  # Readout-noise of OUT4 at selected Gain (e-)
                  "OUT5_RON": "9.8900",  # Readout-noise of OUT5 at selected Gain (e-)
                  "OUT6_RON": "9.8900",  # Readout-noise of OUT6 at selected Gain (e-)
                  "OUT7_RON": "9.8900",  # Readout-noise of OUT7 at selected Gain (e-)
                  "OUT8_RON": "9.8900",  # Readout-noise of OUT8 at selected Gain (e-)
                  "OUT9_RON": "9.8900",  # Readout-noise of OUT9 at selected Gain (e-)
                  "OUT10_RON": "9.8900",  # Readout-noise of OUT10 at selected Gain (e-)
                  "OUT11_RON": "9.8900",  # Readout-noise of OUT11 at selected Gain (e-)
                  "OUT12_RON": "9.8900",  # Readout-noise of OUT12 at selected Gain (e-)
                  "OUT13_RON": "9.8900",  # Readout-noise of OUT13 at selected Gain (e-)
                  "OUT14_RON": "9.8900",  # Readout-noise of OUT14 at selected Gain (e-)
                  "OUT15_RON": "9.8900",  # Readout-noise of OUT15 at selected Gain (e-)
                  "OUT16_RON": "9.8900",  # Readout-noise of OUT16 at selected Gain (e-)

                  "OUT1_GAIN": "1.12",  # Gain for output 1. Conversion from ADU to electron (e-/ADU)
                  "OUT2_GAIN": "1.12",  # Gain for output 2. Conversion from ADU to electron (e-/ADU)
                  "OUT3_GAIN": "1.12",  # Gain for output 3. Conversion from ADU to electron (e-/ADU)
                  "OUT4_GAIN": "1.12",  # Gain for output 4. Conversion from ADU to electron (e-/ADU)
                  "OUT5_GAIN": "1.12",  # Gain for output 5. Conversion from ADU to electron (e-/ADU)
                  "OUT6_GAIN": "1.12",  # Gain for output 6. Conversion from ADU to electron (e-/ADU)
                  "OUT7_GAIN": "1.12",  # Gain for output 7. Conversion from ADU to electron (e-/ADU)
                  "OUT8_GAIN": "1.12",  # Gain for output 8. Conversion from ADU to electron (e-/ADU)
                  "OUT9_GAIN": "1.12",  # Gain for output 9. Conversion from ADU to electron (e-/ADU)
                  "OUT10_GAIN": "1.12",  # Gain for output 10. Conversion from ADU to electron (e-/ADU)
                  "OUT11_GAIN": "1.12",  # Gain for output 11. Conversion from ADU to electron (e-/ADU)
                  "OUT12_GAIN": "1.12",  # Gain for output 12. Conversion from ADU to electron (e-/ADU)
                  "OUT13_GAIN": "1.12",  # Gain for output 13. Conversion from ADU to electron (e-/ADU)
                  "OUT14_GAIN": "1.12",  # Gain for output 14. Conversion from ADU to electron (e-/ADU)
                  "OUT15_GAIN": "1.12",  # Gain for output 15. Conversion from ADU to electron (e-/ADU)
                  "OUT16_GAIN": "1.12",  # Gain for output 16. Conversion from ADU to electron (e-/ADU)
                  }

    def __init__(self):
        CameraBase.__init__(self)

        self.abort.clear()
        self.client = None
        self.pars = list()
        self.stats = list()
        self.sgl2 = list()

        self.ccd = 0
        self.__is_exposing = threading.Event()

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

        self._threadList = []

        self._tmpFilesProxyQueue = Queue.Queue()
        self._finalFilesProxyQueue = Queue.Queue()

    def __start__(self):
        self.open()
        self.log.info("retrieving information from camera...")
        self.get_status()
        self.get_config()
        self.get_camera_settings()
        self.setHz(1.0 / 30.0)

    def __stop__(self):
        try:
            # self.stopFan()
            # WARNING: NEVER do this on this camera!!
            # self.stopCooling()
            self.close()
        except SIException:
            pass

    def control(self):

        for i in range(len(self._threadList)-1,-1,-1):
            if not self._threadList[i].isAlive():
                self._threadList.pop(i)

        self.log.debug("[control] Proxy queue sizes: %i %i" % (self._tmpFilesProxyQueue.qsize(),
                                                               self._finalFilesProxyQueue.qsize()))
        try:
            if self._tmpFilesProxyQueue.qsize() > self["max_files"]:
                for i in range(self["max_files"]):
                    proxy = self._tmpFilesProxyQueue.get()
                    self.log.debug("[control] Closing temporary file %s ..." % proxy[0].filename())
                    # self.log.debug("[control] Closing temporary file %s ..." % proxy[1])
                    proxy[0].close()
        except:
            self.log.error("Error trying to empty image queue.")

        try:
            if self._finalFilesProxyQueue.qsize() > self["max_files"]:
                for i in range(self["max_files"]):
                    proxy = self._finalFilesProxyQueue.get()
                    self.log.debug("[control] Closing final file %s ..." % proxy[0].filename())
                    # self.log.debug("[control] Closing final file %s ..." % proxy[1])
                    proxy[0].close()
        except:
            self.log.error("Error trying to empty image queue.")

        return True

    @lock
    def open(self):
        """
        Open connection with SI Camera server.

        :return:
        """
        self.setHz(0.1)

        return self.connectSIClient()

    def connectSIClient(self):
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

    def getClient(self):
        return self.client

    @lock
    def get_config(self):
        """
        Get the camera configuration parameters.

        .. method:: configure()

        """
        self.pars = []
        client = self.getClient() #self.client
        lines = client.executeCommand(
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
        client = self.getClient()
        lines = client.executeCommand(
            GetStatusFromCamera()).statuslist.splitlines()
        self.stats = []
        for i in range(len(lines)):
            self.stats += [re.split(',(.+),', lines[i])]

    @lock
    def get_camera_settings(self):
        """
        Return the SGLII settings.
        :return:
        """
        client = self.getClient()
        self.sgl2 = client.executeCommand(GetSIImageSGLIISettings())

    @lock
    def get_acq_modes(self):
        """

        :return:
        """
        client = self.getClient()
        self.acqmodes = client.executeCommand(
            GetAcquisitionModes()).menuinfolist.splitlines()

    @lock
    def get_xml_files(self, thefile):
        # Get the main files list
        client = self.getClient()
        xmlfiles = client.executeCommand(
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
        client = self.getClient()
        try:
            ack = client.executeCommand(SetCooler(1))
        except AckException:
            return False
        else:
            return True

    @lock
    def stopCooling(self):
        # send command
        client = self.getClient()
        try:
            ack = client.executeCommand(SetCooler(0))
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
        try:
            self.get_status()
        except:
            self.log.warning('Could not update camera temperature.')
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
        # Fixme: Properly read this from the configuration

        return 9., 9. #length, heigth

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
        client = self.getClient()

        if shutterRequest == Shutter.OPEN:
            shutter = client.executeCommand(SetAcquisitionType(0))  # Light
        elif shutterRequest == Shutter.CLOSE:
            shutter = client.executeCommand(SetAcquisitionType(1))  # Dark
        elif shutterRequest == Shutter.LEAVE_AS_IS:  # As it was
            pass
        else:
            self.log.warning("Incorrect shutter option (%s). Leaving shutter intact" % shutterRequest)

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

        client.executeCommand(SetAcquisitionMode(0))  # Chimera will always execute SINGLE FRAMES
        client.executeCommand(SetExposureTime(imageRequest["exptime"]))
        # self.client.executeCommand(SetNumberOfFrames(self["frames"]))
        # self.client.executeCommand(
        # SetCCDFormatParameters(0, 4096, srl_bin, 0, 4096, prl_bin))

        cmd = Acquire()
        cmd_to_send = cmd.command()
        # save time exposure started
        self.__lastFrameStart = dt.datetime.utcnow()
        self.lastFrameTemp = -999. # self.getTemperature()

        status = CameraStatus.OK

        # ok, start it
        self.exposeBegin(imageRequest)

        # send Acquire command
        bytes_sent = client.sk.send(cmd_to_send.toStruct())

        # check acknowledge
        ret = select.select([client.sk], [], [])
        if not ret[0]:
            raise SIException('No answer from camera')

        if ret[0][0] == client.sk:

            header = Packet()
            header_data = client.recv(len(header))
            header.fromStruct(header_data)

            if header.id == 129:
                ack = Ack()
                ack.fromStruct(header_data + client.recv(header.length - len(header)))

                if not ack.accept:
                    raise AckException("Camera did not accepted command...")
            else:
                raise AckException("No acknowledge received from camera...")

        self.abort.clear()

        while self._isExposing():
            # [ABORT POINT]
            if self.abort.isSet():
                # self.abortExposure()
                client.executeCommand(TerminateAcquisition(),noAck=True)
                while True:

                    ret = select.select([client.sk], [], [])

                    if not ret[0]:
                        break

                    if ret[0][0] == client.sk:

                        header = Packet()
                        header_data = client.recv(len(header))
                        header.fromStruct(header_data)

                        if header.id == 131:  # incoming data pkt
                            data = cmd.result()  # data structure as defined in data.py
                            data.fromStruct(
                                header_data + client.recv(header.length - len(header)))
                            #data.fromStruct (header_data + self.recv (header.length))
                            # logging.debug(data)
                            self.log.debug("data type is {}".format(data.data_type))
                            break

                status = CameraStatus.ABORTED
                break

        return self._endExposure(imageRequest, status)

    def _endExposure(self, request, status):
        self.exposeComplete(request, status)
        return True

    def abortExposure(self, readout=True):
        self.abort.set()

    def _isExposing(self):
        client = self.getClient()
        status = client.executeCommand(InquireAcquisitionStatus())
        return status.exp_done_percent < 100

    def _isReadingOut(self):
        client = self.getClient()
        status = client.executeCommand(InquireAcquisitionStatus())
        return status.readout_done_percent < 100

    def _readout(self, imageRequest):
        # self.readoutBegin(imageRequest)

        # TODO: get initial sizes from pars...
        # imgarray = N.zeros((4096, 4096), N.int32)
        #while not self.abort.isSet():
        status = CameraStatus.OK
        client = self.getClient()
        if self.abort.isSet():
            self.readoutComplete(None, CameraStatus.ABORTED)
            return None

            # status = CameraStatus.ABORTED

        self.abort.clear()

        # while self._isReadingOut():
        #
        #     if self.abort.isSet():
        #         self.abortExposure(readout=False)
        #         status = CameraStatus.ABORTED
        #         break

        # Get orphan packet from Acquire command issue in _expose
        cmd = Acquire()

        while True:

            ret = select.select([client.sk], [], [])

            if not ret[0]:
                break

            if ret[0][0] == client.sk:

                header = Packet()
                header_data = client.recv(len(header))
                header.fromStruct(header_data)

                if header.id == 131:  # incoming data pkt
                    data = cmd.result()  # data structure as defined in data.py
                    data.fromStruct(
                        header_data + client.recv(header.length - len(header)))
                    #data.fromStruct (header_data + self.recv (header.length))
                    # logging.debug(data)
                    self.log.debug("data type is {}".format(data.data_type))
                    break

        (mode, binning, top, left, width, height) = self._getReadoutModeInfo(imageRequest["binning"], imageRequest["window"])

       # LAST ABORT POINT
        if self.abort.isSet():
            self.readoutComplete(None, CameraStatus.ABORTED)
            return None

        if not self["localhost"]:
            self.log.debug('Remote mode')

            serial_length, parallel_length, img_buffer = client.executeCommand(RetrieveImage(0))

            pix = N.array(img_buffer, dtype=N.uint16)

            if len(pix) != width * height:
                raise SIException("Wrong image size. Expected %i x %i (%i), got %i" % (width,
                                                                                     height,
                                                                                     width *
                                                                                     height,
                                                                                     len(pix)))

            pix = pix.reshape(width, height)
            pix.byteswap(True)

            header = client.executeCommand(GetImageHeader(1))

            headers = self._processHeader(header)

            headers["frame_start_time"] = self.__lastFrameStart
            # headers["frame_temperature"] = self.getTemperature()
            # headers["binning_factor"] = self._binning_factors[binning]

            proxy = self._saveImage(imageRequest, pix, headers)

        else:
            self.log.debug('Local mode. Saving file to %s' % (os.path.join(self["local_path"], self["local_filename"])))
            # Save the image to the local disk and read them instead. Should be much faster.
            # Todo: Get rid of "local_path" and "local_filename" and use temporary files
            filename = ''

            if imageRequest:
                if not "filename" in imageRequest.keys():
                    raise TypeError("Invalid filename, you must pass filename=something or a valid ImageRequest object")
                else:
                    filename = imageRequest["filename"]

            path, filename = os.path.split(ImageUtil.makeFilename(filename))

            self.client.executeCommand(SetSaveToFolderPath(self['local_path']))
            self.client.executeCommand(SaveImage(self['local_filename'], 'I16'))
            # self.releaseExposure()
            # self.unlockExposure()

            def cleanHeader(scale_back):
                hdu = pyfits.open(os.path.join(self['local_path'], self['local_filename']),
                                  ignore_missing_end = True,
                                  scale_back=scale_back)


                self.log.debug('Excluding bad cards...')
                badcards = self["bad_cards"].split(',')

                for card in badcards:
                    self.log.debug('Removing card "%s" from header' % card)
                    hdu[0].header.remove(card)

                # Save temporary image to local_path/night
                # Create dir if necessary
                # tmpdir = os.path.join(self['local_path'], os.path.split(path)[-1])
                # if not os.path.exists(tmpdir):
                #     os.mkdir(tmpdir)
                #
                # # Save temporary image
                # hdu.writeto(os.path.join(tmpdir, filename))
                hdu.writeto(os.path.join(self['local_path'], filename))

                return {'ccdtemp': hdu[0].header[self["ccdtemp"]],
                           'itemp': hdu[0].header[self["instrumentTemperature"]],
                           'exptime': float(hdu[0].header[self['exptime']]),
                           }

            try:
                extraHeaders = cleanHeader(True)
            except MemoryError, e:
                self.log.error("Could not save in scale_back mode. Trying with normal mode.")
                self.log.exception(e)
                extraHeaders = cleanHeader(False)



            # From now on camera is ready to take new exposures, will return and move this to a different thread.
            self.log.debug('Registering image and creating proxy. PP')
            # register image on ImageServer
            server = getImageServer(self.getManager())
            # img = Image.fromFile(os.path.join(self['local_path'], filename))
            img = Image.fromFile(os.path.join(self['local_path'], filename))

            proxy = server.register(img)
            self._tmpFilesProxyQueue.put([proxy,proxy.filename()])
            # proxy = self._finishHeader(imageRequest,self.__lastFrameStart,filename,path,extraHeaders)
            if self["fast_mode"]:
                p = threading.Thread(target=self._finishHeader, args=(imageRequest, self.__lastFrameStart, filename, path, extraHeaders))
                self._threadList.append(p)
                p.start()
                # self._tmpFilesProxyQueue.put(proxy)
            else:
                proxy = self._finishHeader(imageRequest,self.__lastFrameStart,filename,path,extraHeaders)

        self.readoutComplete(proxy, CameraStatus.OK)
        return proxy

        # return

    def _finishHeader(self, imageRequest, frameStart, filename, path, extraHeaders):

        hdu = pyfits.open(os.path.join(self['local_path'], filename), scale_back=True)

        hdu[0].header.remove('CHM_ID')
        # self.log.debug('Excluding bad cards...')
        # badcards = self["bad_cards"].split(',')
        #
        # for card in badcards:
        #     self.log.debug('Removing card "%s" from header' % card)
        #     hdu[0].header.remove(card)


        self.log.debug('Adding header information')

        ccdtemp = extraHeaders["ccdtemp"]
        itemp = extraHeaders["itemp"]
        exptime = extraHeaders['exptime']

        if imageRequest:
            for header in imageRequest.headers:
                try:
                    hdu[0].header.set(*header)
                except Exception, e:
                    log.warning("Couldn't add %s: %s" % (str(header), str(e)))

        md = [('FILENAME', os.path.basename(filename)),
              ("DATE", ImageUtil.formatDate(dt.datetime.utcnow()), "date of file creation"),
              ("AUTHOR", _chimera_name_, _chimera_long_description_),
              ('HIERARCH T80S DET EXPTIME', exptime, "exposure time in seconds"),
              ('INSTRUME', str(self['camera_model']), 'Custom. Name of instrument'),
              ('HIERARCH T80S DET TEMP', ccdtemp, ' Chip temperature (C) '),]
        #       ('IMAGETYP', request['type'].strip(), 'Custom. Image type'),
        #       ('SHUTTER', str(request['shutter']), 'Custom. Requested shutter state'),
        #
        #       ('CCD',    str(self.instrument['ccd_model']), 'Custom. CCD Model'),
        #       ('CCD_DIMX', self.instrument.getPhysicalSize()[0], 'Custom. CCD X Dimension Size'),
        #       ('CCD_DIMY', self.instrument.getPhysicalSize()[1], 'Custom. CCD Y Dimension Size'),
        #       ('CCDPXSZX', self.instrument.getPixelSize()[0], 'Custom. CCD X Pixel Size [micrometer]'),
        #       ('CCDPXSZY', self.instrument.getPixelSize()[1], 'Custom. CCD Y Pixel Size [micrometer]')]
        #
            # md += [('HIERARCH T80S INS TEMP', extra_header_info["frame_temperature"],
            #         'Instrument temperature (C) at end of exposure.')]

        (mode, binning, top, left,
        width, height) = self._getReadoutModeInfo(imageRequest["binning"],
                                                  imageRequest["window"])
        binFactor = self._binning_factors[binning]
        pix_w, pix_h = self.getPixelSize() # hdu[0].header[self['ccdsize_x']] / hdu[0].header[self['']]

        if self["telescope_focal_length"] is not None:  # If there is no telescope_focal_length defined, don't store WCS
            focal_length = self["telescope_focal_length"]

            scale_x = binFactor * (((180 / N.pi) / focal_length) * (pix_w * 0.001))
            scale_y = binFactor * (((180 / N.pi) / focal_length) * (pix_h * 0.001))

            full_width, full_height = self.getPhysicalSize()
            CRPIX1 = ((int(full_width / 2.0)) - left) - 1
            CRPIX2 = ((int(full_height / 2.0)) - top) - 1
            # Todo: Check telescope pier side
            parity_y = self["parity_y"]
            parity_x = self["parity_x"]
            # Adding WCS coordinates according to FITS standard.
            # Quick sheet: http://www.astro.iag.usp.br/~moser/notes/GAi_FITSimgs.html
            # http://adsabs.harvard.edu/abs/2002A%26A...395.1061G
            # http://adsabs.harvard.edu/abs/2002A%26A...395.1077C
            md += [("CRPIX1", CRPIX1, "coordinate system reference pixel"),
                ("CRPIX2", CRPIX2, "coordinate system reference pixel"),
                ("CD1_1", parity_x * scale_x * N.cos(self["rotation"]*N.pi/180.),
                 "transformation matrix element (1,1)"),
                ("CD1_2", -parity_y * scale_y * N.sin(self["rotation"]*N.pi/180.),
                 "transformation matrix element (1,2)"),
                ("CD2_1", parity_x * scale_x * N.sin(self["rotation"]*N.pi/180.),
                 "transformation matrix element (2,1)"),
                ("CD2_2", parity_y * scale_y * N.cos(self["rotation"]*N.pi/180.),
                 "transformation matrix element (2,2)")]


        md += [
                # ('BUNIT', 'adu', 'physical units of the array values '),        #TODO:
                #('BLANK', -32768),        #TODO:
                #('BZERO', '0.0'),        #TODO:
                ('HIERARCH T80S INS OPER', 'CHIMERA'),
                ('HIERARCH T80S INS PIXSCALE', '%.3f'%(scale_x*3600.), 'Pixel scale (arcsec)'),
                ('HIERARCH T80S INS TEMP', itemp, 'Instrument temperature'),
                ('HIERARCH T80S DET NAME', self["detectorname"], 'Name of detector system '),
                # ('HIERARCH T80S DET CCDS', ' 1 ', ' Number of CCDs in the mosaic'),        #TODO:
                # ('HIERARCH T80S DET CHIPID', ' 0 ', ' Detector CCD identification'),        #TODO:
                ('HIERARCH T80S DET NX', hdu[0].header['NAXIS1'], ' Number of pixels along X '),
                ('HIERARCH T80S DET NY', hdu[0].header['NAXIS2'], ' Number of pixels along Y'),
                ('HIERARCH T80S DET PSZX', pix_w, ' Size of pixel in X (mu) '),
                ('HIERARCH T80S DET PSZY', pix_h, ' Size of pixel in Y (mu) '),
                # ('HIERARCH T80S DET EXP TYPE', 'LIGHT', ' Type of exp as known to the CCD SW '),        #TODO:
                # ('HIERARCH T80S DET READ MODE', 'SLOW', ' Readout method'),        #TODO:
                # ('HIERARCH T80S DET READ SPEED', '1 MHz', ' Readout speed'),        #TODO:
                # ('HIERARCH T80S DET READ CLOCK', 'DSI 68, High Gain, 1x1', ' Type of exp as known to the CCD SW'),        #TODO:
                # ('HIERARCH T80S DET OUTPUTS', ' 2 ', 'Number of output ports used on chip'),        #TODO:
                ('HIERARCH T80S DET REQTIM', float(imageRequest['exptime']), 'Requested exposure time (sec)')]

        for i_output in range(1, 17):
            line = (i_output-1)%2
            colum = (i_output-((i_output-1)%2)+1)/2

            # md += [
            # ('HIERARCH T80S DET OUT%i ID' % i_output, ' %2i '%(i_output-1), ' Identification for OUT%i readout port ' % i_output),
            # ('HIERARCH T80S DET OUT%i X' % i_output, ' %i ' % (line*hdu[0].header['PG5_5'] + 1), ' X location of output in the chip. (lower left pixel)'),        #TODO:
            # ('HIERARCH T80S DET OUT%i Y' % i_output, ' %i ' % (colum*hdu[0].header['PG5_10'] + 1), ' Y location of output in the chip. (lower left pixel)'),        #TODO:
            # ('HIERARCH T80S DET OUT%i NX' % i_output, hdu[0].header['PG5_5'],
            #  ' Number of image pixels read to port %i in X. Not including pre or overscan' % i_output),
            # ('HIERARCH T80S DET OUT%i NY' % i_output, hdu[0].header['PG5_10'],
            #  ' Number of image pixels read to port %i in Y. Not including pre or overscan' % i_output),
            # ('HIERARCH T80S DET OUT%i IMSC' % i_output, ' [%i:%i,%i:%i] '%(line,line+hdu[0].header['PG5_5'],
            #                                                                colum,colum+hdu[0].header['PG5_10']),
            #  ' Image region for OUT%i in format [xmin:xmax,ymin:ymax] ' % i_output),
            # ('HIERARCH T80S DET OUT%i PRSCX' % i_output, ''), # TODO:
            # ('HIERARCH T80S DET OUT%i PRSCY' % i_output, ''), # TODO:
            # ('HIERARCH T80S DET OUT%i OVSCX' % i_output, ''), # TODO:
            # ('HIERARCH T80S DET OUT%i OVSCY' % i_output,''), # TODO:
            # ('HIERARCH T80S DET OUT%i OVSCY' % i_output,''), # TODO:
            # ('HIERARCH T80S DET OUT%i GAIN' % i_output, self["OUT%i_GAIN" % i_output], ' Gain for output. Conversion from ADU to electron (e-/ADU)'),        #TODO:
            # ('HIERARCH T80S DET OUT%i RON' % i_output, self["OUT%i_RON" % i_output], ' Readout-noise of OUT%i at selected Gain (e-)' % i_output),     # TODO:
            # ('HIERARCH T80S DET OUT%i SATUR' % i_output, self["OUT%i_SATUR" % i_output], ' Saturation of OUT%i (e-)' % i_output)      # TODO:
            # ]

            # for card in wcs:
            #     hdu[0].header.set(*card)

        chimeraCards = [('DATE-OBS', ImageUtil.formatDate(frameStart), 'Date exposure started'),

                        ('CCD-TEMP', ccdtemp, 'CCD Temperature at Exposure Start [deg. C]'),
                        ("EXPTIME", float(imageRequest['exptime']) or 0., "exposure time in seconds"),
                        ('IMAGETYP', imageRequest['type'].strip(), 'Image type'),
                        ('SHUTTER', str(imageRequest['shutter']), 'Requested shutter state'),
                        ('INSTRUME', str(self['camera_model']), 'Name of instrument'),
                        ('CCD', str(self['ccd_model']), 'CCD Model'),
                        ('CCD_DIMX', self.getPhysicalSize()[0], 'CCD X Dimension Size'),
                        ('CCD_DIMY', self.getPhysicalSize()[1], 'CCD Y Dimension Size'),
                        ('CCDPXSZX', self.getPixelSize()[0], 'CCD X Pixel Size [micrometer]'),
                        ('CCDPXSZY', self.getPixelSize()[1], 'CCD Y Pixel Size [micrometer]')]

        # telescope = self.getManager().getProxy(self['telescope'])
        #
        # md += [ ('HIERARCH T80S TEL EL END', telescope.getAlt().toD().__str__()),
        #         ('HIERARCH T80S TEL AZ END', telescope.getAz().toD().__str__()),
        #         ('HIERARCH T80S TEL PARANG END', telescope.getParallacticAngle().toD().__str__(), ' Parallactic angle at end (deg) '),
        #         ('HIERARCH T80S TEL AIRM END',  1 / N.cos(N.pi / 2 - self.instrument.getAlt().R), ' Airmass at end of exposure'),
        #         ]

        for card in chimeraCards:
            hdu[0].header.set(*card)

        for card in md:
            hdu[0].header.set(*card)

        self.log.debug('Writting new fits to disk')
        hdu.writeto(os.path.join(path,
                                 filename.replace('.FIT','.fits')),
                    output_verify='silentfix+warn',
                    checksum=True)
        hdu.close()

        self.log.debug('Header complete')

        self.log.debug('Registering image and creating proxy')
        # register image on ImageServer
        server = getImageServer(self.getManager())
        img = Image.fromFile(os.path.join(path,
                                 filename.replace('.FIT','.fits')))
        # server.register(img)
        proxy = server.register(img)
        self._finalFilesProxyQueue.put([proxy,proxy.filename()])
        return proxy

    def _processHeader(self, header):

        headers = {}
        n_headers = len(header) / 80

        for k in range(n_headers):
            line = header[k * 80:(k + 1) * 80]

            name = line[0:8].strip()
            rest = line[9:]

            if rest.find('/'):
                l = rest.split("/")
                if len(l) != 2:
                    continue

                value, comment = l[0], l[1]
                value = value.strip()
                comment = comment[0:comment.rfind(',')].strip()

                headers[name] = (value, comment)
            else:
                value = rest.strip()
                headers[name] = (value, "")

        return headers

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
