
class HandleMessageError(Exception):
    def __init__(self, message, message_user=None):
        super().__init__(message)
        self.message_user = message_user


class HandleProductError(Exception):
    """ """


class DeserializeProductError(Exception):
    """ """
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors
