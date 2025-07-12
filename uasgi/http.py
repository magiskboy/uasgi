from typing import List, Tuple


def build_http_response_header(status: int, http_version: str, headers: List[Tuple[bytes, bytes]]):
    phrase = STATUS_PHRASES.get(status, b"Unknown")
    buffer = bytearray()
    buffer.extend(f"HTTP/{http_version} {status} {phrase}\r\n".encode("ascii"))

    for k, v in headers:
        buffer.extend(k)
        buffer.extend(b":")
        buffer.extend(v)
        buffer.extend(b"\r\n")
    buffer.extend(b"\r\n")

    return bytes(buffer)



STATUS_PHRASES = {
    # 1xx: Informational
    100: b"Continue",
    101: b"Switching Protocols",
    102: b"Processing",
    103: b"Early Hints",

    # 2xx: Success
    200: b"OK",
    201: b"Created",
    202: b"Accepted",
    203: b"Non-Authoritative Information",
    204: b"No Content",
    205: b"Reset Content",
    206: b"Partial Content",
    207: b"Multi-Status",
    208: b"Already Reported",
    226: b"IM Used",

    # 3xx: Redirection
    300: b"Multiple Choices",
    301: b"Moved Permanently",
    302: b"Found",
    303: b"See Other",
    304: b"Not Modified",
    305: b"Use Proxy",
    307: b"Temporary Redirect",
    308: b"Permanent Redirect",

    # 4xx: Client Error
    400: b"Bad Request",
    401: b"Unauthorized",
    402: b"Payment Required",
    403: b"Forbidden",
    404: b"Not Found",
    405: b"Method Not Allowed",
    406: b"Not Acceptable",
    407: b"Proxy Authentication Required",
    408: b"Request Timeout",
    409: b"Conflict",
    410: b"Gone",
    411: b"Length Required",
    412: b"Precondition Failed",
    413: b"Payload Too Large",
    414: b"URI Too Long",
    415: b"Unsupported Media Type",
    416: b"Range Not Satisfiable",
    417: b"Expectation Failed",
    418: b"I'm a teapot",
    421: b"Misdirected Request",
    422: b"Unprocessable Entity",
    423: b"Locked",
    424: b"Failed Dependency",
    425: b"Too Early",
    426: b"Upgrade Required",
    428: b"Precondition Required",
    429: b"Too Many Requests",
    431: b"Request Header Fields Too Large",
    451: b"Unavailable For Legal Reasons",

    # 5xx: Server Error
    500: b"Internal Server Error",
    501: b"Not Implemented",
    502: b"Bad Gateway",
    503: b"Service Unavailable",
    504: b"Gateway Timeout",
    505: b"HTTP Version Not Supported",
    506: b"Variant Also Negotiates",
    507: b"Insufficient Storage",
    508: b"Loop Detected",
    510: b"Not Extended",
    511: b"Network Authentication Required"
}

