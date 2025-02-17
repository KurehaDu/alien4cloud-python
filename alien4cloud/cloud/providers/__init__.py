from ..factory import CloudProviderFactory
from .mock.provider import MockCloudProvider
from .k8s.provider import K8sCloudProvider

# 注册提供者
CloudProviderFactory.register_provider("mock", MockCloudProvider)
CloudProviderFactory.register_provider("k8s", K8sCloudProvider)

__all__ = ["MockCloudProvider", "K8sCloudProvider"] 