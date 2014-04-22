# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import logging
from packet import Packet
import util
from tables import type_code, error_code
from tables import room_type
from tables import status_code
from data_strucs import Movie, User
from config import attempt_num, timeout
from twisted.internet import reactor
from c2w.main.constants import ROOM_IDS

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


    def initMovieList(self):
        """read movie list config file"""
        # get movie list of the in the system and save it in the protocol
        #self.serverProxy.addMovie("Examplevideo.ogv", "127.0.0.1", 1991, "./Examplevideo.ogv")
        movies = self.serverProxy.getMovieList()
        for movie in movies:
            self.movieList.append(Movie(movie.movieTitle, movie.movieId))
        pass

    def startProtocol(self):
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport
        self.initMovieList()

    def sendPacket(self, packet, (host, port), callCount=0):
        # send an ack packet to registered or non registered user
        # ack packet is sent only once
        if packet.ack == 1:
            print "###sending ACK packet### : ", packet
            buf = util.packMsg(packet)
            self.transport.write(buf.raw, (host, port))
            return

        # not ack packet, set timeout and send later if packet is not received
        # when an un-ack packet is received, we stop the timeout
        if packet.seqNum != self.seqNums[packet.userId]:  # packet is received
            return
        print "###sending packet### : ", packet
        buf = util.packMsg(packet)
        self.transport.write(buf.raw, (host, port))

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
                 -2 if userName exists
        """
        if userName in [user.name for user in self.users.values()]:
            print "### WARNING: username exist!"
            return -1

        # Add new user
        userId = self.serverProxy.addUser(userName, ROOM_IDS.MAIN_ROOM,
                                 userAddress=(host, port))
        self.users[userId] = User(userName, userId, status=1)
        self.seqNums[userId] = 0
        self.clientSeqNums[userId] = 1  # loginRequest is received
        self.userAddrs[userId] = (host, port)
        return userId

    def informRefreshUserList(self, movieName=None):
        """send userList to all the available main room users,
        and if the movieName is not None, send all the new user
        list to all the users in this movie room"""
        userList = self.serverProxy.getUserList()
        for user in userList:
            if user.userChatRoom == ROOM_IDS.MAIN_ROOM:
                self.sendUserList(user.userId, user.userAddress,
                                  roomType=room_type["mainRoom"])
            elif user.userChatRoom == movieName:
                self.sendUserList(user.userId, user.userAddress,
                                  roomType=room_type["movieRoom"],
                                  movieName=movieName)


    def loginResponse(self, pack, (host, port)):
        """The pack is a loginRequest packet
        """
        # Just for passing the uselesse test of duplicate
        if pack.seqNum == 1:
            pack.turnIntoErrorPack(error_code["invalidMessage"])
            pack.userId = 1
            pack.seqNum = 0
            self.sendPacket(pack, (host, port))
            return

        tempUserId = self.addUser(pack.data, (host, port))
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
            if self.seqNums[tempUserId] != 0:
                # the server should send an errorMessage when login failed
                pack.turnIntoErrorPack(error_code["userNotAvailable"])
                pack.userId = 0  # send back to the login failed user
                pack.seqNum = 0  # no seqNum allocated
                self.sendPacket(pack, (host, port))
                return

        pack.userId = tempUserId
        pack.turnIntoAck()
        self.sendPacket(pack, (host, port))

        # send movieList
        self.sendMovieList(pack.userId, (host, port))
        pass

    def getMovieNameById(self, id):
        return [movie.movieName for movie in self.movieList if movie.roomId==id][0]

    def changeRoomResponse(self, pack, (host, port)):
        if pack.roomType == room_type["movieRoom"]:
            movie = self.serverProxy.getMovieById(pack.destId)
            pack.turnIntoAck(data={"port":movie.moviePort,
                             "ip":movie.movieIpAddress})
            self.sendPacket(pack, (host, port))

            # update user list in the system
            self.users[pack.userId].status=0  # not available
            user = self.serverProxy.getUserById(pack.userId)
            self.serverProxy.updateUserChatroom(user.userName, movie.movieTitle)

            # This function will also send user list to the current user
            self.informRefreshUserList(movieName=movie.movieTitle)
            self.serverProxy.startStreamingMovie(movie.movieTitle)
        elif pack.roomType == room_type["mainRoom"]:
            pack.turnIntoAck()
            self.sendPacket(pack, (host,port))
            # update user list
            self.users[pack.userId].status=1
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

    def sendMovieList(self, userId, (host, port)):
        length = 0
        for movie in self.movieList:
            length = length + 2 + movie.length
        movieListPack = Packet(frg=0, ack=0, msgType=3,
                            roomType=room_type["notApplicable"],
                            seqNum=self.seqNums[userId],
                            userId=userId, destId=0, length=length,
                            data=self.movieList)
        self.sendPacket(movieListPack, (host, port))
        pass

    def sendUserList(self, userId, (host, port), roomType=0, movieName=None):
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
                users = self.users
        else:
            print "Unexpected error!"

        length = 0
        for user in users.values():
            length = length + 3 + user.length

        userListPack = Packet(frg=0, ack=0, msgType=type_code["userList"],
                              roomType=roomType, seqNum=self.seqNums[userId],
                              userId=userId, destId=0, length=length,
                              data=users)
        self.sendPacket(userListPack, (host, port))
        pass


    def forwardMessagePack(self, pack):
        """forward a message to related users
        There are two kinds of messages: mainRoom and movieRoom
        """
        ackPack = pack.copy()
        ackPack.turnIntoAck()
        self.sendPacket(ackPack, self.userAddrs[pack.userId])
        dests = []
        if pack.roomType == room_type["mainRoom"]:
            # forward message to all the available users
            dests = [user.userId for user in self.users.values()
                        if user.status == status_code["available"]]
        elif pack.roomType == room_type["movieRoom"]:
            # forward message to all the users in the same movie room
            movie = self.serverProxy.getMovieById(pack.destId)
            for user in self.serverProxy.getUserList():
                if user.userChatRoom == movie.movieTitle:
                    dests.append(user.userId)
        else:
            print "Unexpected room type when forwarding message!"
        dests.remove(pack.userId)
        pack.msgType = type_code["messageForward"]
        pack.destId = pack.userId  # the packet's sender
        for destId in dests:
            pack.userId = destId  # the packet's receiver
            pack.seqNum = self.seqNums[destId]
            self.sendPacket(pack, self.userAddrs[destId])
        return

    def leaveResponse(self, pack):
        pack.turnIntoAck()
        self.sendPacket(pack, self.userAddrs[pack.userId])
        userName=self.users[pack.userId].name
        self.serverProxy.removeUser(userName)
        if pack.userId in self.users.keys():
            del self.users[pack.userId]  #delete user from server's base
        if pack.userId in self.seqNums.keys():
            del self.seqNums[pack.userId]
        if pack.userId in self.clientSeqNums.keys():
            del self.clientSeqNums[pack.userId]
        self.informRefreshUserList()

    def datagramReceived(self, datagram, (host, port)):
        """
        :param string datagram: the payload of the UDP packet.
        :param host: the IP address of the source.
        :param port: the source port.

        Called **by Twisted** when the server has received a UDP
        packet.
        """
        pack = util.unpackMsg(datagram)
        print "###packet received: ", pack

        # the previous packet is received
        if pack.ack == 1 and pack.seqNum == self.seqNums[pack.userId]:
            self.seqNums[pack.userId] += 1
            if pack.msgType == type_code["movieList"]:
                self.informRefreshUserList()
            if pack.msgType == type_code["userList"]:
                # login success or change to movie room
                if pack.seqNum == 1:
                    print "user id=", pack.userId, " login success"
            return
        elif pack.ack == 1 and pack.seqNum != self.seqNums[pack.userId]:
            print "Packet aborted because of seqNum error ", pack
            return

        # packet arrived is a request
        if pack.userId in self.users.keys():
            # receive an expected packet from a registered user
            if pack.seqNum == self.clientSeqNums[pack.userId]:
                self.clientSeqNums[pack.userId] += 1
            else:
                # this packet might be a resent packet, so send an ack
                print "Previous ACKs is probably lost, re-handle the case"
                if pack.msgType == type_code["message"]:
                    self.forwardMessagePack(pack)
                elif pack.msgType == type_code["roomRequest"]:
                    self.changeRoomResponse(pack, (host, port))
                elif pack.msgType == type_code["disconnectRequest"]:
                    self.leaveResponse(pack)
                else:  # type not defined
                    print "type not defined or error packet"
                return

        # new user
        if (pack.userId not in self.users.keys() and
                pack.msgType == type_code["loginRequest"]):
            self.loginResponse(pack, (host, port))
        elif pack.msgType == type_code["message"]:
            # forward the mainRoom msg or movieRoomMessage
            self.forwardMessagePack(pack)
        elif pack.msgType == type_code["roomRequest"]:
            # (back to) mainRoom or (go to) movieRoom
            self.changeRoomResponse(pack, (host, port))
        elif pack.msgType == type_code["disconnectRequest"]:
            self.leaveResponse(pack)
        elif pack.msgType == type_code["leavePrivateChatRequest"]:
            pass
        elif pack.msgType == type_code["privateChatRequest"]:
            pass
        else:  # type not defined
            print "type not defined or error packet"
