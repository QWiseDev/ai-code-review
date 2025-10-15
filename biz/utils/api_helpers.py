"""
API辅助工具模块
提供统一的错误处理、验证和响应格式化功能
"""
from functools import wraps
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
from flask import jsonify
from biz.utils.log import logger


class ApiResponse:
    """统一的API响应格式"""

    @staticmethod
    def success(data: Any = None, message: str = 'Success', code: int = 200) -> Tuple[Any, int]:
        """
        成功响应

        Args:
            data: 返回的数据
            message: 成功消息
            code: HTTP状态码

        Returns:
            Tuple[Response, int]: Flask响应对象和状态码
        """
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message != 'Success':
            response['message'] = message
        return jsonify(response), code

    @staticmethod
    def error(message: str = 'Error', code: int = 500, details: Optional[Dict] = None) -> Tuple[Any, int]:
        """
        错误响应

        Args:
            message: 错误消息
            code: HTTP状态码
            details: 额外的错误详情

        Returns:
            Tuple[Response, int]: Flask响应对象和状态码
        """
        response = {
            'success': False,
            'message': message
        }
        if details:
            response['details'] = details
        return jsonify(response), code


class ValidationError(ValueError):
    """验证错误异常"""
    pass


class Validator:
    """输入验证工具类"""

    @staticmethod
    def validate_webhook_url(url: Optional[str]) -> bool:
        """
        验证Webhook URL的格式

        Args:
            url: 待验证的URL

        Returns:
            bool: URL是否有效
        """
        if not url:
            return True  # 允许为空

        url = url.strip()
        if not url:
            return True

        try:
            parsed = urlparse(url)
            # 必须有协议和域名，且协议为http或https
            return (
                parsed.scheme in ('http', 'https')
                and bool(parsed.netloc)
                and len(url) <= 2048  # URL长度限制
            )
        except Exception:
            return False

    @staticmethod
    def validate_team_name(name: Optional[str]) -> Tuple[bool, str]:
        """
        验证团队名称

        Args:
            name: 团队名称

        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        if not name:
            return False, "团队名称不能为空"

        name = name.strip()
        if not name:
            return False, "团队名称不能为空"

        if len(name) > 50:
            return False, "团队名称不能超过50个字符"

        # 可以添加更多验证规则，如禁止特殊字符等
        forbidden_chars = ['<', '>', '"', "'", ';', '\\']
        for char in forbidden_chars:
            if char in name:
                return False, f"团队名称不能包含特殊字符: {char}"

        return True, ""

    @staticmethod
    def validate_authors(authors: Any) -> Tuple[bool, str]:
        """
        验证作者列表

        Args:
            authors: 作者列表

        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        if not isinstance(authors, list):
            return False, "authors字段必须为数组"

        if not authors:
            return False, "authors数组不能为空"

        if len(authors) > 100:
            return False, "单次最多添加100个成员"

        for author in authors:
            if not isinstance(author, str):
                return False, "author必须为字符串"
            if not author.strip():
                return False, "author不能为空字符串"
            if len(author) > 100:
                return False, "author长度不能超过100个字符"

        return True, ""


def handle_api_errors(operation_name: str = None):
    """
    统一的API错误处理装饰器

    Args:
        operation_name: 操作名称，用于日志记录
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                # 验证错误 - 400
                logger.warning(f"Validation error in {op_name}: {e}")
                return ApiResponse.error(message=str(e), code=400)
            except ValueError as e:
                # 业务逻辑错误 - 400
                logger.warning(f"Business logic error in {op_name}: {e}")
                return ApiResponse.error(message=str(e), code=400)
            except PermissionError as e:
                # 权限错误 - 403
                logger.warning(f"Permission denied in {op_name}: {e}")
                return ApiResponse.error(message=str(e), code=403)
            except FileNotFoundError as e:
                # 资源不存在 - 404
                logger.info(f"Resource not found in {op_name}: {e}")
                return ApiResponse.error(message=str(e), code=404)
            except Exception as e:
                # 未预期的错误 - 500
                logger.error(f"Unexpected error in {op_name}: {e}", exc_info=True)
                return ApiResponse.error(
                    message=f'操作失败: {op_name}',
                    code=500
                )
        return wrapper
    return decorator


def log_api_call(func):
    """
    API调用日志装饰器，记录请求和响应信息
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        from flask import request

        start_time = time.time()
        endpoint = f"{request.method} {request.path}"

        # 记录请求开始
        logger.info(f"API call started: {endpoint}")

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            # 记录成功的请求
            logger.info(
                f"API call completed: {endpoint} | "
                f"Duration: {elapsed:.3f}s | "
                f"Status: success"
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            # 记录失败的请求
            logger.error(
                f"API call failed: {endpoint} | "
                f"Duration: {elapsed:.3f}s | "
                f"Error: {str(e)}"
            )
            raise

    return wrapper
