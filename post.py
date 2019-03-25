import arrow

class Post():
    # __tablename__ = 'appointments'

    id = ''
    name = ''
    time = ''
    timezone = ''

    def __init__(self, name, time, timezone):
        self.name = name
        self.time = time
        self.timezone = timezone
