import socket
from shared import *
from threading import Lock
from pathlib import Path


# Maximum receive data length
RECVLEN = 2**20
# Maximum queued connections
LISTENSERVERLIMIT = 1
# video file types supported (to avoid opening a file that is not a video)
extensions = ["*.mp4", "*.mpeg"]  # TODO: Añadir más
SUPPORTED_VIDEO_FILES = [('video', ext) for ext in extensions]


class TCPUtil:
    """
    Encapsulation class that contains methods for managing tcp connections
    No exceptions are handled
    """
    @staticmethod
    def createServer(serverName: str, serverPort: int):
        """
        Establishes a tcp connection to listen
        Returns a socket.
        """
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serverSocket.bind((serverName, serverPort))
        serverSocket.listen(LISTENSERVERLIMIT)
        return serverSocket

    @staticmethod
    def acceptConnection(serverSocket, time=None):
        """
        Accepts a connection
        Returns a socket.
        """
        serverSocket.settimeout(time)
        sock = serverSocket.accept()[0]
        serverSocket.settimeout(None)
        return sock

    @staticmethod
    def createConnection(hostName: str, hostPort: int):
        """
        Connects to tcp server, for instance created by createServer
        Returns a socket.
        """
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.settimeout(3)
        clientSocket.connect((hostName, hostPort))
        clientSocket.settimeout(None)
        return clientSocket

    @staticmethod
    def closeConnection(socket):
        """ Closes any tcp connection """
        socket.close()

    @staticmethod
    def sendInfo(socket, data: str):
        """ Sends data to the indicated socket """
        socket.send(data.encode())

    @staticmethod
    def recvInfo(sock, timeout=None):
        """
        Sends data to the indicated socket
        Returns retreived data
        """
        sock.settimeout(timeout)
        info = sock.recv(RECVLEN).decode()
        sock.settimeout(None)
        return info


class UDPUtil:
    """
    Encapsulation class that contains methods for managing udp connections
    No exceptions are handled
    """
    @staticmethod
    def createServer(name: str, port: int):
        """
        Establishes a udp connection to listen
        Returns a triplet as a socket. This shall be used to
        receive information
        """
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        serverSocket.bind((name, port))
        return (serverSocket, name, port)

    @staticmethod
    def createConnection(hostName: str, hostPort: int):
        """
        Creates a socket ready to send data
        Returns a triplet as a socket. This shall be used to
        send information
        """
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return (clientSocket, hostName, hostPort)

    @staticmethod
    def closeConnection(clientSocketTriplet):
        """ Closes any udp connection """
        sock = clientSocketTriplet[0]
        sock.close()

    @staticmethod
    def sendInfo(clientSocketTriplet, data: bytes):
        """ Sends data to the indicated socket """
        clientSocket = clientSocketTriplet[0]
        # print(data, " send")
        clientSocket.sendto(
            data,
            (clientSocketTriplet[1], clientSocketTriplet[2])
        )

    @staticmethod
    def recvInfo(serverSocketTriplet, time=None):
        """
        Sends data to the indicated socket
        Returns retreived data
        """
        serverSocket = serverSocketTriplet[0]
        serverSocket.settimeout(time)
        data, _ = serverSocket.recvfrom(RECVLEN)
        serverSocket.settimeout(None)
        return data
