from typing import Dict, Any
import yaml
import logging
from datetime import datetime

from ..model.workflow import WorkflowStepType
from ...workflow.models import WorkflowTemplate, WorkflowStep

logger = logging.getLogger(__name__)

class ParserError(Exception):
    """解析错误"""
    pass

class WorkflowDefinitionParser:
    """工作流定义解析器"""
    
    def parse(self, data: Dict[str, Any]) -> WorkflowTemplate:
        """解析工作流定义"""
        try:
            # 验证必要字段
            if "tosca_definitions_version" not in data:
                raise ParserError("缺少TOSCA版本定义")
            if "topology_template" not in data:
                raise ParserError("缺少拓扑模板定义")
            if "workflows" not in data["topology_template"]:
                raise ParserError("缺少工作流定义")

            # 获取第一个工作流定义
            workflow_name = next(iter(data["topology_template"]["workflows"]))
            workflow_def = data["topology_template"]["workflows"][workflow_name]

            # 创建工作流模板
            template = WorkflowTemplate(
                id=f"wf-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                name=workflow_name,
                description=workflow_def.get("description"),
                inputs=workflow_def.get("inputs", {}),
                outputs=workflow_def.get("outputs", {})
            )

            # 解析步骤
            steps = workflow_def.get("steps", {})
            for step_id, step_def in steps.items():
                step = self._parse_step(step_id, step_def)
                template.steps[step_id] = step

            return template
        except Exception as e:
            raise ParserError(f"解析工作流定义失败: {str(e)}")

    def _parse_step(self, step_id: str, step_def: Dict[str, Any]) -> WorkflowStep:
        """解析工作流步骤"""
        # 确定步骤类型
        step_type = None
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
            target = None
        else:
            step_type = WorkflowStepType.INLINE.value
            operation = None
            target = None

        # 创建步骤
        return WorkflowStep(
            id=step_id,
            name=step_def.get("name", step_id),
            type=step_type,
            target=target,
            operation=operation,
            inputs=step_def.get("inputs", {}),
            on_success=step_def.get("on_success", []),
            on_failure=step_def.get("on_failure", [])
        )

    def parse_file(self, file_path: str) -> WorkflowTemplate:
        """从文件解析工作流定义"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return self.parse(data)
        except Exception as e:
            raise ParserError(f"解析文件失败: {str(e)}")

    def parse_string(self, content: str) -> WorkflowTemplate:
        """从字符串解析工作流定义"""
        try:
            data = yaml.safe_load(content)
            return self.parse(data)
        except Exception as e:
            raise ParserError(f"解析字符串失败: {str(e)}") 