from tables import type_decode, room_type_decode, type_code, error_code
from tables import room_type
import copy



class Packet():

    def __init__(self, frg, ack, msgType, roomType, seqNum, userId, destId, length, data):
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

    def turnIntoAck(self, data=""):
        # FIXME potential problems
        self.ack = 1
        self.data = data
        if (self.msgType == type_code["roomRequest"] and
                    self.roomType == room_type["movieRoom"]):
            # data filed: dict {"ip": ip, "port": port}
            self.length = 6
        else:
            self.length = 0
        return

    def turnIntoErrorPack(self, error_type):
        """ error message is a special type of ACK packet
        """
        self.ack = 1
        self.msgType = type_code["errorMessage"]
        self.length = 1
        self.data = error_type
        return

    def copy(self):
        return copy.deepcopy(self)
