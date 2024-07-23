from utils import TCPUtil as tcp
from shared import *


class controlKeys:
    """ Keys used to access Calling responses """
    nick = "nick"
    port = "port"


def _parseResponse(response: str):
    """
    Parses response of control command output, removing first word
    Returns a list of items
    """
    return response.split(" ")[1:]


def calling(nick: str, srcUDPPort: int, userIP: str, userPort: int, proto = "V0"):
    """
    Calls a user self-identifying as given nickname
    Returns a map with nick and port
    This port is the one opened by the user to create a call
    Raises exception if the user is already in a call
    or the call was denied
    """
    clientSock = tcp.createConnection(userIP, int(userPort))
    data = " ".join(['CALLING', nick, str(srcUDPPort)])
    if proto != "V0":
        data += " " + proto 
    tcp.sendInfo(clientSock, data)
    try:
        response = _parseResponse(tcp.recvInfo(clientSock, 10))
    except Exception:
        tcp.closeConnection(clientSock)
        raise Exception("Usuario no contesta")
    tcp.closeConnection(clientSock)
    if not response:  # Already in a call
        raise Exception("Llamada ocupada")
    if len(response) == 1:  # Call declined
        raise Exception("Llamada rechazada")
    # Call accepted
    if str(response[1]).isnumeric():
        ret = {controlKeys.nick: response[0], controlKeys.port: int(response[1])}
        return ret
    raise Exception("Puerto inválido")



def callAccept(sock, nick: str, port: int):
    """ Wrapper function to accept a call """
    data = "CALL_ACCEPTED " + nick + " " + str(port)
    tcp.sendInfo(sock, data)


def callDeny(sock, nick: str):
    """ Wrapper function to deny a call """
    data = "CALL_DENIED " + nick
    tcp.sendInfo(sock, data)


def callBusy(sock):
    """ Wrapper function to ignore a call """
    data = "CALL_BUSY"
    tcp.sendInfo(sock, data)


def _callRequest(userIP: str, userPort: int, data: str):
    """ Auxiliary function to avoid repeating code """
    if userIP == "" or userPort == 0:
        return
    clientSock = tcp.createConnection(userIP, int(userPort))
    tcp.sendInfo(clientSock, data)
    tcp.closeConnection(clientSock)


def callHold(nick: str, userIP: str, userPort: int):
    """ Sends request for call hold """
    data = " ".join(['CALL_HOLD', nick])
    _callRequest(userIP, userPort, data)


def callResume(nick: str, userIP: str, userPort: int):
    """ Sends request for call resume """
    data = " ".join(['CALL_RESUME', nick])
    _callRequest(userIP, userPort, data)


def callEnd(nick: str, userIP: str, userPort: int):
    """ Sends request for call resume """
    data = " ".join(['CALL_END', nick])
    _callRequest(userIP, userPort, data)
