from typing import Any, Dict, List, Optional, Type, TypeVar
from ..model.base import BaseModel, ToscaType

T = TypeVar('T', bound=BaseModel)

class ValidationError(Exception):
    """验证错误"""
    def __init__(self, message: str, path: Optional[str] = None):
        self.message = message
        self.path = path
        super().__init__(f"{path + ': ' if path else ''}{message}")

class BaseValidator:
    """基础验证器"""
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class

    def validate(self, data: Dict[str, Any], path: str = "") -> List[ValidationError]:
        """验证数据"""
        errors = []
        
        # 验证必要字段
        required_fields = ['id', 'name']
        for field in required_fields:
            if field not in data:
                errors.append(ValidationError(f"缺少必要字段: {field}", path))

        # 验证字段类型
        if 'id' in data and not isinstance(data['id'], str):
            errors.append(ValidationError("id必须是字符串类型", f"{path}.id"))
        if 'name' in data and not isinstance(data['name'], str):
            errors.append(ValidationError("name必须是字符串类型", f"{path}.name"))
        if 'description' in data and not isinstance(data['description'], (str, type(None))):
            errors.append(ValidationError("description必须是字符串类型", f"{path}.description"))
        if 'metadata' in data and not isinstance(data['metadata'], dict):
            errors.append(ValidationError("metadata必须是字典类型", f"{path}.metadata"))

        return errors

class ToscaTypeValidator(BaseValidator):
    """TOSCA类型验证器"""
    
    def validate(self, data: Dict[str, Any], path: str = "") -> List[ValidationError]:
        """验证TOSCA类型数据"""
        errors = super().validate(data, path)

        # 验证版本
        if 'version' not in data:
            errors.append(ValidationError("缺少必要字段: version", path))
        elif not isinstance(data['version'], str):
            errors.append(ValidationError("version必须是字符串类型", f"{path}.version"))
        elif not self._validate_version(data['version']):
            errors.append(ValidationError("无效的版本格式", f"{path}.version"))

        # 验证derived_from
        if 'derived_from' in data and not isinstance(data['derived_from'], (str, type(None))):
            errors.append(ValidationError("derived_from必须是字符串类型", f"{path}.derived_from"))

        # 验证properties
        if 'properties' in data:
            if not isinstance(data['properties'], dict):
                errors.append(ValidationError("properties必须是字典类型", f"{path}.properties"))
            else:
                for prop_name, prop_data in data['properties'].items():
                    if not isinstance(prop_data, dict):
                        errors.append(ValidationError(
                            f"属性 '{prop_name}' 必须是字典类型", 
                            f"{path}.properties.{prop_name}"
                        ))

        return errors

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