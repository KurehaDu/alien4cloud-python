from typing import Dict, Any
from datetime import datetime

from .models import WorkflowTemplate, WorkflowStep
from ..tosca.model.workflow import WorkflowStepType

class ConversionError(Exception):
    """转换错误"""
    pass

class WorkflowConverter:
    """工作流转换器"""
    
    def convert(self, workflow_def: Dict[str, Any]) -> WorkflowTemplate:
        """转换工作流定义为工作流模板"""
        try:
            # 创建工作流模板
            template = WorkflowTemplate(
                id=f"wf-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                name=workflow_def.get("name", "未命名工作流"),
                description=workflow_def.get("description"),
                version=workflow_def.get("version", "1.0.0"),
                inputs=workflow_def.get("inputs", {}),
                outputs=workflow_def.get("outputs", {}),
                metadata=workflow_def.get("metadata", {})
            )

            # 转换步骤
            steps = workflow_def.get("steps", {})
            for step_id, step_def in steps.items():
                step = self._convert_step(step_id, step_def)
                template.steps[step_id] = step

            return template
        except Exception as e:
            raise ConversionError(f"转换工作流定义失败: {str(e)}")

    def _convert_step(self, step_id: str, step_def: Dict[str, Any]) -> WorkflowStep:
        """转换工作流步骤"""
        # 确定步骤类型
        step_type = None
        operation = None
        target = None

        if "type" in step_def:
            step_type = step_def["type"]
        else:
            # 根据步骤定义推断类型
            if "node_operation" in step_def:
                step_type = WorkflowStepType.NODE_OPERATION.value
                operation = step_def["node_operation"]
                target = step_def.get("target")
            elif "relationship_operation" in step_def:
                step_type = WorkflowStepType.RELATIONSHIP_OPERATION.value
                operation = step_def["relationship_operation"]
                target = step_def.get("target_relationship")
            elif "call_operation" in step_def:
                step_type = WorkflowStepType.CALL_OPERATION.value
                operation = step_def["call_operation"]
            else:
                step_type = WorkflowStepType.INLINE.value

        # 创建步骤
        return WorkflowStep(
            id=step_id,
            name=step_def.get("name", step_id),
            type=step_type,
            target=target,
            operation=operation,
            inputs=step_def.get("inputs", {}),
            outputs=step_def.get("outputs", {}),
            on_success=step_def.get("on_success", []),
            on_failure=step_def.get("on_failure", [])
        )

    def to_tosca(self, template: WorkflowTemplate) -> Dict[str, Any]:
        """转换工作流模板为TOSCA定义"""
        workflow_def = {
            "tosca_definitions_version": "alien_dsl_2_0_0",
            "metadata": {
                "template_name": template.name,
                "template_version": template.version,
                "template_author": "alien4cloud-python"
            },
            "description": template.description,
            "topology_template": {
                "workflows": {
                    template.name: {
                        "description": template.description,
                        "inputs": template.inputs,
                        "steps": {}
                    }
                }
            }
        }

        # 转换步骤
        for step_id, step in template.steps.items():
            step_def = {
                "name": step.name,
                "inputs": step.inputs,
                "on_success": step.on_success,
                "on_failure": step.on_failure
            }

            # 根据步骤类型添加特定字段
            if step.type == WorkflowStepType.NODE_OPERATION.value:
                step_def["node_operation"] = step.operation
                if step.target:
                    step_def["target"] = step.target
            elif step.type == WorkflowStepType.RELATIONSHIP_OPERATION.value:
                step_def["relationship_operation"] = step.operation
                if step.target:
                    step_def["target_relationship"] = step.target
            elif step.type == WorkflowStepType.CALL_OPERATION.value:
                step_def["call_operation"] = step.operation

            workflow_def["topology_template"]["workflows"][template.name]["steps"][step_id] = step_def

        return workflow_def