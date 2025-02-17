from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ResourceStatus:
    """资源状态"""
    id: str
    name: str
    type: str
    state: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

@dataclass
class DeploymentStatus:
    """部署状态"""
    id: str
    name: str
    state: str
    resources: List[ResourceStatus]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    metadata: Dict[str, Any]

class CloudProvider(ABC):
    """云平台提供者基类"""

    @abstractmethod
    async def connect(self) -> None:
        """连接到云平台"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开与云平台的连接"""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """验证连接是否有效"""
        pass

    @abstractmethod
    async def create_deployment(self, name: str, template: Dict[str, Any], 
                              inputs: Dict[str, Any] = None) -> str:
        """创建部署"""
        pass

    @abstractmethod
    async def delete_deployment(self, deployment_id: str) -> None:
        """删除部署"""
        pass

    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        """获取部署状态"""
        pass

    @abstractmethod
    async def list_deployments(self, filters: Dict[str, Any] = None) -> List[DeploymentStatus]:
        """列出部署"""
        pass

    @abstractmethod
    async def update_deployment(self, deployment_id: str, 
                              template: Dict[str, Any], 
                              inputs: Dict[str, Any] = None) -> None:
        """更新部署"""
        pass

    @abstractmethod
    async def execute_operation(self, deployment_id: str, operation: str,
                              inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行操作"""
        pass

    @abstractmethod
    async def get_logs(self, deployment_id: str, resource_id: Optional[str] = None,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> List[str]:
        """获取日志"""
        pass

    @abstractmethod
    async def get_metrics(self, deployment_id: str, resource_id: Optional[str] = None,
                         metric_names: List[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> Dict[str, List[Any]]:
        """获取指标"""
        pass

    @abstractmethod
    async def validate_template(self, template: Dict[str, Any]) -> List[str]:
        """验证模板"""
        pass

    @abstractmethod
    async def get_resource_types(self) -> List[str]:
        """获取支持的资源类型"""
        pass

    @abstractmethod
    async def get_operation_types(self) -> List[str]:
        """获取支持的操作类型"""
        pass

    @abstractmethod
    async def get_provider_info(self) -> Dict[str, Any]:
        """获取提供者信息"""
        pass 