from typing import Dict, Any, Optional
from datetime import datetime

from ..tosca.model.workflow import WorkflowDefinition, WorkflowStep, WorkflowStepType

class WorkflowConverter:
    """工作流转换器，将TOSCA工作流定义转换为可执行的工作流"""
    
    @classmethod
    def from_definition(cls, definition: WorkflowDefinition) -> Dict[str, Any]:
        """从工作流定义创建工作流状态"""
        # 创建工作流状态
        workflow = {
            "id": definition.id or str(int(datetime.now().timestamp())),
            "name": definition.name,
            "state": "CREATED",
            "created_at": datetime.now().isoformat(),
            "inputs": definition.inputs or {},
            "metadata": {
                "preconditions": definition.preconditions,
                "triggers": definition.triggers
            },
            "steps": {}
        }
        
        # 转换步骤
        for step_id, step_def in definition.steps.items():
            step = cls._convert_step(step_id, step_def)
            workflow["steps"][step_id] = step
            
        return workflow
    
    @classmethod
    def _convert_step(cls, step_id: str, step_def: WorkflowStep) -> Dict[str, Any]:
        """转换工作流步骤"""
        return {
            "id": step_id,
            "name": step_def.target,
            "state": "PENDING",
            "outputs": {
                "type": step_def.type.value,
                "operation": step_def.operation,
                "inputs": step_def.inputs,
                "on_success": step_def.on_success,
                "on_failure": step_def.on_failure
            }
        }
    
    @classmethod
    def to_definition(cls, workflow: Dict[str, Any]) -> WorkflowDefinition:
        """将工作流状态转换回工作流定义"""
        # 创建工作流定义
        definition = WorkflowDefinition(
            id=workflow["id"],
            name=workflow["name"],
            inputs=workflow.get("inputs", {}),
            preconditions=workflow.get("metadata", {}).get("preconditions", []),
            triggers=workflow.get("metadata", {}).get("triggers", [])
        )
        
        # 转换步骤
        for step_id, step in workflow.get("steps", {}).items():
            step_def = cls._convert_step_back(step)
            definition.steps[step_id] = step_def
            
        return definition
    
    @classmethod
    def _convert_step_back(cls, step: Dict[str, Any]) -> WorkflowStep:
        """将步骤状态转换回步骤定义"""
        outputs = step.get("outputs", {})
        return WorkflowStep(
            type=WorkflowStepType(outputs.get("type")),
            target=step["name"],
            operation=outputs.get("operation"),
            inputs=outputs.get("inputs", {}),
            on_success=outputs.get("on_success", []),
            on_failure=outputs.get("on_failure", [])
        )