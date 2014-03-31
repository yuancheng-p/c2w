class Movie():

    def __init__(self, movieName, roomId):
        self.movieName = movieName
        self.roomId = roomId
        self.length = len(movieName)
        pass

    def __repr__(self):
        return  "MovieObject(length:%d; roomId:%d; movieName:%s)" % (self.length,
                self.roomId, self.movieName)


class User():

    def __init__(self, name, userId, roomId=3, status=1):
        self.name = name
        self.length = len(name)
        self.userId = userId
        self.status = status
        pass

    def __repr__(self):
        return "UserObject(length:%d; userId:%d; status:%d; name:%s)" % (self.length,
                self.userId, self.status, self.name)
