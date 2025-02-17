# alien4cloud/cloud/config.py

from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class CloudConfig:
    """云平台配置"""
    type: str  # 云平台类型: mock, k8s 等
    name: str  # 云平台名称
    description: Optional[str] = None  # 描述
    enabled: bool = True  # 是否启用
    default: bool = False  # 是否为默认云平台
    timeout: int = 300  # 操作超时时间(秒)
    retry_count: int = 3  # 重试次数
    retry_interval: int = 5  # 重试间隔(秒)
    properties: Dict[str, Any] = None  # 特定云平台的配置属性

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}

    def validate(self) -> None:
        """验证配置"""
        if not self.type:
            raise ValueError("云平台类型不能为空")
        if not self.name:
            raise ValueError("云平台名称不能为空")
        if self.timeout <= 0:
            raise ValueError("超时时间必须大于0")
        if self.retry_count < 0:
            raise ValueError("重试次数不能小于0")
        if self.retry_interval <= 0:
            raise ValueError("重试间隔必须大于0")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "default": self.default,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_interval": self.retry_interval,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CloudConfig':
        """从字典创建配置"""
        return cls(
            type=data["type"],
            name=data["name"],
            description=data.get("description"),
            enabled=data.get("enabled", True),
            default=data.get("default", False),
            timeout=data.get("timeout", 300),
            retry_count=data.get("retry_count", 3),
            retry_interval=data.get("retry_interval", 5),
            properties=data.get("properties", {})
        )