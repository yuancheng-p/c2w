import ctypes
import struct
from packet import Packet
from tables import type_code
from data_strucs import Movie, User

def packMsg(pack):
    """
    """
    byte_1 = pack.frg | (pack.ack << 1) | (pack.msgType << 2) | (pack.roomType << 6)

    buf_len = 6 + pack.length
    buf = ctypes.create_string_buffer(buf_len)

    header = ">BBBBH"
    offset = 0
    struct.pack_into(header, buf, offset,
                    byte_1,
                    pack.seqNum,
                    pack.userId,
                    pack.destId,
                    pack.length)
    offset += 6

    if pack.ack == 1:
        if pack.msgType == type_code["errorMessage"]:
            struct.pack_into("B", buf, offset, pack.data)
        return buf

    if pack.msgType == type_code["movieList"]:
        for movie in pack.data:  # data is a movie list
            movie_list_format = "BB" + repr(movie.length) + "s"
            struct.pack_into(movie_list_format, buf, offset,
                            movie.length, movie.roomId, movie.movieName)
            offset = offset + 2 + movie.length
    elif pack.msgType == type_code["userList"]:
        for user in pack.data.values():  # data is a user dict
            user_header_format = "BBB" + repr(user.length) + "s"
            struct.pack_into(user_header_format, buf, offset,
                            user.length, user.userId, user.status, user.name)
            offset = offset + 3 + user.length
    elif pack.msgType == type_code["roomRequest"] and pack.ack == 1:
        """2 bytes for portNum, 4 byte for ip addr"""
        addr_format = "HBBBB"

        ip = pack.data["ip"].split(".")
        struct.pack_into(addr_format, buf, offset,
                pack.data["port"], ip[0], ip[1], ip[2], ip[3])

        struct.pack_into("B", buf, offset, pack.data)
    else:  # str: loginRequest, message, messageForward,
        buf_format = repr(pack.length) + "s"
        struct.pack_into(buf_format, buf, offset, # offset 0
                        pack.data)
    return buf

# unpack for UDP
def unpackMsg(datagram):
    """
    For the roomRequest, the type of data field is a dict with key "port" and
    key "ip"
    """


    header_format = ">BBBBH"
    offset = 0
    header = struct.unpack_from(header_format, datagram, offset)
    offset += 6
    frg = header[0] & 1
    ack = header[0]>>1 & 1
    msgType = header[0]>>2 & 15
    roomType = header[0]>>6 & 3

    data = None
    if ack == 1 and msgType == type_code["errorMessage"]:
        data = struct.unpack_from("B", datagram, offset)

    if msgType == type_code["movieList"]:
        movieList = []
        while offset <= header[4]:
            movie_header_format = "BB"
            movie_header = struct.unpack_from(movie_header_format, datagram, offset)
            offset += 2

            movieName_format = repr(movie_header[0]) + "s"
            movieName = struct.unpack_from(movieName_format, datagram, offset)[0]
            offset += movie_header[0]

            movie = Movie(movieName, movie_header[1])
            movieList.append(movie)
        data = movieList
        pass
    elif msgType == type_code["userList"]:
        userList = []
        while offset <= header[4]:
            user_header_format = "BBB"
            user_header = struct.unpack_from(user_header_format, datagram, offset)
            offset += 3

            userName_format = repr(user_header[0]) + "s"
            userName  = struct.unpack_from(userName_format, datagram, offset)[0]
            offset += user_header[0]

            user = User(userName, user_header[1], user_header[2]>>7)
            userList.append(user)
        data = userList
        pass
    elif msgType == type_code["roomRequest"]:  # and pack.ack == 1:
        """2 bytes for portNum, 4 byte for ip addr"""
        addr_format = "HBBBB"
        msg = struct.unpack_from(addr_format, datagram, offset)
        data = {"port": msg[0], "ip": ".".join(map(str, msg[1:]))}
        pass
    else:  # str: loginRequest, message, messageForward,
        buf_format = repr(len(datagram) - 6) + "s"
        msg = struct.unpack_from(buf_format, datagram, offset)
        data = msg[0]

    pack = Packet(frg, ack, msgType, roomType, seqNum=header[1],
            userId=header[2], destId=header[3], length=header[4], data=data)
    return pack


def adaptMovieList(movieList):
    """change movieList into GUI adapted format"""
    #TODO
    return []

def adaptUserList(users):
    """change users into GUI adapted format"""
    #TODO
    return []
