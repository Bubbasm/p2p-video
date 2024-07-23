import socket
from utils import TCPUtil as tcp
from shared import *


class dsKeys:
    """ Keys used to access Discovery Server responses """
    nick = "nick"  # Value pointed by port is a string
    timestamp = "ts"  # Value pointed by port is a floating point
    ip = "ip_address"  # Value pointed by port is a string
    port = "port"  # Value pointed by port is an integer
    protocol = "proto"  # Value pointed by port is a list of string


def _parseResponse(response: str):
    """
    Parses response of DS server, removing first two words
    Returns a list of items
    """
    aux = response.split(" ", 2)
    if len(aux) < 3:
        return ""
    return aux[2]


def _quitAndClose(sock):
    """ Common code that closes a connection with the server """
    data = "QUIT"
    tcp.sendInfo(sock, data)
    tcp.closeConnection(sock)


def register(nick: str, passwd: str, ip: str, port: int, protos: list):
    """
    Registers user in the Discovery Server
    Returns a map with nick and timestamp
    Raises exception in case of error
    """
    serverSock = tcp.createConnection(serverName, serverPort)
    protosStr = "#".join(protos)
    data = " ".join(['REGISTER', nick, ip, str(port), passwd, protosStr])
    tcp.sendInfo(serverSock, data)
    response = _parseResponse(tcp.recvInfo(serverSock))
    _quitAndClose(serverSock)
    if not response:
        raise Exception("Wrong password")
    response = response.split(" ")
    ret = {dsKeys.nick: response[0], dsKeys.timestamp: float(response[1])}
    return ret


def query(nick: str):
    """
    Queries for a user in the Discovery Server
    Returns a map with nick, ip, port and protocol
    Note that the key value of protocol is a list of supported protocols
    Raises exception in case of error
    """
    serverSock = tcp.createConnection(serverName, serverPort)
    data = " ".join(['QUERY', nick])
    tcp.sendInfo(serverSock, data)
    response = _parseResponse(tcp.recvInfo(serverSock))
    _quitAndClose(serverSock)
    if not response:
        raise Exception("No user found")
    response = response.split(" ")
    if not response[2].isnumeric():
        raise Exception("Port is not integer")
    protos = response[3].split("#")
    ret = {
        dsKeys.nick: response[0],
        dsKeys.ip: response[1],
        dsKeys.port: int(response[2]),
        dsKeys.protocol: protos}
    return ret


def _valid_ip(address):
    """ Utilidad para reconocer si una IPv4 es válida """
    try:
        socket.inet_aton(address)
        return True
    except BaseException:
        return False


def listUsers():
    """
    Queries for a user in the Discovery Server
    Returns a list containing maps with nick, ip and port
    Raises exception in case of error
    """
    serverSock = tcp.createConnection(serverName, serverPort)
    data = 'LIST_USERS'
    tcp.sendInfo(serverSock, data)
    response = _parseResponse(tcp.recvInfo(serverSock))

    while True:
        try:
            response += tcp.recvInfo(serverSock, 0.1)
        except Exception:
            break

    _quitAndClose(serverSock)

    if not response.split(" "):  # empty string
        raise Exception("No user found")
    response = response.split(" ", 1)[1]
    # print(response)
    users = [user.split(" ") for user in response.split("#")]
    # print(users)
    ret = [
        {dsKeys.nick: user[0], dsKeys.ip: user[1], dsKeys.port: int(user[2])} 
        for user in users 
        if len(user) >= 2 and user[2].isnumeric() and _valid_ip(user[1])
        ]
    # Extra checking, like len(user) >= 2
    # A numeric value in port and a valid ip address
    return ret
