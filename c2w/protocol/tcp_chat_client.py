# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
import logging
import util
from data_strucs import Movie, User
from packet import Packet
from tables import type_code, room_type

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.tcp_chat_client_protocol')


class c2wTcpChatClientProtocol(Protocol):

    #def connectionMade(self):
    #    """
    #    The Graphical User Interface (GUI) needs this function to know
     #   when to display the request window.
#
     #   DO NOT MODIFY IT.
     #   """
     #   print 'connection success!'
#
        #self.clientProxy.connectionSuccess()


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
        self.roomType = 3  # user's current room types
        self.seqNum = 0  # sequence number for the next packet to be sent
        self.serverSeqNum = 0  # sequence number of the next not ack packet
        self.userId = 0
        self.userName = ""
        self.hasPrivateChat = False
        self.movieRoomId = -1  # not in movie room

    def sendPacket(self, packet):
        buf = util.packMsg(packet)
        self.transport.write(buf)

    def sendLoginRequestOIE(self, userName):
        """
        :param string userName: The user name that the user has typed.

        The controller calls this function as soon as the user clicks on
        the login button.
        """
        moduleLogger.debug('loginRequest called with username=%s', userName)

        self.roomType = room_type["notApplicable"]
        self.seqNum = 0
        self.userId = 0
        self.userName = userName
        loginRequest = Packet(frg=0, ack=0, msgType=type_code["loginRequest"],
                    roomType=self.roomType, seqNum=self.seqNum,
                    userId=self.userId, destId=0, length= len(userName), data=userName)
        self.sendPacket(loginRequest)



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
        self.seqNum += 1
        if(self.seqNum==256):
            self.seqNum=0
            
        message = self.userName + ":" + message

     
        # Création du packet dans la main room
        if (roomType == room_type["mainRoom"]):
            chatMessage = Packet(frg=0, ack=0, msgType=type_code["message"], roomType=self.roomType,        
                                seqNum=self.seqNum, userId=self.userId, destId=0, length = len(message),      
                                data=message)

        # Création du packet dans une movie room
        if (roomType == room_type["movieRoom"]):
            chatMessage = Packet(frg=0, ack=0, msgType=type_code["message"], roomType=self.roomType,       
                                seqNum=self.seqNum, userId=self.userId,
                                destId=self.movieRoomId, length= len(message), data=message)

        # Création du packet dans une private room
        # TODO : destId ???
        #if (roomType == 2):
        #    chatMessage = Packet(frg=0, ack=0, msgType=1, roomType=self.roomType, 
    #                            seqNum=self.seqNum, userId=self.userId, destId=0, length = len(message), data=message)    
     
        #Envoi du message                  
        sendPacket(self, chatMessage)
 

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
        pass

    def sendLeaveSystemRequestOIE(self):
        """
        Called **by the controller**  when the user
        has clicked on the leave button in the main room.
        """
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
        
        #if the packet is an ack
        if pack.ack == 1:
            if msgType == type_code["errorMessage"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
            
            else:
                pass
                
        #if the packet is a request
        else:
            
            if msgType == type_code["movieList"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
                
            
            if msgType == type_code["userList"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
            
            if msgType == type_code["messageForward"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
            
            if msgType == type_code["privateChateRequest"]:
            #private chat request
            #respond with an ack if he's available
                pass  
            
            if msgType == type_code["leaveChatRoomRequestForward"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
                
            if msgType == type_code["AYT"]:
                pack.turnIntoAck()
                self.sendPacket(pack)
            
             
        
                

