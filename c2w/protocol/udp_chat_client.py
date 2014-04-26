# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import logging
from packet import Packet
import util
from twisted.internet import reactor
from config import attempt_num, timeout
from tables import type_code, state_code
from tables import error_decode, state_decode, room_type
from c2w.main.constants import ROOM_IDS

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
        self.movieRoomId = -1  # not in movie room
        self.currentMovieRoom = None

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

        if packet.ack == 1:
            print "###sending ACK packet###:", packet
            buf = util.packMsg(packet)
            self.transport.write(buf.raw, (self.serverAddress, self.serverPort))
            return

        if packet.seqNum != self.seqNum:
            return

        print "###sending packet###:", packet
        buf = util.packMsg(packet)
        self.transport.write(buf.raw, (self.serverAddress, self.serverPort))
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
        # This method is called when user clicks "send" button of any room
        destId = 0
        if self.state == state_code["inMainRoom"]:
            roomType = room_type["mainRoom"]
            destId = 0  # for main room
        elif self.state == state_code["inMovieRoom"]:
            roomType = room_type["movieRoom"]
            destId = self.movieRoomId
        else:
            print "State error!"
            return

        messagePack = Packet(frg=0, ack=0, msgType=type_code["message"],
                            roomType=roomType, seqNum=self.seqNum,
                            userId=self.userId, destId=destId,
                            length=len(message), data=message)
        self.sendPacket(messagePack)

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
        if roomName == ROOM_IDS.MAIN_ROOM:
            joinRoomRequest = Packet(frg=0, ack=0,
                                    msgType=type_code["roomRequest"],
                                    roomType=room_type["mainRoom"],
                                    seqNum=self.seqNum, userId=self.userId,
                                    destId=0, length=0, data=None)
            self.sendPacket(joinRoomRequest)
            self.state = state_code["waitForMainRoomAck"]
            self.movieRoomId = -1
        else:
            roomId = [movie.roomId for movie in self.movieList
                                            if movie.movieName==roomName][0]
            joinRoomRequest = Packet(frg=0, ack=0,
                                    msgType=type_code["roomRequest"],
                                    roomType=room_type["movieRoom"],
                                    seqNum=self.seqNum, userId=self.userId,
                                    destId=roomId, length=0, data=None)
            self.sendPacket(joinRoomRequest)
            self.state = state_code["waitForMovieRoomAck"]
            self.currentMovieRoom = roomName
            self.movieRoomId = roomId

    def sendLeaveSystemRequestOIE(self):
        """
        Called **by the controller**  when the user
        has clicked on the leave button in the main room.
        """

        LeaveSystemRequest=Packet(frg=0, ack=0, msgType=type_code["disconnectRequest"],
                                roomType=room_type["notApplicable"],
                                seqNum=self.seqNum, userId=self.userId,
                                destId=0, length=0, data="")
        self.sendPacket(LeaveSystemRequest)

    def movieListReceived(self, pack):
        """save movieList, and send ack"""
        self.movieList = pack.data
        pack.turnIntoAck()
        self.sendPacket(pack)

    def userListReceived(self, pack):
        """ save users, and send ack"""
        self.users = pack.data
        pack.turnIntoAck()
        self.sendPacket(pack)

    def messageReceived(self, pack):
        # different action for different room type
        # find userName by id
        userName = [user.name for user in self.users if user.userId==pack.destId][0]
        if (pack.roomType == room_type["mainRoom"] or
                pack.roomType == room_type["movieRoom"]):
            self.clientProxy.chatMessageReceivedONE(userName, pack.data)
        pack.turnIntoAck()
        self.sendPacket(pack)

    def showMainRoom(self):
        """init the main room"""
        userList = util.adaptUserList(self.users)
        movieList = util.adaptMovieList(self.movieList)
        self.clientProxy.initCompleteONE(userList, movieList)

    def changeRoom(self):
        self.clientProxy.joinRoomOKONE()

    def updateUserList(self, movieName=None):
        """refresh the userList in the room"""
        userList = util.adaptUserList(self.users, movieName=movieName)
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
        print "####packet received:", pack

        # the previous packet is received
        if pack.ack == 1 and pack.seqNum == self.seqNum:
            self.seqNum += 1
            if pack.msgType == type_code["errorMessage"]:  # error handling
                print "error message received:", error_decode[pack.data]
                print "state:", state_decode[self.state]
                if self.state == state_code["loginWaitForAck"]:  # loginFailed
                    self.clientProxy.connectionRejectedONE(
                                            error_decode[pack.data])  # back to login window
                else:
                    print "unexpected error code"
            elif pack.msgType == type_code["loginRequest"]:  # wait for movieList
                self.state = state_code["loginWaitForMovieList"]
                self.userId = pack.userId  # get userId from server
            elif pack.msgType == type_code["roomRequest"]:
                if (pack.roomType == room_type["movieRoom"] and
                        self.state == state_code["waitForMovieRoomAck"]):
                    # This packet contains the ip and the port of the movie requested
                    self.state = state_code["waitForMovieRoomUserList"]
                    self.clientProxy.updateMovieAddressPort(self.currentMovieRoom,
                            pack.data["ip"], pack.data["port"])
                elif (pack.roomType == room_type["mainRoom"] and
                        self.state == state_code["waitForMainRoomAck"]):
                    self.state = state_code["waitForMainRoomUserList"]
                else:
                    print "unexpected roomrequest ACK"
            elif pack.msgType == type_code["disconnectRequest"]:
                self.clientProxy.leaveSystemOKONE()
                self.clientProxy.applicationQuit()
            else:
                print "Unexpected type of ACK packet"
            return

        # packet arrived is not an ACK packet
        if pack.seqNum == self.serverSeqNum:  # expected packet
            self.serverSeqNum += 1
        else:  # unexpected packet
            # This is perhapse a resend packet from the server if the
            # privous ACK packet is lost. The client should resend the ACK.
            print "Previous ACK might be lost, resend ACK"
            pack.turnIntoAck()
            self.sendPacket(pack)
            return

        if pack.msgType == type_code["movieList"]:
            self.movieListReceived(pack)
            self.state = state_code["loginWaitForUserList"]
        elif pack.msgType == type_code["userList"]:
            self.userListReceived(pack)
            if self.state == state_code["loginWaitForUserList"]:
                self.state = state_code["inMainRoom"]
                self.showMainRoom()
            elif self.state == state_code["inMainRoom"]:
                self.updateUserList()
            elif self.state == state_code["inMovieRoom"]:
                self.updateUserList(movieName=self.currentMovieRoom)
            elif self.state == state_code["waitForMovieRoomUserList"]:
                self.state = state_code["inMovieRoom"]
                self.changeRoom()
                self.updateUserList(movieName=self.currentMovieRoom)
            elif self.state == state_code["waitForMainRoomUserList"]:
                self.state = state_code["inMainRoom"]
                self.changeRoom()
                self.updateUserList()
            else:
                print "unexpected userList"
        elif pack.msgType == type_code["messageForward"]:
            self.messageReceived(pack)
        else:  # type not defined
            print "type not defined on client side"
