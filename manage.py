#!/usr/bin/env python
"""画己职测 — Django 命令行管理工具入口。

品牌：画己职测
项目：career_test
默认配置模块：career_test.settings.dev
"""

import os
import sys


def main() -> None:
    """执行命令行管理任务。

    通过 ``DJANGO_SETTINGS_MODULE`` 环境变量指向开发配置，
    可在运行前覆盖为 ``career_test.settings.prod`` 等其他环境配置。
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "career_test.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("无法导入 Django，请确认 Django 已安装且虚拟环境已激活。") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
