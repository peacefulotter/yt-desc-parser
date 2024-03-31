class Record:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return f"Config({str(self.__dict__)[1:-1]})"

    def __repr__(self):
        return self.__str__()
