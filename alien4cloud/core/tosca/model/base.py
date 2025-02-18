from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class BaseModel:
    """TOSCA基础模型类
    
    基础属性：
    - id: 唯一标识符
    - name: 名称
    - version: 版本号
    - description: 描述信息（可选）
    - metadata: 元数据（可选）
    """
    id: str
    name: str
    version: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """从字典创建实例"""
        created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        
        return cls(
            id=data['id'],
            name=data['name'],
            version=data['version'],
            description=data.get('description'),
            metadata=data.get('metadata', {}),
            created_at=created_at,
            updated_at=updated_at
        )

@dataclass
class ToscaType(BaseModel):
    """TOSCA类型基础模型
    
    继承BaseModel的基础属性，并添加：
    - derived_from: 继承自哪个类型（可选）
    - properties: 属性定义（可选）
    """
    derived_from: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        data.update({
            'derived_from': self.derived_from,
            'properties': self.properties
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToscaType':
        """从字典创建实例"""
        instance = super().from_dict(data)
        instance.derived_from = data.get('derived_from')
        instance.properties = data.get('properties', {})
        return instance 