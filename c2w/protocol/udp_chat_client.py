# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import logging
from packet import Packet
import util
from twisted.internet import reactor
from config import attempt_num, timeout
from tables import type_code, type_decode, state_code
from tables import error_decode, state_decode

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_client_protocol')


class c2wUdpChatClientProtocol(DatagramProtocol):

    def __init__(self, serverAddress, serverPort, clientProxy, lossPr):
        """
        :param serverAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param serverPort: The port number used by the c2w server,
            given by the user.
        :param clientProxy: The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attributes:

        .. attribute:: serverAddress

            The IP address (or the name) of the c2w server.

        .. attribute:: serverPort

            The port number used by the c2w server.

        .. attribute:: clientProxy

            The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        .. attribute:: lossPr

            The packet loss probability for outgoing packets.  Do
            not modify this value!  (It is used by startProtocol.)

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """

        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.clientProxy = clientProxy
        self.lossPr = lossPr
        #self.roomType = [3]  # user's current room types
        self.seqNum = 0  # sequence number for the next packet to be sent
        self.serverSeqNum = 0  # sequence number of the next not ack packet
        self.userId = 0
        self.userName = ""
        self.packReceived = False
        self.movieList = []
        self.users = []  # userId: user
        self.state = state_code["disconnected"]

    def startProtocol(self):
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport

    def sendPacket(self, packet, callCount=0):
        """
        param packet: Packet object
        param callCount: only used for the timeout mechanism.
        """
        # the packet is received
        if packet.ack != 1 and packet.seqNum != self.seqNum:
            return
        print "###sending packet###:", packet
        if packet.ack != 1:
            print "packet.seqNum=", packet.seqNum, " self.seqNum=", self.seqNum
        buf = util.packMsg(packet)
        self.transport.write(buf, (self.serverAddress, self.serverPort))

        if packet.ack == 1:
            return

        callCount += 1
        if callCount < attempt_num:
            reactor.callLater(timeout, self.sendPacket, packet, callCount)
        else:
            print "too many tries, packet:", packet," aborted"
            return

    def sendLoginRequestOIE(self, userName):
        """
        :param string userName: The user name that the user has typed.

        The controller calls this function as soon as the user clicks on
        the login button.
        """
        moduleLogger.debug('loginRequest called with username=%s', userName)

        self.roomType = 3
        self.seqNum = 0  # reset seqNum
        self.userId = 0  # use reserved userId when login
        self.userName = userName

        loginRequest = Packet(frg=0, ack=0, msgType=0,
                    roomType=self.roomType, seqNum=self.seqNum,
                    userId=self.userId, destId=0, length=len(userName),
                    data=userName)
        self.sendPacket(loginRequest)
        self.state = state_code["loginWaitForAck"]


    def sendChatMessageOIE(self, message):
        """
        :param message: The text of the chat message.
        :type message: string

        Called **by the controller**  when the user has decided to send
        a chat message

        .. note::
           This is the only function handling chat messages, irrespective
           of the room where the user is.  Therefore it is up to the
           c2wChatClientProctocol or to the server to make sure that this
           message is handled properly, i.e., it is shown only by the
           client(s) who are in the same room.
        """
        pass

    def sendJoinRoomRequestOIE(self, roomName):
        """
        :param roomName: The room name (or movie title.)

        Called **by the controller**  when the user
        has clicked on the watch button or the leave button,
        indicating that she/he wants to change room.

        .. warning:
            The controller sets roomName to
            c2w.main.constants.ROOM_IDS.MAIN_ROOM when the user
            wants to go back to the main room.
        """
        pass

    def sendLeaveSystemRequestOIE(self):
        """
        Called **by the controller**  when the user
        has clicked on the leave button in the main room.
        """
        pass

    def movieListReceived(self, pack):
        """save movieList, and send ack"""
        self.movieList = pack.data
        pack.turnIntoAck()
        self.sendPacket(pack)
        pass

    def userListReceived(self, pack):
        """ save users, and send ack"""
        self.users = pack.data
        pack.turnIntoAck()
        self.sendPacket(pack)
        pass

    def messageReceived(self, pack):
        pass

    def aytReceived(self, pack):
        pass

    def abortReceivedPack(self, pack):
        pass

    def showMainRoom(self):
        userList = util.adaptUserList(self.users)
        movieList = util.adaptMovieList(self.movieList)
        self.clientProxy.initCompleteONE(userList, movieList)
        pass

    def refreshMainRoom(self):
        userList = util.adaptUserList(self.users)
        self.clientProxy.setUserListONE(userList)

    def datagramReceived(self, datagram, (host, port)):
        """
        :param string datagram: the payload of the UDP packet.
        :param host: the IP address of the source.
        :param port: the source port.

        Called **by Twisted** when the client has received a UDP
        packet.
        """
        pack = util.unpackMsg(datagram)
        print pack

        # the previous packet is received
        if pack.ack == 1 and pack.seqNum == self.seqNum:
            self.seqNum += 1
            if pack.msgType == type_code["errorMessage"]:  # error handling
                print "error message received:", error_decode[pack.data]
                print "state:", state_decode[self.state]
                if self.state == state_code["loginWaitForAck"]:  # loginFailed
                    self.clientProxy.connectionRejectedONE(
                                            error_decode[pack.data])
            if pack.msgType == type_code["loginRequest"]:  # wait for movieList
                self.state = state_code["loginWaitForMovieList"]
                self.userId = pack.userId  # get userId from server
                pass
            return

        # packet arrived is not an ACK packet
        if pack.seqNum != self.serverSeqNum:
            print "received an unexpected packet, aborted"
            return

        self.serverSeqNum += 1
        if pack.msgType == type_code["movieList"]:
            self.movieListReceived(pack)
            self.state = state_code["loginWaitForUserList"]
        elif pack.msgType == type_code["userList"]:
            self.userListReceived(pack)
            if self.state == state_code["loginWaitForUserList"]:
                self.state = state_code["inMainRoom"]
                self.showMainRoom()
            elif self.state == state_code["inMainRoom"]:
                self.refreshMainRoom()
        elif pack.msgType == type_code["messageForward"]:
            # TODO
            self.messageReceived(pack)
        elif pack.msgType == type_code["AYT"]:
            # TODO
            self.aytReceived(pack)
        else:  # type not defined
            print "type not defined on client side"
            pass
        pass
