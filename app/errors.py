from fastapi import HTTPException, status


def unauthorized(msg: str = "未登录或令牌无效"):
    return HTTPException(status.HTTP_401_UNAUTHORIZED, msg)


def forbidden(msg: str = "无权限"):
    return HTTPException(status.HTTP_403_FORBIDDEN, msg)


def not_found(msg: str = "资源不存在"):
    return HTTPException(status.HTTP_404_NOT_FOUND, msg)


def conflict(msg: str):
    return HTTPException(status.HTTP_409_CONFLICT, msg)


def bad_request(msg: str):
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def too_many(msg: str = "发送过于频繁"):
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, msg)
