# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
import logging
from frame_handler import FrameHandler
import util
from c2w.main.constants import ROOM_IDS
from packet import Packet
from tables import state_code, type_code
from tables import error_decode, state_decode, room_type


logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.tcp_chat_client_protocol')


class c2wTcpChatClientProtocol(Protocol):

    def __init__(self, clientProxy, serverAddress, serverPort):
        """
        :param clientProxy: The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.
        :param serverAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param serverPort: The port number used by the c2w server,
            given by the user.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: clientProxy

            The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        .. attribute:: serverAddress

            The IP address (or the name) of the c2w server.

        .. attribute:: serverPort

            The port number used by the c2w server.

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """
        self.serverAddress = serverAddress
        self.serverPort = serverPort
        self.clientProxy = clientProxy
        self.frameHandler = FrameHandler()

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

    def sendPacket(self, packet):
        """
        param packet: Packet object
        param callCount: only used for the timeout mechanism.
        """
        if packet.ack == 1:
            print "###sending ACK packet###:", packet
            buf = util.packMsg(packet)
            self.transport.write(buf.raw)
            return

        if packet.seqNum != self.seqNum:
            return

        print "###sending packet###:", packet
        buf = util.packMsg(packet)
        self.transport.write(buf.raw)

    def userListReceived(self, pack):
        """ save users, and send ack"""
        self.users = pack.data
        pack.turnIntoAck()
        self.sendPacket(pack)

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

    def movieListReceived(self, pack):
        """save movieList, and send ack"""
        self.movieList = pack.data
        pack.turnIntoAck()
        self.sendPacket(pack)

    def messageReceived(self, pack):
        # different action for different room type
        # find username by id
        userName = [user.name for user in self.users if user.userId==pack.destId][0]
        if (pack.roomType == room_type["mainRoom"] or
                pack.roomType == room_type["movieRoom"]):
            self.clientProxy.chatMessageReceivedONE(userName, pack.data)
        pack.turnIntoAck()
        self.sendPacket(pack)

    def dataReceived(self, data):
        """
        :param data: The message received from the server
        :type data: A string of indeterminate length

        Twisted calls this method whenever new data is received on this
        connection.
        """
        print "#### data received!"
        packList = self.frameHandler.extractPackets(data)

        for pack in packList:
            print "## packet received:", pack
            # the previous packet is received
            if pack.ack == 1 and pack.seqNum == self.seqNum:
                self.seqNum += 1
                if pack.msgType == type_code["errorMessage"]:
                    print "error message received:", error_decode[pack.data]
                    print "state:", state_decode[self.state]
                    if self.state == state_code["loginWaitForAck"]:  # loginFailed
                        # prompt error message
                        self.clientProxy.connectionRejectedONE(
                                                error_decode[pack.data])
                if pack.msgType == type_code["loginRequest"]:
                    self.state = state_code["loginWaitForMovieList"]
                    self.userId = pack.userId  # get distributed userId
                if pack.msgType == type_code["roomRequest"]:
                    if (pack.roomType == room_type["movieRoom"] and
                            self.state == state_code["waitForMovieRoomAck"]):
                        # This packet contains the ip and the port of the movie requested
                        self.state = state_code["waitForMovieRoomUserList"]
                        self.clientProxy.updateMovieAddressPort(self.currentMovieRoom,
                                pack.data["ip"], pack.data["port"])
                    elif (pack.roomType == room_type["mainRoom"] and
                            self.state == state_code["waitForMainRoomAck"]):
                        self.state = state_code["waitForMainRoomUserList"]
                if pack.msgType == type_code["disconnectRequest"]:
                    self.clientProxy.leaveSystemOKONE()
                    self.clientProxy.applicationQuit()
                continue

            # Packet lost will never happen
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
                    self.updateUserList()
                elif self.state == state_code["inMovieRoom"]:
                    self.updateUserList(movieName=self.currentMovieRoom)
                    pass
                elif self.state == state_code["waitForMovieRoomUserList"]:
                    self.state = state_code["inMovieRoom"]
                    self.changeRoom()
                    self.updateUserList(movieName=self.currentMovieRoom)
                elif self.state == state_code["waitForMainRoomUserList"]:
                    self.state = state_code["inMainRoom"]
                    self.changeRoom()
                    self.updateUserList()
            elif pack.msgType == type_code["messageForward"]:
                self.messageReceived(pack)
            else:  # type not defined
                print "type not defined on client side"
