

class HandleRequestError(Exception):
    """
    """
    def __init__(self, message, status, **kwargs):
        super().__init__(message)
        self.status_code = status
        self.data = {}
        self.data['error'] = {'message': message, **kwargs}


class HandleWebSocketError(HandleRequestError):
    pass


class DBError(Exception):
    pass


class ObjectDoesNotExist(Exception):
    pass


class PermissionDenied(Exception):
    """The user did not have permission to do that"""
    pass
