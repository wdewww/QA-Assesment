class PageFetcherException(Exception):
    """Base Exception for all derivate excptions"""

class PageUnreachableException(PageFetcherException):
    pass

class PageTimeoutException(PageFetcherException):
    pass

class UnsupportedContentTypeException(PageFetcherException):
    pass

class EmptyResponseException(PageFetcherException):
    pass

class DOMParsingException(PageFetcherException):
    pass

class HTTPErrorException(PageFetcherException):
    def __init__(self, status_code: int):
        super().__init__(f"HTTP error: {status_code}")
        self.status_code = status_code
