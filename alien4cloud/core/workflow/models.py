from datetime import datetime
import json
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .base import Base, WorkflowStatus, StepStatus

class WorkflowModel(Base):
    """工作流数据库模型"""
    __tablename__ = 'workflows'

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    _inputs = Column('inputs', Text)
    _outputs = Column('outputs', Text)
    _metadata = Column('metadata', Text)

    steps = relationship("StepModel", back_populates="workflow", cascade="all, delete-orphan")

    @hybrid_property
    def inputs(self) -> Dict[str, Any]:
        return json.loads(self._inputs) if self._inputs is not None else {}

    @inputs.setter
    def inputs(self, value: Dict[str, Any]):
        self._inputs = json.dumps(value) if value is not None else None

    @hybrid_property
    def outputs(self) -> Dict[str, Any]:
        return json.loads(self._outputs) if self._outputs is not None else {}

    @outputs.setter
    def outputs(self, value: Dict[str, Any]):
        self._outputs = json.dumps(value) if value is not None else None

    @hybrid_property
    def metadata(self) -> Dict[str, Any]:
        return json.loads(self._metadata) if self._metadata is not None else {}

    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        self._metadata = json.dumps(value) if value is not None else None

class StepModel(Base):
    """步骤数据库模型"""
    __tablename__ = 'steps'

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    _outputs = Column('outputs', Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    workflow = relationship("WorkflowModel", back_populates="steps")

    @hybrid_property
    def outputs(self) -> Dict[str, Any]:
        return json.loads(self._outputs) if self._outputs is not None else {}

    @outputs.setter
    def outputs(self, value: Dict[str, Any]):
        self._outputs = json.dumps(value) if value is not None else None

class WorkflowTemplate(Base):
    """工作流模板模型"""
    __tablename__ = 'workflow_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    yaml_content = Column(String, nullable=False)  # 原始YAML内容
    parsed_data = Column(JSON)  # 解析后的数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkflowInstance(Base):
    """工作流实例模型"""
    __tablename__ = 'workflow_instances'
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('workflow_templates.id'), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String, default=WorkflowStatus.CREATED.value)
    nodes_status = Column(JSON)  # 节点状态
    cloud_provider = Column(String(50))  # mock, k8s
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 