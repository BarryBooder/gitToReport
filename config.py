# config.py

import json
import os

DEFAULT_CONFIG_FILE = "config.json"

def load_config(config_file=DEFAULT_CONFIG_FILE):
    """
    从配置文件中加载 JSON，并返回字典。
    若文件不存在或无法解析，则返回空字典。
    """
    if not os.path.exists(config_file):
        print(f"[配置警告] 未找到配置文件 {config_file}，将使用空配置。")
        return {}
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[配置错误] 解析 {config_file} 失败: {e}")
        return {}

def merge_config(cli_args, file_config):
    """
    将命令行参数 (cli_args) 与文件配置 (file_config) 合并并返回最终配置字典。

    优先级(高->低)：
    1. 命令行参数(若非空/非None)
    2. 配置文件 file_config
    3. 默认值(在这里可设定一些硬编码)

    cli_args: 命令行解析得到的 Namespace (或类似字典)
    file_config: load_config 返回的字典
    """
    final_cfg = {}

    # 1) Base URL
    final_cfg["base_url"] = (
        cli_args.baseurl if hasattr(cli_args, "baseurl") and cli_args.baseurl
        else file_config.get("base_url", "https://api.openai.com/v1")
    )

    # 2) API Key
    final_cfg["api_key"] = (
        cli_args.api_key if hasattr(cli_args, "api_key") and cli_args.api_key
        else file_config.get("api_key", "")
    )

    # 3) Model
    final_cfg["model"] = (
        cli_args.model if hasattr(cli_args, "model") and cli_args.model
        else file_config.get("model", "gpt-3.5-turbo")
    )

    # 4) Period (daily / weekly / monthly / all)
    final_cfg["default_period"] = (
        cli_args.period if hasattr(cli_args, "period") and cli_args.period
        else file_config.get("default_period", "weekly")
    )

    # 5) Output JSON
    final_cfg["default_output_file"] = (
        cli_args.output if hasattr(cli_args, "output") and cli_args.output
        else file_config.get("default_output_file", "output.json")
    )

    return final_cfg
