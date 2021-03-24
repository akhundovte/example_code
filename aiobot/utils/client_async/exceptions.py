

class ConsumerError(Exception):
    """
    """


class HttpError(Exception):
    """
    Общая ошибка для всех исключений, которые возникают в результате запроса
    """
    def __init__(self, message, error=None):
        super().__init__(message)
        self.message = message
        self.error = error


class RequestError(HttpError):
    """
    """


class ConnectionRequestError(RequestError):
    """
    """


class ConnectionRetryError(ConnectionRequestError):
    """
    Обертка для исключений после которых будет делать повторные запросы
    """


class ConnectionTimeout(ConnectionRequestError):
    """
    """


class HTTPResponseError(HttpError):
    """
    """
    def __init__(self, message, error=None, status_code=None):
        self.status_code = status_code
        super().__init__(message, error)


class HTTPResponseEntityTooLarge(HttpError):
    """
    """




def raise_from_response(error, params=None, key_descr=None):
    """
    Поднятие ошибки при из полученных данных на запрос, когда в в теле есть описание ошибки
    при кодах 400 <= response.status_code < 500
    raise_from_response(response_data.get('error'), response_data)

    В данном случае error это строка, приходит в ответе с сервера
    Например,
    {
    'error_description': 'The specified code is not valid',
    'error': 'invalid_grant'
    }
    """
    kwargs = {}
    if params:
        kwargs['description'] = params.get('error_description')
    raise ErrorInResponse(error=error, **kwargs)


class ErrorInResponse(Exception):
    """
    В ответе от сервера приходят error и error_description
    аналог oauthlib.oauth2.rfc6749.errors.py
    """
    description = ''

    def __init__(self, error, description=None):
        if description is not None:
            self.description = description

        if error:
            message = '(%s) %s' % (error, self.description)
        else:
            message = '%s' % (self.description)
        super().__init__(message)
        self.message = message
