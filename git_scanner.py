# git_scanner.py

import os
import sys
import subprocess
import re
from datetime import datetime, timedelta
import json
from tqdm import tqdm

def compute_period_dates(period):
    """
    根据 period 返回 (since_date, until_date) 字符串。
    period 可选：daily, weekly, monthly, all
    """
    now = datetime.now()

    if period == "daily":
        since = now - timedelta(days=1)
        until = now
    elif period == "weekly":
        since = now - timedelta(days=7)
        until = now
    elif period == "monthly":
        since = now - timedelta(days=30)
        until = now
    elif period == "all":
        since = datetime(1970, 1, 1)
        until = now
    else:
        # 若 period 不合法，就当 all
        since = datetime(1970, 1, 1)
        until = now

    return since.strftime('%Y-%m-%d 00:00:00'), until.strftime('%Y-%m-%d 23:59:59')


def compute_single_day_dates(date_str):
    """
    如果指定某一天（YYYY-MM-DD），则返回该天的起止时间。
    """
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"[错误] --date 参数格式不正确，应为 YYYY-MM-DD，收到: {date_str}")
        sys.exit(1)
    since = day.strftime("%Y-%m-%d 00:00:00")
    until = day.strftime("%Y-%m-%d 23:59:59")
    return since, until


def get_git_repos(root_path):
    """
    递归查找含 .git 的仓库根目录，并显示进度。
    """
    git_repos = []
    print("正在查找 Git 仓库，请稍候...")

    for dirpath, dirnames, filenames in tqdm(os.walk(root_path), desc="已扫描", unit="dir"):
        if '.git' in dirnames:
            git_repos.append(dirpath)

    return git_repos


def get_commits(repo_path, since_date, until_date, authors_list):
    """
    在仓库 repo_path 中，获取指定时间范围&作者条件的所有提交哈希。
    """
    cmd = [
        "git", "-C", repo_path,
        "log",
        f"--since={since_date}",
        f"--until={until_date}",
        "--pretty=format:%H"
    ]

    if authors_list:
        pattern = "|".join(re.escape(a) for a in authors_list)
        cmd.append("--perl-regexp")
        cmd.append(f"--author={pattern}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[警告] 获取提交哈希出错：{result.stderr.strip()} (仓库: {repo_path})")
        return []

    commits = result.stdout.strip().split('\n')
    commits = [c for c in commits if c]
    return commits


def get_commit_info(repo_path, commit_hash):
    """
    获取提交的元信息（作者、日期、描述），不含 diff
    """
    cmd = [
        "git", "-C", repo_path,
        "show",
        "--no-patch",
        "--pretty=medium",
        commit_hash
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_code_diff(repo_path, commit_hash, exclude_list=None):
    """
    获取提交的完整 diff（不含提交元信息），排除 exclude_list 中的文件。
    """
    if exclude_list is None:
        exclude_list = []
    cmd = [
        "git", "-C", repo_path,
        "show",
        "--pretty=format:",
        commit_hash,
        "--"
    ]
    for ex_item in exclude_list:
        cmd.append(f":(exclude){ex_item}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout


def get_diff_lines_of_commit(repo_path, commit_hash, exclude_list=None):
    """
    统计 diff 行数（插入+删除）
    """
    if exclude_list is None:
        exclude_list = []
    cmd = [
        "git", "-C", repo_path,
        "show",
        "--stat",
        commit_hash,
        "--"
    ]
    for ex_item in exclude_list:
        cmd.append(f":(exclude){ex_item}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0

    total_diff_lines = 0
    lines = result.stdout.strip().split('\n')
    for line in reversed(lines):
        if ("files changed" in line) and ("insertions" in line or "deletions" in line):
            parts = line.strip().split(',')
            insertions = 0
            deletions = 0
            for p in parts:
                p = p.strip()
                if 'insertions' in p:
                    insertions = int(''.join(filter(str.isdigit, p)))
                elif 'deletions' in p:
                    deletions = int(''.join(filter(str.isdigit, p)))
            total_diff_lines = insertions + deletions
            break
    return total_diff_lines


def scan_git_repos(root_path, period=None, single_day_str=None,
                   authors_str="", excludes_str="", output_json="gitOutput/output.json"):
    """
    综合的扫描函数，用于外部调用。
    """
    # 计算实际时间范围
    if single_day_str:
        since_date, until_date = compute_single_day_dates(single_day_str)
        actual_period = "single-day"
    else:
        since_date, until_date = compute_period_dates(period or "all")
        actual_period = period or "all"

    # 解析 authors / excludes
    authors_list = [a.strip() for a in authors_str.split(",") if a.strip()] if authors_str else []
    exclude_list = [x.strip() for x in excludes_str.split(",") if x.strip()] if excludes_str else []

    # 查找仓库
    git_repos = get_git_repos(root_path)
    repo_count = len(git_repos)

    if not git_repos:
        print("未找到 Git 仓库，退出...")
        return [], 0, 0, 0, since_date, until_date, actual_period

    total_commits = 0
    total_diff_lines = 0
    commits_data = []

    # 遍历所有仓库，添加进度条
    for repo_path in tqdm(git_repos, desc="Repositories 扫描进度", unit="repo"):
        commit_hashes = get_commits(repo_path, since_date, until_date, authors_list)
        total_commits += len(commit_hashes)

        # 遍历每个提交，添加进度条
        for commit_hash in tqdm(commit_hashes, desc=f"正在处理 {os.path.basename(repo_path)} 中的 Commits", unit="commit", leave=False):
            commit_info = get_commit_info(repo_path, commit_hash)
            code_diff = get_code_diff(repo_path, commit_hash, exclude_list)
            diff_line_count = get_diff_lines_of_commit(repo_path, commit_hash, exclude_list)
            total_diff_lines += diff_line_count

            commits_data.append({
                "commitInfo": commit_info,
                "codeDiff": code_diff
            })

    # 写出到 JSON 文件
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(commits_data, f, ensure_ascii=False, indent=4)

    return commits_data, repo_count, total_commits, total_diff_lines, since_date, until_date, actual_period
