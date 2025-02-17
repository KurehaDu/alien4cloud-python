# alien4cloud/cloud/errors.py

class CloudError(Exception):
    """云平台基础错误"""
    pass

class ConfigError(CloudError):
    """配置错误"""
    pass

class ConnectionError(CloudError):
    """连接错误"""
    pass

class AuthenticationError(CloudError):
    """认证错误"""
    pass

class ResourceError(CloudError):
    """资源错误"""
    pass

class DeploymentError(CloudError):
    """部署错误"""
    pass

class OperationError(CloudError):
    """操作错误"""
    pass

class NotFoundError(CloudError):
    """资源不存在错误"""
    pass

class ValidationError(CloudError):
    """验证错误"""
    pass 