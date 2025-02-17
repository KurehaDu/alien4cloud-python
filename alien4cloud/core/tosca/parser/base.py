from typing import Any, Dict, Optional, Type, TypeVar
import yaml
from ..model.base import BaseModel, ToscaType

T = TypeVar('T', bound=BaseModel)

class ParserError(Exception):
    """解析器错误"""
    pass

class BaseParser:
    """TOSCA基础解析器"""
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class

    def parse_file(self, file_path: str) -> T:
        """解析YAML文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return self.parse_dict(data)
        except yaml.YAMLError as e:
            raise ParserError(f"YAML解析错误: {str(e)}")
        except Exception as e:
            raise ParserError(f"文件解析错误: {str(e)}")

    def parse_string(self, content: str) -> T:
        """解析YAML字符串"""
        try:
            data = yaml.safe_load(content)
            return self.parse_dict(data)
        except yaml.YAMLError as e:
            raise ParserError(f"YAML解析错误: {str(e)}")
        except Exception as e:
            raise ParserError(f"字符串解析错误: {str(e)}")

    def parse_dict(self, data: Dict[str, Any]) -> T:
        """解析字典数据"""
        try:
            return self.model_class.from_dict(data)
        except KeyError as e:
            raise ParserError(f"缺少必要字段: {str(e)}")
        except Exception as e:
            raise ParserError(f"数据解析错误: {str(e)}")

class ToscaTypeParser(BaseParser):
    """TOSCA类型解析器"""
    
    def __init__(self):
        super().__init__(ToscaType)

    def parse_dict(self, data: Dict[str, Any]) -> ToscaType:
        """解析TOSCA类型数据"""
        # 验证必要字段
        required_fields = ['id', 'name', 'version']
        for field in required_fields:
            if field not in data:
                raise ParserError(f"缺少必要字段: {field}")

        # 验证版本格式
        version = data['version']
        if not self._validate_version(version):
            raise ParserError(f"无效的版本格式: {version}")

        return super().parse_dict(data)

    def _validate_version(self, version: str) -> bool:
        """验证版本格式"""
        try:
            # 简单的版本格式验证，可以根据需要扩展
            parts = version.split('.')
            if len(parts) < 2:
                return False
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False 