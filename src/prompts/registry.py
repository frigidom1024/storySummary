"""Prompt 注册表，支持默认提示词 + 运行时覆盖"""

import os
from typing import Dict, Callable, Any
from string import Template


class PromptRegistry:
    """Prompt 注册表，支持默认提示词 + 运行时覆盖"""

    def __init__(self):
        self._templates: Dict[str, str] = {}
        self._builders: Dict[str, Callable[..., str]] = {}

    def register(self, key: str, template: str):
        """运行时注册自定义提示词"""
        self._templates[key] = template

    def register_builder(self, key: str, builder: Callable[..., str]):
        """注册一个 builder 函数，用于动态构建提示词"""
        self._builders[key] = builder

    def get(self, key: str, **kwargs) -> str:
        """获取提示词，支持占位符替换"""
        if key in self._templates:
            template = self._templates[key]
            if kwargs:
                try:
                    t = Template(template)
                    return t.safe_substitute(**kwargs)
                except Exception:
                    return template
            return template
        if key in self._builders:
            return self._builders[key](**kwargs)
        raise KeyError(f"Prompt not found: {key}")

    def has(self, key: str) -> bool:
        """检查是否存在某个提示词"""
        return key in self._templates or key in self._builders


# 全局注册表实例
global_registry = PromptRegistry()


def get_prompt(key: str, **kwargs) -> str:
    """快捷获取提示词"""
    return global_registry.get(key, **kwargs)


def register_prompt(key: str, template: str):
    """快捷注册提示词"""
    global_registry.register(key, template)


def register_builder(key: str, builder: Callable[..., str]):
    """快捷注册 builder"""
    global_registry.register_builder(key, builder)
