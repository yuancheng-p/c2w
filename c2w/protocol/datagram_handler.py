import util
class DatagramHandler():
    """
    A class designed for client to handle fragmentation.
    """

    def __init__(self, c2wUdpChatClient):
        """
        .. attribute:: serverSeqNum
        The next expected packet from server

        .. attribute:: dataBuf
        Binary data, to be completed by following packets

        .. attribute:: c2wUdpChatClient
        An object of the class c2wUdpChatClientProtocol

        .. attribute:: header
        Header of a fragmentation packet
        """
        self.serverSeqNum = 0  # sequence number of the next not ack packet
        self.client = c2wUdpChatClient
        self.dataBuf = ""
        self.header = None

    def sendAck(self, pack):
        ackPack = pack.copy()
        ackPack.turnIntoAck()
        self.client.sendPacket(ackPack)
        return

    def unpackMsg(self, datagram):
        packHeader = util.unpackHeader(datagram)
        if packHeader.ack == 1:
            return util.unpackMsg(datagram)
        else:
            if packHeader.seqNum == self.serverSeqNum:
                self.serverSeqNum += 1
                self.sendAck(packHeader)
            else:
                print "Unexpected seqNum packet received, aborted"
                self.sendAck(packHeader)
                return

            if packHeader.frg == 1:
                if self.header == None:  # first frg packet
                    self.header = util.unpackHeader(datagram)
                else:
                    self.header.length += packHeader.length
                # save current buf
                self.dataBuf += datagram[6:]
            elif packHeader.frg == 0 and self.header != None:  # last frgment packet
                self.header.length += packHeader.length
                self.header.seqNum = packHeader.seqNum
                self.header.frg = 0
                self.dataBuf += datagram[6:]
                headerBuf = util.packHeader(self.header).raw
                finalPackBuf = headerBuf + self.dataBuf
                # reset attributes before return packet
                self.dataBuf = ""
                self.header = None
                return util.unpackMsg(finalPackBuf)
            elif packHeader.frg == 0 and self.header == None:  # not a frgment packet
                return util.unpackMsg(datagram)
            else:
                print "Unexpected error when unpacking datagram"

class ClientDatagramHandler():
    """
    A class designed for  handling client's fragmentation.
    This class should be used for server.
    """

    def __init__(self, c2wUdpChatServer, (host, port)):
        """
        .. attribute:: clientSeqNum
        The next expected packet from server

        .. attribute:: dataBuf
        Binary data, to be completed by following packets

        .. attribute:: c2wUdpChatClient
        An object of the class c2wUdpChatClientProtocol

        .. attribute:: header
        Header of a fragmentation packet
        """
        self.clientSeqNum = 1  # sequence number of the next not ack packet
        self.server = c2wUdpChatServer
        self.dataBuf = ""
        self.header = None
        self.host = host
        self.port = port

    def sendAck(self, pack):
        ackPack = pack.copy()
        ackPack.turnIntoAck()
        self.server.sendPacket(ackPack, (self.host, self.port))
        return

    def unpackMsg(self, datagram):
        packHeader = util.unpackHeader(datagram)
        if packHeader.ack == 1:
            return util.unpackMsg(datagram)
        else:
            # send ack for fragments
            if packHeader.seqNum == self.clientSeqNum:
                if packHeader.frg == 1:
                    self.sendAck(packHeader)  # intermediate packets
                self.clientSeqNum += 1
            else:
                # TODO this is maybe an ack lost request, or a part of it
                self.sendAck(packHeader)  # intermediate packets
                print "Unexpected packet received, ack sent"
                return None

            if packHeader.frg == 1:
                if self.header == None:  # first frg packet
                    self.header = util.unpackHeader(datagram)
                else:
                    self.header.length += packHeader.length
                # save current buf
                self.dataBuf += datagram[6:]
                return None
            elif packHeader.frg == 0 and self.header != None:  # last frgment packet
                self.header.length += packHeader.length
                self.header.seqNum = packHeader.seqNum
                self.header.frg = 0
                self.dataBuf += datagram[6:]
                headerBuf = util.packHeader(self.header).raw
                finalPackBuf = headerBuf + self.dataBuf
                # reset attributes before return packet
                self.dataBuf = ""
                self.header = None
                return util.unpackMsg(finalPackBuf)
            elif packHeader.frg == 0 and self.header == None:  # not a frgment packet
                return util.unpackMsg(datagram)
            else:
                print "Unexpected error when unpacking datagram"
                return None
