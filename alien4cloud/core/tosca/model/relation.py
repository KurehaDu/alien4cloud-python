from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from .base import ToscaType

@dataclass
class RelationshipValidSource:
    """关系有效源定义"""
    node_type: str
    capability_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_type': self.node_type,
            'capability_type': self.capability_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipValidSource':
        return cls(
            node_type=data['node_type'],
            capability_type=data.get('capability_type')
        )

@dataclass
class RelationshipValidTarget:
    """关系有效目标定义"""
    node_type: str
    capability_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_type': self.node_type,
            'capability_type': self.capability_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipValidTarget':
        return cls(
            node_type=data['node_type'],
            capability_type=data.get('capability_type')
        )

@dataclass
class RelationshipType(ToscaType):
    """关系类型模型"""
    valid_sources: List[RelationshipValidSource] = field(default_factory=list)
    valid_targets: List[RelationshipValidTarget] = field(default_factory=list)
    interfaces: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'valid_sources': [s.to_dict() for s in self.valid_sources],
            'valid_targets': [t.to_dict() for t in self.valid_targets],
            'interfaces': self.interfaces,
            'attributes': self.attributes
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipType':
        instance = super().from_dict(data)
        
        # 解析valid_sources
        valid_sources = []
        for source_data in data.get('valid_sources', []):
            valid_sources.append(RelationshipValidSource.from_dict(source_data))
        instance.valid_sources = valid_sources

        # 解析valid_targets
        valid_targets = []
        for target_data in data.get('valid_targets', []):
            valid_targets.append(RelationshipValidTarget.from_dict(target_data))
        instance.valid_targets = valid_targets

        instance.interfaces = data.get('interfaces', {})
        instance.attributes = data.get('attributes', {})
        
        return instance 