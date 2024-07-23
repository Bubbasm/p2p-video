import numpy as np
from time import sleep
from abc import ABC, abstractmethod
from threading import Thread, Lock
from utils import UDPUtil as udp


class CircularBuffer:
    '''
    Circular Buffer for the app packets.
    By default sorts the packets by their order number.
    '''

    def __init__(self, secs, sort: bool = True, version=0) -> None:
        '''
        Constructor of the buffer
         - size: size of the buffer
        '''

        self.mainBuf = []
        self.fpsBuf = []
        self.secs = secs
        self.size = 0
        self.setFPS(20)
        self.sort = sort
        self.mutex = Lock()
        self.version = version
        self.lastRead = -1

    @staticmethod
    def _sortFunction(e):
        '''
        Custom sort function for the buffer.
        Sorts by the first element of the tuple
        '''
        return e[0]

    def getMaxFps(self):
        maximum = 0
        for _, fps in self.fpsBuf:
            if maximum < fps:
                maximum = fps
        return maximum

    def _writeV1(self, data):
        ''' Implements writing into the buffer as version 1 '''
        with self.mutex:
            if len(self.mainBuf) >= 2*self.size:
                raise Exception("buffer is full")

            lenPack1, rest = data.split(b' ', 1)
            lenPack1 = lenPack1.decode()
            if not lenPack1.isnumeric():
                raise Exception("packet is corrupt")
            lenPack1 = int(lenPack1)
            pack1 = rest[:lenPack1]

            dataList = pack1.split(b'#', 4)
            try:
                n = int(dataList[0])
                fps = float(dataList[3])
            except Exception:
                raise Exception("Packet is corrupt")  # discard
            if n <= self.lastRead:
                raise Exception("Packet too old")

            self.mainBuf.append((n, data))
            self.fpsBuf.append((n, fps))

            self.setFPS(self.getMaxFps())

            if self.sort:
                self.mainBuf.sort(key=self._sortFunction)
                self.fpsBuf.sort(key=self._sortFunction)

    def _writeV0(self, data):
        ''' Implements writing into the buffer as version 0 '''
        with self.mutex:
            if len(self.mainBuf) >= 2*self.size:
                raise Exception("buffer is full")

            dataList = data.split(b'#', 4)
            try:
                n = int(dataList[0])
                fps = float(dataList[3])
            except Exception:
                raise Exception("Packet is corrupt")  # discard
            if n <= self.lastRead:
                raise Exception("Packet too old")
            self.mainBuf.append((n, data))
            self.fpsBuf.append((n, fps))

            self.setFPS(self.getMaxFps())

            if self.sort:
                self.mainBuf.sort(key=self._sortFunction)

    def write(self, data):
        '''
        Insert element in the buffer, and sort the buffer itself
        Raises exception if the buffer is full
        '''

        if self.version == 0:
            self._writeV0(data)
        elif self.version == 1:
            self._writeV1(data)
        else:
            raise Exception("Buffer version incorrect")

    def _readV1(self):
        ''' Implements reading from the buffer with version 1 '''
        with self.mutex:
            data = self.mainBuf[0] # not popped yet
            n = data[0]
            data = data[1]
                
            lenPack1, rest = data.split(b' ', 1)
            lenPack1 = lenPack1.decode()
            if not lenPack1.isnumeric():
                raise Exception("packet is corrupt")
            lenPack1 = int(lenPack1)
            pack1 = rest[:lenPack1]

            lenPack2, pack2 = rest[lenPack1 + 1:].split(b' ', 1)
            lenPack2 = lenPack2.decode()
            if not lenPack2.isnumeric():
                raise Exception("packet is corrupt")
            lenPack2 = int(lenPack2)

            pack = pack1
            if self.lastRead < n - 1 and lenPack2 > 0:
                pack = pack2
                self.lastRead = n - 1
            else:
                self.mainBuf.pop(0)
                self.fpsBuf.pop(0)
                self.lastRead = n
            return pack

    def _readV0(self):
        ''' Implements reading from the buffer with version 0 '''

        with self.mutex:
            try:
                data = self.mainBuf.pop(0)
                if data[0] == self.fpsBuf[0][0]:
                    self.fpsBuf.pop(0)
            except Exception:
                raise Exception("buffer is empty")
            self.lastRead = data[0]
            return data[1]

    def read(self):
        '''
        Read first element from the buffer
        Raises an exception if buffer is empty (IndexError)
        '''
        if self.version == 0:
            return self._readV0()
        elif self.version == 1:
            return self._readV1()
        else:
            raise Exception("Buffer version incorrect")

    def readRaw(self):
        ''' Reads the raw buffer '''
        with self.mutex:
            try:
                data = self.mainBuf.pop(0)
            except Exception:
                raise Exception("buffer is empty")
            try:
                if data[0] == self.fpsBuf[0][0]:
                    self.fpsBuf.pop(0)
            except Exception:
                pass
            self.lastRead = data[0]
            return data[1]

        

    def setVersion(self, version: int):
        ''' Sets version of the buffer '''
        self.version = version

    def clear(self):
        with self.mutex:
            self.mainBuf = []

    def setFPS(self, fps):
        # check that fps is not a big number,
        # so that the buffer doesn't grow uncontrolably
        if fps > 0 and fps <= 60:
            self.size = fps * self.secs

    def isFull(self):
        return len(self.mainBuf) >= self.size


