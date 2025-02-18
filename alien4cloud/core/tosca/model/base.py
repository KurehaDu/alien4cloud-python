from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class BaseModel:
    """TOSCA基础模型类"""
    id: str
    name: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
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
            description=data.get('description'),
            metadata=data.get('metadata', {}),
            created_at=created_at,
            updated_at=updated_at
        )

@dataclass
class ToscaType(BaseModel):
    """TOSCA类型基础模型"""
    id: str
    name: str
    version: str
    derived_from: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        data.update({
            'version': self.version,
            'derived_from': self.derived_from,
            'properties': self.properties
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToscaType':
        """从字典创建实例"""
        base_data = {k: v for k, v in data.items() 
                    if k in ['id', 'name', 'description', 'metadata', 'created_at', 'updated_at']}
        instance = super().from_dict(base_data)
        
        instance.version = data['version']
        instance.derived_from = data.get('derived_from')
        instance.properties = data.get('properties', {})
        return instance 