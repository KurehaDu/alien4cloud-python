from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    name: str
    type: str
    target: Optional[str] = None
    operation: Optional[str] = None
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    on_success: List[str] = field(default_factory=list)
    on_failure: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "target": self.target,
            "operation": self.operation,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "on_success": self.on_success,
            "on_failure": self.on_failure
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowStep':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            target=data.get("target"),
            operation=data.get("operation"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            on_success=data.get("on_success", []),
            on_failure=data.get("on_failure", [])
        )

@dataclass
class WorkflowTemplate:
    """工作流模板"""
    id: str
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowTemplate':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", "1.0.0"),
            steps={k: WorkflowStep.from_dict(v) for k, v in data.get("steps", {}).items()},
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        )

@dataclass
class WorkflowInstance:
    """工作流实例"""
    id: str
    template_id: str
    name: str
    status: str = "PENDING"
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    steps: Dict[str, Dict] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "steps": self.steps,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowInstance':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            template_id=data["template_id"],
            name=data["name"],
            status=data.get("status", "PENDING"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            steps=data.get("steps", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message")
        ) 