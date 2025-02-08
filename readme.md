# 使用说明

本程序是一个多文件、可配置的 Git 仓库提交统计工具，并可选通过 AI 接口（兼容 OpenAI Chat Completion）自动生成日报/周报/月报。项目示例包含以下文件：

- `config.json`：配置文件（存储默认的 API Key、base_url、模型、默认统计周期等）
- `config.py`：加载并合并配置（命令行优先级 > 配置文件）
- `git_scanner.py`：Git 仓库扫描与提交统计逻辑
- `ai_helper.py`：AI 调用模块（可对接兼容 OpenAI 的 API）
- `index.py`：主程序入口，命令行参数解析与流程控制

## 功能概述

1. **扫描指定目录下的 Git 仓库**（递归查找所有含 `.git` 的项目）
2. **统计提交**（指定时间范围、作者过滤、排除特定文件的 diff），并输出到 `output.json`
3. 可选：生成日报 / 周报 / 月报
   - 将统计到的提交 JSON 数据交给 AI 模型，自动输出 Markdown 格式的工作报告，并附带 tokens 用量信息。

## 环境准备

1. **Python 3.7+**

2. **安装依赖**
     ```
     pip install -r requirements.txt
     ```

3. **Git 命令行工具**

   - 本工具需要调用本地 `git`，请确保系统中可用 `git` 命令。

4. **配置文件 `config.json`**（可选）

   - 如果你想使用 AI 功能（如自动生成日报/周报/月报），需要在此配置 `api_key` 或在命令行/环境变量提供；如果你不需要 AI 功能，可以忽略 Key 和 base_url。

   - 例子：

     ```
     {
       "api_key": "sk-xxxxx",
       "base_url": "https://api.openai.com/v1",
       "model": "gpt-3.5-turbo",
       "default_period": "weekly",
       "default_output_file": "output.json"
     }
     ```

## 文件说明

### 1. `config.py`

- **功能**：加载并合并配置文件和命令行参数。

- 主要函数

  - `load_config()`：读取并解析 `config.json`
  - `merge_config(cli_args, file_config)`：命令行参数与文件配置的合并逻辑

### 2. `git_scanner.py`

- **功能**：负责 Git 仓库扫描与提交数据收集。
  1. **查找所有 Git 仓库**
  2. **git log** 统计提交
  3. 收集 `commitInfo`、`codeDiff`、`diffLines` 等信息
  4. 生成并写出 `output.json`
  5. 返回统计结果（提交列表、仓库数、提交数、总行变动等）

### 3. `ai_helper.py`

- **功能**：AI 调用模块，可对接 OpenAI API 或其他兼容服务。

  - `init_ai(api_key, base_url)`：设置 key、base URL
  - `generate_report(...)`：使用 Chat Completion 模型生成日报/周报/月报，输出 Markdown 并记录 tokens 用量。

### 4. `index.py`

- **功能**：整合所有功能的主入口，命令行解析 + 业务流程控制。

- 主要流程
  1. **解析命令行参数**
  2. **加载并合并配置**（`config.py`）
  3. **初始化 AI**（如果需要生成报告并提供了 Key）
  4. **调用 `scan_git_repos(...)`** 做 Git 统计
  5. **打印统计结果**
  6. **可选：调用 `generate_report(...)`** 生成 AI 报告

## 使用方法

假设你已在项目根目录放好上面文件。通过 `python index.py [选项]` 运行脚本，常见的可用参数包括：

| 参数                | 说明                                                     | 示例                                                |
| ------------------- | -------------------------------------------------------- | --------------------------------------------------- |
| `--path` (必填)     | 要遍历的根目录，脚本会在该目录递归查找包含 `.git` 的项目 | `--path /Users/alice/workspace`                     |
| `--period`          | 统计周期，可选 `daily` / `weekly` / `monthly` / `all`    | `--period weekly`                                   |
| `--date`            | 只统计某一天 (YYYY-MM-DD)，会覆盖 `--period`             | `--date 2025-02-09`                                 |
| `--authors`         | 只统计特定作者，逗号分隔                                 | `--authors "Alice,Bob"`                             |
| `--excludes`        | 排除某些文件/路径的 diff，逗号分隔                       | `--excludes "*.json,dist/*"`                        |
| `--output`          | 指定输出的 JSON 文件名（若未指定则用配置或脚本默认值）   | `--output my_commits.json`                          |
| `--generate-report` | 是否生成 AI 报告，可选：`daily` / `weekly` / `monthly`   | `--generate-report weekly`                          |
| `--api-key`         | 如果不想使用配置文件里的 Key，可在命令行上显式传入       | `--api-key "sk-xxxxxx"`                             |
| `--baseurl`         | 自定义 AI 接口 URL（若非官方 OpenAI）                    | `--baseurl "https://xxx.volcengineapi.com/v1/chat"` |
| `--model`           | 指定模型名称（默认为配置文件中的）                       | `--model "gpt-4"`                                   |

### 示例 1：只做统计

```
python index.py \
  --path /path/to/your/projects \
  --period weekly \
  --excludes "*.json,dist/*"
```

- 脚本会递归扫描 `/path/to/your/projects` 下的所有 Git 仓库，统计最近一周的提交信息并写入 `output.json`。
- 不会生成任何 AI 报告。

### 示例 2：指定一天 + 生成日报

```
python index.py \
  --path /path/to/your/projects \
  --date 2025-02-09 \
  --generate-report daily
```

- 只统计 `2025-02-09` 当天的提交，并生成 `day-report.md` 日报。
- `api_key` 可以从 `config.json` 中读取。如果未配置且没在命令行提供，生成报告会失败或报错。

### 示例 3：指定作者 + 生成周报

```
python index.py \
  --path . \
  --period weekly \
  --authors "Alice,Bob" \
  --generate-report weekly \
  --output all_commits.json
```

- 扫描当前目录，统计最近一周 `Alice` 和 `Bob` 的提交。
- 统计结果写到 `all_commits.json`。
- AI 自动生成周报到 `week-report.md`。

### 示例 4：自定义 AI 接口

如果你使用 OpenAI 兼容服务，你可以：

```
python index.py \
  --path . \
  --period monthly \
  --generate-report monthly \
  --api-key "自建服务的Token" \
  --baseurl "https://xxx.volcengineapi.com/v1/chat/completions"
```

- 将自动改用你提供的 `--baseurl`，并使用该 Token 进行调用。

------

## 常见问题 FAQ

1. **如何避免输入/泄露 Key？**
   - 可将 Key 写到 `config.json` 并加入 `.gitignore`；或设置环境变量 `OPENAI_API_KEY`，在代码中读取。
2. **提交量很多，脚本较慢怎么办？**
   - 多数时间花在 `git show` & `git log` 上，建议缩小统计范围（指定 `--date` 或 `--period`），或者定期汇总、拆分仓库。
3. **如何改用 GPT-4 / 其他模型？**
   - 在 `--model` 参数或 `config.json` 里写入对应的模型名称，如 `"gpt-4"`、`"deepseek-reasoner"` 等。
4. **AI 报告里的 tokens 用量如何计算？**
   - 服务器返回数据中自带 `usage` 字段，脚本会写入报告结尾并在控制台打印。
5. **如何本地调试而不调用AI？**
   - 不加 `--generate-report` 即可只跑统计逻辑。或在 `config.json` 不写 `api_key` 且不传入 `--api-key`。

------