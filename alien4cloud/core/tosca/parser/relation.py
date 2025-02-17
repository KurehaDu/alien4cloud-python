from typing import Any, Dict
from .base import BaseParser, ParserError
from ..model.relation import RelationshipType, RelationshipValidSource, RelationshipValidTarget

class RelationshipTypeParser(BaseParser):
    """关系类型解析器"""
    
    def __init__(self):
        super().__init__(RelationshipType)

    def parse_dict(self, data: Dict[str, Any]) -> RelationshipType:
        """解析关系类型数据"""
        # 验证必要字段
        required_fields = ['id', 'name', 'version']
        for field in required_fields:
            if field not in data:
                raise ParserError(f"缺少必要字段: {field}")

        # 验证版本格式
        version = data['version']
        if not self._validate_version(version):
            raise ParserError(f"无效的版本格式: {version}")

        # 验证valid_sources
        if 'valid_sources' in data:
            for source in data['valid_sources']:
                if 'node_type' not in source:
                    raise ParserError("有效源缺少必要字段: node_type")

        # 验证valid_targets
        if 'valid_targets' in data:
            for target in data['valid_targets']:
                if 'node_type' not in target:
                    raise ParserError("有效目标缺少必要字段: node_type")

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