from typing import Any, Dict
from .base import BaseParser, ParserError
from ..model.node import NodeType, NodeRequirement, NodeCapability

class NodeTypeParser(BaseParser):
    """节点类型解析器"""
    
    def __init__(self):
        super().__init__(NodeType)

    def parse_dict(self, data: Dict[str, Any]) -> NodeType:
        """解析节点类型数据"""
        # 验证必要字段
        required_fields = ['id', 'name', 'version']
        for field in required_fields:
            if field not in data:
                raise ParserError(f"缺少必要字段: {field}")

        # 验证版本格式
        version = data['version']
        if not self._validate_version(version):
            raise ParserError(f"无效的版本格式: {version}")

        # 验证requirements
        if 'requirements' in data:
            for req_name, req_data in data['requirements'].items():
                if 'type' not in req_data or 'relationship' not in req_data:
                    raise ParserError(f"需求 '{req_name}' 缺少必要字段: type 或 relationship")

        # 验证capabilities
        if 'capabilities' in data:
            for cap_name, cap_data in data['capabilities'].items():
                if 'type' not in cap_data:
                    raise ParserError(f"能力 '{cap_name}' 缺少必要字段: type")

        return super().parse_dict(data)

    def _validate_version(self, version: str) -> bool:
        """验证版本格式"""
        try:
            parts = version.split('.')
            if len(parts) < 2:
                return False
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False 