class CommunicationClass(ABC):
    '''
    Abstract class used to recieve or send frames.
    The frame reception/sending must be done
    implementing the methods:
        -   _processFrames
        -   _connectionFunction
        -   buf
    '''

    def __init__(self, bufSize) -> None:
        self.conn = None
        self.playingMutex = Lock()
        self.buf = CircularBuffer(bufSize)

    @abstractmethod
    def _processFrames(self):
        ''' Frame processing and buffer access must be done here '''
        pass

    @abstractmethod
    def _connectionFunction(self, hostName: str, hostPort: int):
        ''' The connection is created here '''
        pass

    def start(self, hostName: str, hostPort: int, version = 0):
        '''
        Start the connection with another user,
        and start receiving data
        '''
        self.setVersion(version)

        if self.conn is not None:
            print(self.conn)
            raise Exception("UDP connection already set")

        self.buf.clear()
        try:
            self._connectionFunction(hostName, hostPort)
        except Exception:
            raise Exception("Error abriendo la conexion")

        self.thread = Thread(target=self._processFrames)
        self.thread.start()

    def stop(self):
        ''' End the connection '''

        if self.conn:
            udp.closeConnection(self.conn)
            self.conn = None

    def pause(self):
        ''' Pause the processing of frames '''

        if self.conn is None:
            raise Exception("UDP connection not started")

        self.playingMutex.acquire()
        self.buf.clear()

    def play(self):
        ''' Resume the frame processing '''

        if self.conn is None:
            raise Exception("UDP connection not started")

        self.playingMutex.release()

    def clear(self):
        ''' Empties the buffer '''
        self.buf.clear()

    def setVersion(self, version: int):
        ''' Sets version of the buffer '''
        self.buf.setVersion(version)


class SendFramesClass(CommunicationClass):
    '''
    Class designed to create the send buffer, access it,
    and send the packets stored in the buffer.
    Packet insertion is done outside this class
    '''

    def __init__(self, bufSize, packetLoss: float) -> None:
        super().__init__(bufSize)
        self.packetLoss = packetLoss

    def _processFrames(self):
        '''
        Method to read from the buffer
        and send the data to the other person
        '''
        # print("1 process frames send")
        while self.conn is not None:  # conn is None when the call has ended
            with self.playingMutex:
                try:
                    data = self.buf.readRaw()
                    if np.random.rand() > self.packetLoss:
                        udp.sendInfo(self.conn, data)  # non blocking
                except Exception:
                    # print("send ", e)
                    # Espera semiactiva
                    sleep(0.01)
                    pass
        # print("0 process frames send")

    def _connectionFunction(self, hostName: str, hostPort: int):
        ''' Connection to a UDP sink, in order to send data'''
        self.conn = udp.createConnection(hostName, hostPort)


class RecvFramesClass(CommunicationClass):
    '''
    Class designed to create the revc buffer
    and store the recieved packets.
    Packet access is done outside this class
    '''

    def _processFrames(self):
        '''
        Method to receive packets from the other
        person and to store them in the buffer.
        '''
        # print("1 process frames recv")
        while self.conn is not None:  # conn is None when the call has ended
            with self.playingMutex:
                try:
                    data = udp.recvInfo(self.conn, 1)
                    # print(data)
                    self.buf.write(data)
                except Exception:
                    # print("recv ", e)
                    pass
        # print("0 process frames recv")

    def _connectionFunction(self, hostName: str, hostPort: int):
        ''' Connection to UDP source, in order to receive data '''
        self.conn = udp.createServer(hostName, hostPort)
