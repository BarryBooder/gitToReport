# index.py

import argparse
import sys

from config import load_config, merge_config
from git_scanner import scan_git_repos
from ai_helper import init_ai, generate_report


def main():
    parser = argparse.ArgumentParser(description="Git统计 + AI报告")

    # 常规 Git 统计参数
    parser.add_argument("--path", required=True, help="要遍历的根目录")
    parser.add_argument("--period", choices=["daily", "weekly", "monthly", "all"],
                        help="统计周期，可选：daily/weekly/monthly/all")
    parser.add_argument("--date", help="只统计某一天 (YYYY-MM-DD)，若指定则覆盖 --period")
    parser.add_argument("--authors", help="逗号分隔的作者列表，如: Alice,Bob")
    parser.add_argument("--excludes", help="排除的文件/路径模式，逗号分隔，如: *.json,dist/*")
    parser.add_argument("--output", help="输出 JSON 文件名，默认见 config.json 或脚本默认")

    # AI 相关，可从命令行也可从配置文件
    parser.add_argument("--api-key", help="AI 接口的 Key，若不提供则从配置文件读取")
    parser.add_argument("--baseurl", help="AI 接口的 Base URL（若不是官方OpenAI）")
    parser.add_argument("--model", help="AI 模型，如 gpt-3.5-turbo / gpt-4 等")

    # 是否生成报告
    parser.add_argument("--generate-report", choices=["daily", "weekly", "monthly"],
                        help="生成对应的 日报/周报/月报（输出 day-report.md/week-report.md/month-report.md）")

    args = parser.parse_args()

    # 1) 先加载文件配置
    file_cfg = load_config()  # 默认读取 config.json
    # 2) 合并命令行与文件配置
    final_cfg = merge_config(args, file_cfg)

    # 3) 提取实际配置
    root_path = args.path
    date_str = args.date
    authors_str = args.authors.strip() if args.authors else ""
    excludes_str = args.excludes.strip() if args.excludes else ""
    period = args.period if args.period else final_cfg["default_period"]
    output_file = args.output if args.output else final_cfg["default_output_file"]

    # 4) 初始化 AI (若后续需要 generate_report 才用到)
    #    这里不会立即发请求，只是设置好 key 和 base_url
    if final_cfg["api_key"]:
        try:
            init_ai(api_key=final_cfg["api_key"], base_url=final_cfg["base_url"])
        except ValueError as e:
            print(e)
            sys.exit(1)
    else:
        # 如果既没在命令行也没在 config.json 配置 key，
        # 但用户又要生成报告 => 会报错
        if args.generate_report:
            print("[警告] 未提供 API Key，但尝试生成AI报告可能会失败。")

    # 5) 执行 Git 扫描
    (commits_data, repo_count, total_commits, total_diff_lines, since_date, until_date, actual_period
     ) = scan_git_repos(
        root_path=root_path,
        period=period,
        single_day_str=date_str,
        authors_str=authors_str,
        excludes_str=excludes_str,
        output_json=output_file
    )

    # 6) 输出统计信息
    print("========== 统计结果 ==========")
    if date_str:
        print(f"统计日期：{date_str}")
    else:
        print(f"统计周期：{actual_period} (时间范围: {since_date} ~ {until_date})")

    if authors_str:
        print(f"指定作者：{authors_str.split(',')}")
    if excludes_str:
        print(f"排除模式：{excludes_str.split(',')}")

    print(f"共遍历到的 Git 仓库数：{repo_count}")
    print(f"符合条件的提交总数：{total_commits}")
    print(f"累计 diff 行数：{total_diff_lines}")
    print("================================")
    print(f"[完成] 提交详情已写入 {output_file}")

    # 7) 若需要生成AI报告，则调用 generate_report
    if args.generate_report:
        # 使用 final_cfg["model"] 作为默认模型
        generate_report(args.generate_report, commits_data, model=final_cfg["model"])


if __name__ == "__main__":
    main()
