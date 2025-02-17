from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from .base import ToscaType

@dataclass
class NodeRequirement:
    """节点需求定义"""
    type: str
    relationship: str
    capability: Optional[str] = None
    node: Optional[str] = None
    occurrences: Optional[List[int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'relationship': self.relationship,
            'capability': self.capability,
            'node': self.node,
            'occurrences': self.occurrences
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeRequirement':
        return cls(
            type=data['type'],
            relationship=data['relationship'],
            capability=data.get('capability'),
            node=data.get('node'),
            occurrences=data.get('occurrences')
        )

@dataclass
class NodeCapability:
    """节点能力定义"""
    type: str
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'description': self.description,
            'properties': self.properties,
            'attributes': self.attributes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeCapability':
        return cls(
            type=data['type'],
            description=data.get('description'),
            properties=data.get('properties', {}),
            attributes=data.get('attributes', {})
        )

@dataclass
class NodeType(ToscaType):
    """节点类型模型"""
    requirements: Dict[str, NodeRequirement] = field(default_factory=dict)
    capabilities: Dict[str, NodeCapability] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    interfaces: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'requirements': {k: v.to_dict() for k, v in self.requirements.items()},
            'capabilities': {k: v.to_dict() for k, v in self.capabilities.items()},
            'attributes': self.attributes,
            'artifacts': self.artifacts,
            'interfaces': self.interfaces
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeType':
        instance = super().from_dict(data)
        
        # 解析requirements
        requirements = {}
        for name, req_data in data.get('requirements', {}).items():
            requirements[name] = NodeRequirement.from_dict(req_data)
        instance.requirements = requirements

        # 解析capabilities
        capabilities = {}
        for name, cap_data in data.get('capabilities', {}).items():
            capabilities[name] = NodeCapability.from_dict(cap_data)
        instance.capabilities = capabilities

        instance.attributes = data.get('attributes', {})
        instance.artifacts = data.get('artifacts', {})
        instance.interfaces = data.get('interfaces', {})
        
        return instance 