from tables import type_decode, room_type_decode, type_code, error_code
import copy



class Packet():

    """Docstring for Packet. """

    def __init__(self, frg, ack, msgType, roomType, seqNum, userId, destId, length, data):
        """@todo: to be defined1. """
        self.frg = frg
        self.ack = ack
        self.msgType = msgType
        self.roomType = roomType
        self.seqNum = seqNum
        self.userId = userId
        self.destId = destId
        self.data = data
        self.length = length
        pass

    def __repr__(self):
        return "[frg:%d; ack:%d; msgType:%s(%d); roomType:%s(%d); seqNum:%d; \
userId:%d; destId:%d; length:%d; data(%s):%s]" % (
                    self.frg, self.ack, type_decode[self.msgType], self.msgType,
                    room_type_decode[self.roomType], self.roomType,
                    self.seqNum, self.userId, self.destId,
                    self.length, type(self.data), repr(self.data))

    def turnIntoAck(self):
        self.ack = 1
        self.data = ""
        self.length = 0
        return

    def turnIntoErrorPack(self, error_type):
        """ errer message is a special type of ack packet
        """
        self.ack = 1
        self.msgType = type_code["errorMessage"]
        self.length = 1
        self.data = error_type
        return

    def copy(self):
        return copy.deepcopy(self)
