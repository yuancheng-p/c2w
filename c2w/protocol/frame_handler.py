from packet import Packet
import util

class FrameHandler:

    def __init__(self):
        self.headFound = False
        self.currentHead = ""  # current header in binary mode
        self.currentSize = 0
        self.buf = ""
        self.header = Packet(0, 0, 0, 3, 0, 0, 0, 0, None)

    def extractPackets(self, data):
        """
        return: a list of packet objects
        """
        packList = []
        while data != "":
            # header detected
            if not self.headFound:
                print "PACKET HEADER DETECTED"
                remainHeadLength = 6 - len(self.currentHead)
                if len(data) >= remainHeadLength:
                    if self.currentHead != "":
                        self.currentHead += data[0:remainHeadLength]
                        data = data[remainHeadLength:]
                    else:
                        self.currentHead = data[0:6]
                        data = data[6:]
                    self.header = util.unpackHeader(self.currentHead)
                    self.buf += self.currentHead
                    self.currentHead = ""
                    self.headFound = True
                else:
                    self.currentHead += data

            # remain msg in the packet
            else:
                # The packet is separated into many TCP packets
                if len(data) <= (self.header.length - self.currentSize):
                    self.buf += data
                    self.currentSize += len(data)
                    data = ""
                # Multiple packets are packed into one TCP packet, always happen
                else:  # cut the data
                    t_data = data[0:self.header.length - self.currentSize]
                    self.buf += t_data
                    self.currentSize += len(t_data)
                    data = data[self.header.length - self.currentSize:]

            if self.currentSize >= self.header.length and self.headFound:
                packList.append(util.unpackMsg(self.buf))
                self.header = Packet(0, 0, 0, 3, 0, 0, 0, 0, None)
                self.headFound = False
                self.currentSize = 0
                self.buf = ""
        return packList
