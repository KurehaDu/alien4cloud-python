from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

class WorkflowStatus(str, Enum):
    """工作流状态"""
    CREATED = "created"         # 已创建
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    PAUSED = "paused"          # 已暂停
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 执行失败
    CANCELLED = "cancelled"     # 已取消

class StepStatus(str, Enum):
    """步骤状态"""
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 执行失败
    SKIPPED = "skipped"        # 已跳过

@dataclass
class StepState:
    """步骤状态"""
    id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class WorkflowState:
    """工作流状态"""
    id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    steps: Dict[str, StepState] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowTemplate:
    """工作流模板"""
    id: str
    name: str
    description: Optional[str] = None
    yaml_content: str = ""  # 原始YAML内容
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class WorkflowInstance:
    """工作流实例"""
    id: str
    template_id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    nodes_status: Dict[str, Any] = field(default_factory=dict)
    cloud_provider: str = "mock"  # mock, k8s
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now) 