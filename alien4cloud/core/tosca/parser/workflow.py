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
        required_fields = ['id', 'name', 'workflow']
        for field in required_fields:
            if field not in data:
                raise ParserError(f"缺少必要字段: {field}")

        # 验证workflow
        if not isinstance(data['workflow'], dict):
            raise ParserError("workflow必须是字典类型")

        # 验证steps
        if 'steps' in data and not isinstance(data['steps'], dict):
            raise ParserError("steps必须是字典类型")

        # 验证步骤
        for step_data in data.get('workflow', {}).values():
            if 'type' not in step_data or 'target' not in step_data:
                raise ParserError(f"步骤缺少必要字段: type 或 target")
            
            # 验证步骤类型
            try:
                WorkflowStepType(step_data['type'])
            except ValueError:
                raise ParserError(f"步骤类型无效: {step_data['type']}")

        # 验证步骤依赖关系
        self._validate_step_dependencies(data.get('workflow', {}))

        return super().parse_dict(data)

    def _validate_step_dependencies(self, steps: Dict[str, Any]) -> None:
        """验证步骤依赖关系"""
        step_names = set(steps.keys())
        
        for step_name, step_data in steps.items():
            # 验证成功依赖
            for dep in step_data.get('on_success', []):
                if dep not in step_names:
                    raise ParserError(f"步骤 '{step_name}' 的成功依赖 '{dep}' 不存在")
            
            # 验证失败依赖
            for dep in step_data.get('on_failure', []):
                if dep not in step_names:
                    raise ParserError(f"步骤 '{step_name}' 的失败依赖 '{dep}' 不存在")
            
            # 检查循环依赖
            self._check_circular_dependencies(step_name, steps)

    def _check_circular_dependencies(self, start_step: str, steps: Dict[str, Any], visited: Set[str] = None) -> None:
        """检查循环依赖"""
        if visited is None:
            visited = set()
        
        if start_step in visited:
            raise ParserError(f"检测到循环依赖: {start_step}")
        
        visited.add(start_step)
        step_data = steps.get(start_step, {})
        
        # 检查所有依赖
        for dep in step_data.get('on_success', []) + step_data.get('on_failure', []):
            self._check_circular_dependencies(dep, steps, visited.copy())

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
            workflow = self.workflow_parser.parse_dict(data['workflow'])
            data['workflow'] = workflow
        except ParserError as e:
            raise ParserError(f"工作流定义验证失败: {str(e)}")

        return super().parse_dict(data) 