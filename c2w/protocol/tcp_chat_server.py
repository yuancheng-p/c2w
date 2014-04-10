# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
import logging
import util
from data_strucs import Movie, User
from packet import Packet
from tables import type_code


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
        self.users = {}  # userId: user
        self.seqNums = {}  # userId: seqNum
        self.currentId = 0 # a variable for distributing user id

        
    def connectionMade(self):
        print "A new client is connected"

    def sendPacket(self, packet):
        buf = util.packMsg(packet)
        self.transport.write(buf)
        pass
 

    def loginRequest(self, pack):
      
        if serverProxy.userExists(pack.data)==1: #test username exists
        
            if len(self.users.keys()) !== 255: # test userlist full 
                            
             # login ack
                pack.turnIntoAck()
                self.sendPacket(pack)
            
             # add user
                serverProxy.addUser(userName=pack.data, userChatRoom=MAIN_ROOM, userChatInstance=None)
                             
            else :
                print "User list is full"
                pack.turnIntoErrorPack(error_code["invalidMessage"])
                pack.userId = 0 # send back to the login failed user
                pack.seqNum = 0 # no seqNum allocated FIXME potential problems
                self.sendPacket(pack)
                return

        else :
            print "User Name Exists !"
            pack.turnIntoErrorPack(error_code["invalidMessage"])
            pack.userId = 0 # send back to the login failed user
            pack.seqNum = 0 # no seqNum allocated FIXME potential problems
            self.sendPacket(pack)
            return
            
    


    def sendMovieList(self, userId)
        #calculate the length of the movie list
        movieListPack = Packet(frg=0, ack=0, msgType=type_code["movieList"], roomType=room_type["mainRoom"],
                            seqNum=self.seqNums[userId],
                            userId=userId, destId=0, length = 13,
                            data=self.serverProxy.getMovieList())  #is it really serverProxy ??? phrasing ???
        self.sendPacket(movieListPack)

    def sendUserList(self, userId)
        #calculate the length of the user list
        userListPack = Packet(frg=0, ack=0, msgType=type_code["movieList"], roomType=room_type["mainRoom"], #main room ? what about the movie rooms?
                            seqNum=self.seqNums[userId],
                            userId=userId, destId=0, length = 13,
                            data=self.serverProxy.getUserList())
        self.sendPacket(userListPack)

        pass #is it useful ????

    def forwardMessagePack(self, pack)
    
    
        forwardMessagePack = Packet(frg=0, ack=0, msgType=type_code["messageForward"], roomType=pack.roomType,       
                                seqNum=self.seqNum, userId=pack.userId,
                                destId=pack.destId, length=len(pack.data), data=pack.data) #seqNum ??????
        self.sendPacket(forwardMessagePack)
        pass


    def dataReceived(self, data):
        """
        :param data: The message received from the server
        :type data: A string of indeterminate length

        Twisted calls this method whenever new data is received on this
        connection.
        """      
        pack = util.unpackMsg(data)
        print "###packet received: ", pack
        

        # ACK
        if pack.ack == 1:
            
            if msgType == type_code["movieList"]:
                self.sendUserList(pack.userId)
                
            if msgType == type_code["userList"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
                #send an updated userlist to everyone ???????????
            
            if msgType == type_code["privateChatRequest"]:    
                #start the privatechat (send an ack to client A)
                pass
                    
        # REQUESTS
        else:
        
           if msgType == type_code["loginRequest"]:
                self.loginRequest(pack)
                self.sendMovieList(pack.userId)

            elif msgType == type_code["disconnectRequest"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
                if pack.roomType == room_type["movieRoom"]:
                    updateUserChatroom(pack.userName, MAIN_ROOM)
                else :
                    removeUser(pack.userName)
                #sendUserList(self, userId) how to send it to everyone ???
                pass

            elif msgType == type_code["message"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
                self.forwardMessagePack(pack)

            elif msgType == type_code["roomRequest"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
                updateUserChatroom(pack.userName, MOVIE_ROOM)
                    #send an updated userlist to everyone
                pass

            elif msgType == type_code["privateChateRequest"]:
                #verify the user B is available : send him a request
                pass    

            elif msgType == type_code["leavePrivateChatRequest"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
                #forward it
                pass


            # Type non défini
            else:
                print "type not defined"
                errorMessagePack = Packet(frg=0, ack=1, msgType=type_code["errorMessage"], roomType=pack.roomType,       
                                seqNum=self.seqNum, userId=pack.userId,
                                destId=0, length = 8, data=error_code=["invalidMessage"]) #seqNum ??????
                
                    
       



















