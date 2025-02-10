# ai_helper.py
import datetime
import json
import time

import requests

# 这两个全局变量在 init_ai() 中赋值，供 generate_report() 使用
API_URL = None
HEADERS = None


def init_ai(api_key, base_url=None):
    """
    初始化 API 调用的关键信息：
    - api_key (必填)
    - base_url (如果不是官方URL，就在此指定完整路径，包含 /chat/completions)
    """
    global API_URL, HEADERS

    if not api_key:
        raise ValueError("[AI] 未提供 api_key，无法调用 AI 接口。")

    # 如果你使用官方的 OpenAI 接口，可将这个值设置为
    # "https://api.openai.com/v1/chat/completions"
    API_URL = base_url or "https://api.openai.com/v1/chat/completions"

    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def generate_report(report_type, commits_data, model, since_date, until_date, date_str):
    """
    调用 AI 接口，生成日报 / 周报 / 月报：
    - report_type: 'daily' / 'weekly' / 'monthly'
    - commits_data: 来自 scan_git_repos 的提交列表
    - model: 模型名称
    """

    if not commits_data:
        print("[AI] 提交数据为空，无法生成报告。")
        return

    # 把提交数据序列化成 JSON 以便给AI
    diff_json = json.dumps(commits_data, ensure_ascii=False, indent=2)
    # 转换成 datetime.date 类型
    since_date = datetime.datetime.strptime(since_date, "%Y-%m-%d %H:%M:%S").date()
    until_date = datetime.datetime.strptime(until_date, "%Y-%m-%d %H:%M:%S").date()
    if report_type == "daily":
        filename = f"report/{date_str}_day-report.md"
        period_name = "日报"
    elif report_type == "weekly":
        filename = f"report/{since_date.strftime('%Y%m%d')}-{until_date.strftime('%Y%m%d')}_week-report.md"
        period_name = "周报"
    elif report_type == "monthly":
        filename = f"report/{since_date.strftime('%Y%m%d')}-{until_date.strftime('%Y%m%d')}_month-report.md"
        period_name = "月报"
    else:
        print(f"[AI] report_type={report_type} 无效，跳过报告生成。")
        return

    print(f"[AI] 正在生成{period_name}报告...\n")

    # 构造提示词
    system_prompt = f"你是一位资深前端经理，你需要根据下面的json来书写{period_name}。"
    user_prompt = (
        f"下面是我收集的 JSON 数据：\n{diff_json}\n\n"
        f"请根据以上 JSON 数据，输出符合以下格式的{period_name}：\n\n"
        f"格式要求：\n"
        f"摘要：（用一段话描述这{'天' if report_type == 'daily' else '周' if report_type == 'weekly' else '月'}干了什么）\n"
        f"本{'日' if report_type == 'daily' else '周' if report_type == 'weekly' else '月'}工作：（详细说明这{'天' if report_type == 'daily' else '周' if report_type == 'weekly' else '月'}干了些啥）\n"
    )

    # 组织请求 payload
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7
    }

    try:
        # 发起请求
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=600)
        response.raise_for_status()  # 若非 2xx，会抛出异常

        data = response.json()
        # 获取 AI 生成内容
        ai_text = data["choices"][0]["message"]["content"]
        usage_info = data.get("usage", {})
        prompt_tokens = usage_info.get("prompt_tokens", 0)
        completion_tokens = usage_info.get("completion_tokens", 0)
        total_tokens = usage_info.get("total_tokens", 0)

        # 写入报告文件
        with open(filename, "w", encoding="utf-8") as f:
            f.write(ai_text)
        # 下面是Ai的token用量信息，可以根据需求自行决定是否输出到文件
        # f.write("\n\n---\n")
        # f.write("**Tokens 用量信息**:\n")
        # f.write(f"- prompt_tokens: {prompt_tokens}\n")
        # f.write(f"- completion_tokens: {completion_tokens}\n")
        # f.write(f"- total_tokens: {total_tokens}\n")

        print(f"[AI] 已生成 {period_name}：{filename}")
        print(f"    tokens 用量: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")

    except requests.exceptions.RequestException as e:
        print(
            f"[AI] 调用 AI 接口失败: {e}")
        print(
            f"[AI] 可以在“gitOutput/prompt/xxx_prompt.txt”中找到输出的提示词在web中手动提问")
        with open(f"gitOutput/prompt/{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}_prompt.txt", "w",
                  encoding="utf-8") as f:
            f.write(system_prompt)
            f.write("\n")
            f.write(user_prompt)
    except Exception as e:
        print(f"[AI] 处理返回结果时出现异常: {e}")
