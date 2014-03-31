# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import logging
from packet import Packet
import util
from tables import type_code, error_code
from data_strucs import Movie, User
from config import attempt_num, timeout
from twisted.internet import reactor

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_server_protocol')


class c2wUdpChatServerProtocol(DatagramProtocol):

    def __init__(self, serverProxy, lossPr):
        """
        :param serverProxy: The serverProxy, which the protocol must use
            to interact with the user and movie store (i.e., the list of users
            and movies) in the server.
        :param lossPr: The packet loss probability for outgoing packets.  Do
            not modify this value!

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: serverProxy

            The serverProxy, which the protocol must use
            to interact with the user and movie store in the server.

        .. attribute:: lossPr

            The packet loss probability for outgoing packets.  Do
            not modify this value!  (It is used by startProtocol.)

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """
        self.serverProxy = serverProxy
        self.lossPr = lossPr
        self.users = {}  # userId: user
        self.seqNums = {}  # userId: seqNum
        self.clientSeqNums = {}  # userId: seqNum expected to receive
        self.currentId = 1  # a variable for distributing user id,
                            # 0 is reserved for login use
        self.movieList = []
        self.userAddrs = {}  # userId: (host, addr)
        for i in range(2):
            movieName = "The wolf of wall street"
            movie = Movie(movieName, i)
            self.movieList.append(movie)

    def startProtocol(self):
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport

    def sendPacket(self, packet, (host, port), callCount=0):
        if packet.seqNum != self.seqNums[packet.userId]:  # packet is received
            return
        print "###sending packet### : ", packet
        buf = util.packMsg(packet)
        self.transport.write(buf, (host, port))

        if packet.ack == 1:
            return

        callCount += 1
        if callCount < attempt_num:
            reactor.callLater(timeout, self.sendPacket,
                              packet, (host, port), callCount)
        else:
            print "too man tries, packet:", packet, " aborted"
            return

    def addUser(self, userName, (host, port)):
        """ add a new user into userList
        returns: -1 if server is full, otherwise a user id
        """
        # TODO check if username exist
        if len(self.users.keys()) == 255:
            # TODO Error msg: too much clients, userNotAvailable
            return -1

        # Add new user
        while self.currentId in self.users.keys() or self.currentId == 0:
            self.currentId = (self.currentId + 1) % 256

        self.users[self.currentId] = User(userName, self.currentId)
        self.seqNums[self.currentId] = 0
        self.clientSeqNums[self.currentId] = 1  # loginRequest is received
        self.userAddrs[self.currentId] = (host, port)
        return self.currentId

    def infromRefreshUserList(self):
        for userId in self.users.keys():
            self.sendUserList(userId, self.userAddrs[userId])
        pass

    def loginResponse(self, pack, (host, port)):
        """The pack is a loginRequest packet
        """
        # login ack, if login fails, addUser returns -1,
        # then the server should send an eoorMessage
        pack.userId = self.addUser(pack.data, (host, port))
        if pack.userId == -1:
            pack.turnIntoErrorPack(error_code["userNotAvailable"])
            self.sendPacket(pack, (host, port))
            return
        pack.turnIntoAck()
        self.sendPacket(pack, (host, port))

        # send movieList
        self.sendMovieList(pack.userId, (host, port))
        pass

    def sendMovieList(self, userId, (host, port)):
        length = 0
        for movie in self.movieList:
            length = length + 2 + movie.length
        movieListPack = Packet(frg=0, ack=0, msgType=3, roomType=0,
                            seqNum=self.seqNums[userId],
                            userId=userId, destId=0, length=length,
                            data=self.movieList)
        self.sendPacket(movieListPack, (host, port))
        pass

    def sendUserList(self, userId, (host, port), roomType=0):
        length = 0
        for user in self.users.values():
            length = length + 3 + user.length
        userListPack = Packet(frg=0, ack=0, msgType=type_code["userList"],
                            roomType=roomType, seqNum=self.seqNums[userId],
                            userId=userId, destId=0, length=length,
                            data=self.users)
        self.sendPacket(userListPack, (host, port))
        pass

    def datagramReceived(self, datagram, (host, port)):
        """
        :param string datagram: the payload of the UDP packet.
        :param host: the IP address of the source.
        :param port: the source port.

        Called **by Twisted** when the server has received a UDP
        packet.
        """
        pack = util.unpackMsg(datagram)
        print pack

        # the previous packet is received
        if pack.ack == 1 and pack.seqNum == self.seqNums[pack.userId]:
            self.seqNums[pack.userId] += 1
            if pack.msgType == type_code["errorMessage"]:
                pass
            if pack.msgType == type_code["AYT"]:
                pass
            if pack.msgType == type_code["movieList"]:
                #self.sendUserList(pack.userId, (host, port))
                self.infromRefreshUserList()
            if pack.msgType == type_code["userList"]:
                print "user id=", pack.userId, " login success"
            return

        # packet arrived is a request
        if (pack.userId in self.users.keys()
                and pack.seqNum != self.clientSeqNums[pack.userId]):
            print "an unexpected packet is received, aborted"
            return

        if pack.userId in self.users.keys():
            self.clientSeqNums[pack.userId] += 1

        if pack.msgType == type_code["loginRequest"]:
            self.loginResponse(pack, (host, port))
        elif pack.msgType == type_code["disconnectRequest"]:
            pass
        elif pack.msgType == type_code["message"]:
            pass
        elif pack.msgType == type_code["roomRequest"]:
            pass
        elif pack.msgType == type_code["leavePrivateChatRequest"]:
            pass
        elif pack.msgType == type_code["privateChatRequest"]:
            pass
        else:  # type not defined
            print "type not defined"
            pass

        pass
