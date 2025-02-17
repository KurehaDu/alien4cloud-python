from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from .base import BaseModel

class WorkflowStepType(Enum):
    """工作流步骤类型"""
    NODE_OPERATION = "node_operation"
    RELATIONSHIP_OPERATION = "relationship_operation"
    CALL_OPERATION = "call_operation"
    INLINE = "inline"

@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    type: WorkflowStepType
    target: str
    operation: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    on_success: List[str] = field(default_factory=list)
    on_failure: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'target': self.target,
            'operation': self.operation,
            'inputs': self.inputs,
            'on_success': self.on_success,
            'on_failure': self.on_failure
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        return cls(
            type=WorkflowStepType(data['type']),
            target=data['target'],
            operation=data.get('operation'),
            inputs=data.get('inputs', {}),
            on_success=data.get('on_success', []),
            on_failure=data.get('on_failure', [])
        )

@dataclass
class WorkflowDefinition(BaseModel):
    """工作流定义模型"""
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'steps': {k: v.to_dict() for k, v in self.steps.items()},
            'inputs': self.inputs,
            'preconditions': self.preconditions,
            'triggers': self.triggers
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDefinition':
        instance = super().from_dict(data)
        
        # 解析steps
        steps = {}
        for name, step_data in data.get('steps', {}).items():
            steps[name] = WorkflowStep.from_dict(step_data)
        instance.steps = steps

        instance.inputs = data.get('inputs', {})
        instance.preconditions = data.get('preconditions', [])
        instance.triggers = data.get('triggers', [])
        
        return instance

@dataclass
class WorkflowTemplate(BaseModel):
    """工作流模板模型"""
    workflow: WorkflowDefinition
    node_types: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'workflow': self.workflow.to_dict(),
            'node_types': self.node_types,
            'tags': self.tags
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowTemplate':
        instance = super().from_dict(data)
        
        instance.workflow = WorkflowDefinition.from_dict(data['workflow'])
        instance.node_types = data.get('node_types', [])
        instance.tags = data.get('tags', [])
        
        return instance 