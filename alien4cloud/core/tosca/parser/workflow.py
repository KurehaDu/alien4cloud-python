from typing import Any, Dict, Set
from .base import BaseParser, ParserError
from ..model.workflow import (
    WorkflowDefinition, 
    WorkflowTemplate, 
    WorkflowStep,
    WorkflowStepType
)

class WorkflowDefinitionParser(BaseParser):
    """工作流定义解析器"""
    
    def __init__(self):
        super().__init__(WorkflowDefinition)

    def parse_dict(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """解析工作流定义数据"""
        # 验证必要字段
        required_fields = ['id', 'name', 'steps']
        for field in required_fields:
            if field not in data:
                raise ParserError(f"缺少必要字段: {field}")

        # 验证steps
        if not isinstance(data['steps'], dict):
            raise ParserError("steps必须是字典类型")

        for step_name, step_data in data['steps'].items():
            if 'type' not in step_data or 'target' not in step_data:
                raise ParserError(f"步骤 '{step_name}' 缺少必要字段: type 或 target")
            
            # 验证步骤类型
            try:
                WorkflowStepType(step_data['type'])
            except ValueError:
                raise ParserError(f"步骤 '{step_name}' 的类型无效: {step_data['type']}")

        # 验证步骤依赖关系
        self._validate_step_dependencies(data['steps'])

        return super().parse_dict(data)

    def _validate_step_dependencies(self, steps: Dict[str, Any]) -> None:
        """验证步骤依赖关系"""
        step_names = set(steps.keys())
        
        for step_name, step_data in steps.items():
            # 验证on_success引用
            for dep in step_data.get('on_success', []):
                if dep not in step_names:
                    raise ParserError(f"步骤 '{step_name}' 的on_success引用了不存在的步骤: {dep}")
            
            # 验证on_failure引用
            for dep in step_data.get('on_failure', []):
                if dep not in step_names:
                    raise ParserError(f"步骤 '{step_name}' 的on_failure引用了不存在的步骤: {dep}")
            
            # 检测循环依赖
            self._check_circular_dependencies(steps, step_name)

    def _check_circular_dependencies(self, steps: Dict[str, Any], start_step: str, visited: Set[str] = None) -> None:
        """检测循环依赖"""
        if visited is None:
            visited = set()

        if start_step in visited:
            raise ParserError(f"检测到循环依赖，从步骤 '{start_step}' 开始")

        visited.add(start_step)
        step_data = steps[start_step]

        # 检查所有依赖
        for dep in step_data.get('on_success', []) + step_data.get('on_failure', []):
            self._check_circular_dependencies(steps, dep, visited.copy())

class WorkflowTemplateParser(BaseParser):
    """工作流模板解析器"""
    
    def __init__(self):
        super().__init__(WorkflowTemplate)
        self.workflow_parser = WorkflowDefinitionParser()

    def parse_dict(self, data: Dict[str, Any]) -> WorkflowTemplate:
        """解析工作流模板数据"""
        # 验证必要字段
        required_fields = ['id', 'name', 'workflow']
        for field in required_fields:
            if field not in data:
                raise ParserError(f"缺少必要字段: {field}")

        # 验证工作流定义
        if not isinstance(data['workflow'], dict):
            raise ParserError("workflow必须是字典类型")

        # 使用工作流解析器验证工作流定义
        try:
            self.workflow_parser.parse_dict(data['workflow'])
        except ParserError as e:
            raise ParserError(f"工作流定义验证失败: {str(e)}")

        return super().parse_dict(data) 