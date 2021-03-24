
class ParseError(Exception):

    def __init__(self, message, message_user=None):
        super().__init__(message)
        self.message_user = message_user


class ParserImportError(ParseError):
    pass
