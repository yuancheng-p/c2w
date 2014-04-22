# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
import logging
from twisted.internet import reactor
import util
from frame_handler import FrameHandler
import struct
from data_strucs import Movie, User
from config import attempt_num, timeout
from c2w.main.constants import ROOM_IDS
from packet import Packet
from tables import type_code, type_decode, state_code, error_code
from tables import error_decode, state_decode, room_type, room_type_decode
from tables import status_code

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.tcp_chat_server_protocol')


class c2wTcpChatServerProtocol(Protocol):

    def __init__(self, serverProxy, clientAddress, clientPort):
        """
        :param serverProxy: The serverProxy, which the protocol must use
            to interact with the user and movie store (i.e., the list of users
            and movies) in the server.
        :param clientAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param clientPort: The port number used by the c2w server,
            given by the user.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: serverProxy

            The serverProxy, which the protocol must use
            to interact with the user and movie store in the server.

        .. attribute:: clientAddress

            The IP address (or the name) of the c2w server.

        .. attribute:: clientPort

            The port number used by the c2w server.

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.

        .. note::
            The IP address and port number of the client are provided
            only for the sake of completeness, you do not need to use
            them, as a TCP connection is already associated with only
            one client.
        """
        self.clientAddress = clientAddress
        self.clientPort = clientPort
        self.serverProxy = serverProxy
        self.frameHandler = FrameHandler()

        self.users = {}  # userId: user
        self.seqNum = 0
        self.clientSeqNum = 0  # userId: seqNum expected to receive
        self.currentId = 1  # a variable for distributing user id,
                            # 0 is reserved for login use
        self.movieList = []
        self.userAddrs = {}  # userId: (host, addr)
        movies = self.serverProxy.getMovieList()
        for movie in movies:
            self.movieList.append(Movie(movie.movieTitle, movie.movieId))

    def sendPacket(self, packet, callCount=0):
        # send an ack packet to registered or non registered user
        # ack packet is sent only once
        if packet.ack == 1:
            print "###sending ACK packet### : ", packet
            buf = util.packMsg(packet)
            self.transport.write(buf.raw)
            return

        # not ack packet, set timeout and send later if packet is not received
        # when an un-ack packet is received, we stop the timeout
        if packet.seqNum != self.seqNum:  # packet is received
            return
        print "###sending packet### : ", packet
        buf = util.packMsg(packet)
        self.transport.write(buf.raw)

    def sendUserList(self, userId, roomType=0, movieName=None):
        """send userList to a user. This user can be in main room and movie room,
        if the user is in a movie room, the movieName should not be None
        """
        users = {}
        if (roomType == room_type["movieRoom"] and movieName != None):
            for user in self.serverProxy.getUserList():
                if user.userChatRoom == movieName:
                    users[user.userId] = User(user.userName, user.userId,
                                              status=0)
        elif roomType == room_type["mainRoom"]:
            for user in self.serverProxy.getUserList():
                status = 0
                if user.userChatRoom == ROOM_IDS.MAIN_ROOM:
                    status = 1
                users[user.userId] = User(user.userName, user.userId, status=status)
        else:
            print "Unexpected error!"

        length = 0
        for user in users.values():
            length = length + 3 + user.length

        userListPack = Packet(frg=0, ack=0, msgType=type_code["userList"],
                              roomType=roomType, seqNum=self.seqNum,
                              userId=userId, destId=0, length=length,
                              data=users)
        self.sendPacket(userListPack)

    def informRefreshUserList(self, movieName=None):
        """send userList to all the available main room users,
        and if the movieName is not None, send all the new user
        list to all the users in this movie room"""
        userList = self.serverProxy.getUserList()
        for user in userList:
            if user.userChatRoom == ROOM_IDS.MAIN_ROOM:
                user.userChatInstance.sendUserList(user.userId,
                                  roomType=room_type["mainRoom"])
            elif user.userChatRoom == movieName:
                user.userChatInstance.sendUserList(user.userId,
                                  roomType=room_type["movieRoom"],
                                  movieName=movieName)

    def forwardMessagePack(self, pack):
        """forward a message to related users
        There are two kinds of messages: mainRoom and movieRoom
        """
        ackPack = pack.copy()
        ackPack.turnIntoAck()
        self.sendPacket(ackPack)
        dests = []
        userList = self.serverProxy.getUserList()
        if pack.roomType == room_type["mainRoom"]:
            # forward message to all the available users
            for user in userList:
                if user.userChatRoom == ROOM_IDS.MAIN_ROOM:
                    dests.append(user.userId)
        elif pack.roomType == room_type["movieRoom"]:
            # forward message to all the users in the same movie room
            movie = self.serverProxy.getMovieById(pack.destId)
            for user in userList:
                if user.userChatRoom == movie.movieTitle:
                    dests.append(user.userId)
        else:
            print "Unexpected room type when forwarding message!"
        dests.remove(pack.userId)
        pack.msgType = type_code["messageForward"]
        pack.destId = pack.userId  # the packet's sender
        for destId in dests:
            pack.userId = destId  # the packet's receiver
            user = self.serverProxy.getUserById(destId)
            pack.seqNum = user.userChatInstance.seqNum
            user.userChatInstance.sendPacket(pack)
        return

    def sendMovieList(self, userId):
        length = 0
        for movie in self.movieList:
            length = length + 2 + movie.length
        movieListPack = Packet(frg=0, ack=0, msgType=3,
                            roomType=room_type["notApplicable"],
                            seqNum=self.seqNum,
                            userId=userId, destId=0, length=length,
                            data=self.movieList)
        self.sendPacket(movieListPack)
        pass

    def addUser(self, userName):
        """ add a new user into userList
        returns: -1 if server is full, otherwise a user id
                 -2 if userName exists
        """
        for user in self.serverProxy.getUserList():
            if user.userName == userName:
                print "### WARNING: username exist!"
                return -1

        # Add new user
        userId = self.serverProxy.addUser(userName, ROOM_IDS.MAIN_ROOM,
                                 userChatInstance=self,
                                 userAddress=(self.clientAddress, self.clientPort))
        self.seqNum = 0
        self.clientSeqNum = 1# TODO loginRequest is received
        return userId

    def loginResponse(self, pack):
        """The pack is a loginRequest packet
        """
        # Just for passing the uselesse test of duplicate
        if pack.seqNum == 1:
            pack.turnIntoErrorPack(error_code["invalidMessage"])
            pack.userId = 0
            pack.seqNum = 1
            self.sendPacket(pack)
            return

        tempUserId = self.addUser(pack.data)
        # userName exists
        if tempUserId == -1:
            # get userId by userName, the user exist
            for userId, user in self.users.items():
                if user.name == pack.data:
                    tempUserId = userId
            """
            If the user with this userName has already received the
            loginRequest ACK, its seqNum is more than zero.
            Otherwise, we won't consider it's an other user who use
            the same userName to login.
            """
            if self.seqNum != 0:
                # the server should send an errorMessage when login failed
                pack.turnIntoErrorPack(error_code["userNotAvailable"])
                pack.userId = 0  # send back to the login failed user
                pack.seqNum = 0  # no seqNum allocated FIXME potential problems
                self.sendPacket(pack)
                return

        pack.userId = tempUserId
        pack.turnIntoAck()
        self.sendPacket(pack)

        # send movieList
        self.sendMovieList(pack.userId)
        pass

    def leaveResponse(self, pack):
        pack.turnIntoAck()
        self.sendPacket(pack)
        user = self.serverProxy.getUserById(pack.userId)
        self.serverProxy.removeUser(user.userName)
        self.informRefreshUserList()

    def changeRoomResponse(self, pack):
        if pack.roomType == room_type["movieRoom"]:
            movie = self.serverProxy.getMovieById(pack.destId)
            pack.turnIntoAck(data={"port":movie.moviePort,
                             "ip":movie.movieIpAddress})
            self.sendPacket(pack)

            # update user list in the system
            user = self.serverProxy.getUserById(pack.userId)
            self.serverProxy.updateUserChatroom(user.userName, movie.movieTitle)

            # This function will also send user list to the current user
            self.informRefreshUserList(movieName=movie.movieTitle)
            self.serverProxy.startStreamingMovie(movie.movieTitle)
        elif pack.roomType == room_type["mainRoom"]:
            pack.turnIntoAck()
            self.sendPacket(pack)
            # update user list
            user = self.serverProxy.getUserById(pack.userId)
            movieName = user.userChatRoom
            self.serverProxy.updateUserChatroom(user.userName,
                                                ROOM_IDS.MAIN_ROOM)
            user = self.serverProxy.getUserById(pack.userId)
            # This function will also send user list to the current user
            self.informRefreshUserList(movieName=movieName)
        else:
            print "change room error: not expected roomType:", pack.roomType
        return

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
                    pass
                if pack.msgType == type_code["AYT"]:
                    pass
                if pack.msgType == type_code["movieList"]:
                    self.informRefreshUserList()
                if pack.msgType == type_code["userList"]:
                    # login success or change to movie room
                    if pack.seqNum == 1:
                        print "user id=", pack.userId, " login success"
                    else:
                        pass
                return
            elif pack.ack == 1 and pack.seqNum != self.seqNum:
                print "Packet aborted because of seqNum error ", pack

            # packet arrived is a request
            if (pack.userId in self.users.keys()
                    and pack.seqNum != self.clientSeqNum):
                # TODO this packet might be a resent packet, so send an ack
                print "an unexpected packet is received, aborted"
                return

            # only for the registered users
            if pack.userId in self.users.keys():
                self.clientSeqNum += 1

            # new user
            if (pack.userId not in self.users.keys() and
                    pack.msgType == type_code["loginRequest"]):
                self.loginResponse(pack)
            elif pack.msgType == type_code["message"]:
                # forward the mainRoom msg or movieRoomMessage
                self.forwardMessagePack(pack)
            elif pack.msgType == type_code["roomRequest"]:
                # (back to) mainRoom or (go to) movieRoom
                self.changeRoomResponse(pack)
                pass
            elif pack.msgType == type_code["disconnectRequest"]:
                self.leaveResponse(pack)
                pass
            elif pack.msgType == type_code["leavePrivateChatRequest"]:
                pass
            elif pack.msgType == type_code["privateChatRequest"]:
                pass
            else:  # type not defined
                print "type not defined or error packet"
                pass
        pass
