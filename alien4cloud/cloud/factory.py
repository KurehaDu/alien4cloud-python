# alien4cloud/cloud/factory.py

import importlib
from typing import Dict, List, Optional, Type

from .base import CloudProvider
from .config import CloudConfig
from .errors import ConfigError

class CloudProviderFactory:
    """云平台提供者工厂"""
    
    _providers: Dict[str, Type[CloudProvider]] = {}
    _instances: Dict[str, CloudProvider] = {}
    _configs: Dict[str, CloudConfig] = {}
    _default_provider: Optional[str] = None

    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[CloudProvider]) -> None:
        """注册云平台提供者"""
        if provider_type in cls._providers:
            raise ConfigError(f"云平台类型 {provider_type} 已经注册")
        cls._providers[provider_type] = provider_class

    @classmethod
    def register_config(cls, config: CloudConfig) -> None:
        """注册云平台配置"""
        config.validate()
        if config.name in cls._configs:
            raise ConfigError(f"云平台 {config.name} 已经配置")
        if config.type not in cls._providers:
            raise ConfigError(f"未知的云平台类型 {config.type}")
        
        cls._configs[config.name] = config
        if config.default:
            if cls._default_provider and cls._default_provider != config.name:
                old_config = cls._configs[cls._default_provider]
                old_config.default = False
            cls._default_provider = config.name

    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> CloudProvider:
        """获取云平台提供者实例"""
        if name is None:
            if cls._default_provider is None:
                raise ConfigError("未设置默认云平台")
            name = cls._default_provider

        if name not in cls._configs:
            raise ConfigError(f"未找到云平台配置 {name}")
        
        if name not in cls._instances:
            config = cls._configs[name]
            if not config.enabled:
                raise ConfigError(f"云平台 {name} 已禁用")
            provider_class = cls._providers[config.type]
            cls._instances[name] = provider_class()

        return cls._instances[name]

    @classmethod
    def list_providers(cls) -> List[CloudConfig]:
        """列出所有云平台配置"""
        return list(cls._configs.values())

    @classmethod
    def get_config(cls, name: str) -> CloudConfig:
        """获取云平台配置"""
        if name not in cls._configs:
            raise ConfigError(f"未找到云平台配置 {name}")
        return cls._configs[name]

    @classmethod
    def remove_config(cls, name: str) -> None:
        """移除云平台配置"""
        if name not in cls._configs:
            raise ConfigError(f"未找到云平台配置 {name}")
        config = cls._configs[name]
        if config.default:
            cls._default_provider = None
        del cls._configs[name]
        if name in cls._instances:
            del cls._instances[name]

    @classmethod
    def clear(cls) -> None:
        """清除所有配置和实例"""
        cls._configs.clear()
        cls._instances.clear()
        cls._default_provider = None

    @classmethod
    def load_provider(cls, module_path: str) -> None:
        """从模块加载提供者"""
        try:
            importlib.import_module(module_path)
        except ImportError as e:
            raise ConfigError(f"无法加载模块 {module_path}: {str(e)}") 