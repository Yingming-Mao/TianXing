# TianXing（天行）

[English](README.md) | 中文

自动化论文审稿与改进工具，基于 [Claude Code](https://claude.ai/claude-code) 构建。这是一个**独立的工具仓库**——安装一次，即可在你的所有论文项目中使用。

系统运行 Review → Plan → Modify → Validate → Record 循环，迭代式提升论文质量。核心目标：**去除 AI 生成痕迹**，优化叙事逻辑和实验设计。

## 安装

```bash
git clone https://github.com/Yingming-Mao/TianXing.git
cd TianXing
pip install -e .
```

## 快速开始

### 1. 初始化你的论文项目

```bash
cd /path/to/your-paper-project
bash /path/to/TianXing/scripts/setup_project.sh
```

脚本会自动创建所需的目录结构、复制配置模板，并配置 Claude Code 权限（`.claude/settings.json`），使 `/review-loop` 可以自动运行，无需每步手动确认。

### 2. 配置

编辑论文项目中的 `config.yaml`，适配你的项目：

```yaml
compile:
  main_file: "paper/main.tex"

# 如果你的实验代码运行在单独的环境中，在这里指定：
project:
  env: "myenv"                # conda 环境名
  # env: "/path/to/envs/myenv"       # 或 conda 环境路径
  # env: "/path/to/venv/bin/python"  # 或 virtualenv 的 python 路径
```

TianXing 本身可以装在任何地方——当需要运行你的实验代码或测试时，会自动在指定环境中执行。不填或留空则使用当前环境。

### 3. 运行 Review 循环

在论文项目中打开 Claude Code，执行：

```
/review-loop
```

## 工具列表

所有工具输出结构化 JSON，通过 `python -m tianxing.<模块名>` 调用。

| 工具 | 用途 |
|------|------|
| `checkpoint_repo` | 修改前创建 git 检查点（tag） |
| `rollback_repo` | 回滚到之前的检查点 |
| `compile_paper` | 编译 LaTeX 并报告错误/警告 |
| `run_tests` | 运行项目测试（仅在代码被修改且测试已启用时运行） |
| `record_round` | 保存审稿产物（review、plan、changes） |
| `update_status` | 跟踪审稿进度和分数 |
| `notify_status` | 记录通知日志 |
| `collect_metrics` | 扫描 results 目录收集指标 |
| `experiment_map` | 自动发现和查询 论文↔代码↔测试↔结果 的双向映射 |

也可以使用 CLI 入口：`tianxing <命令> [参数]`

## 仓库结构

```
tianxing/     Python 包（可 pip 安装）
commands/               Claude Code slash command
skills/                 详细的 Skill prompt
prompts/                子 Agent prompt 模板（reviewer、planner、rewriter、summarizer）
templates/              用户项目模板文件（AGENT.md、.gitignore）
scripts/                项目初始化脚本
tests/                  工具自身的测试
```

## 用户项目使用后的结构

运行 `setup_project.sh` 后，你的论文项目会变成：

```
my-paper-project/
├── AGENT.md                 # Agent 行为规则
├── config.yaml              # 项目配置
├── experiment_map.json      # 实验知识图谱（自动生成，可手动编辑）
├── .claude/commands/
│   └── review-loop.md       # Slash command
├── paper/                   # LaTeX 源文件
├── code/                    # 实验代码
├── results/                 # 实验结果
├── reviews/                 # 自动生成的审稿记录
├── logs/                    # 编译和测试日志
└── status/                  # 审稿进度追踪
```

## 实验知识图谱（Experiment Map）

TianXing 会自动构建并维护 `experiment_map.json`，双向映射：

- **论文章节**（section、table、figure）↔ **代码文件**
- **代码文件** ↔ **测试命令**
- **代码文件** ↔ **结果文件**（数据、图表）

这意味着：review 发现某个表格结果不够 convincing → 顺着映射找到对应代码 → 改完代码知道跑哪个测试 → 也知道论文哪些段落需要同步更新。映射由扫描项目自动生成，每轮更新，也支持手动编辑。

```bash
tianxing map --action discover   # 扫描并生成
tianxing map --action query --id "tab:results"   # 查找关联代码/测试
tianxing map --action query --path "code/train.py"  # 查找关联测试/论文章节
```

## 工作原理

每一轮 Review 包含以下步骤：

1. **Checkpoint** — 给当前 git 状态打 tag，确保可回滚
2. **Experiment Map** — 发现或更新 论文↔代码↔测试↔结果 映射
3. **Review** — 从五个维度分析论文：清晰度、叙事逻辑、实验设计、AI 味、可读性
4. **Plan** — 按影响/风险比排序，生成优先级行动计划；通过映射找到所有受影响文件
5. **Modify** — 执行修改（低风险批量执行，高风险逐个处理）
6. **Validate** — 编译论文；通过映射只跑关联测试；失败则回滚
7. **Record** — 保存产物、更新分数、检查停止条件

### 停止条件

循环在以下任一条件满足时停止：
- 达到目标分数（`review.target_score`，默认 7.0）
- 超过最大轮数（`review.max_rounds`，默认 3）
- 分数连续无提升（`review.stop_on_plateau` 轮）
- 连续验证失败（`review.stop_on_fail` 次）

## 去 AI 味策略

这是本工具的核心差异化功能。系统内置 50+ 条 AI 写作反模式检测规则，包括：

| 类别 | 示例 |
|------|------|
| 空洞套话 | "It is worth noting that..." → 直接陈述事实 |
| 过度声称 | "groundbreaking" → 用具体数据说话 |
| 模糊量词 | "significantly" → 仅在有统计显著性时使用 |
| 机械过渡 | "Furthermore... Moreover..." → 变化句式 |
| 被动过度 | "It can be observed that" → "We observe" |

详细规则见 `prompts/rewriter.md`。

## 配置说明

完整配置见 `config.example.yaml`，关键设置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `review.venue` | **必填**：目标期刊/会议（如 `"NeurIPS 2026"`、`"IEEE TPAMI"`），reviewer 据此调整评审标准 | 空（未设置时循环不启动） |
| `project.env` | 实验运行环境：conda 环境名、conda 路径、或 venv 的 python 路径 | 当前环境 |
| `review.max_rounds` | 最大改进轮数 | 3 |
| `review.target_score` | 目标分数（达到即停） | 7.0 |
| `review.stop_on_plateau` | 连续 N 轮无提升则停 | 2 |
| `review.stop_on_fail` | 连续 N 次验证失败则停 | 2 |
| `compile.main_file` | LaTeX 主文件路径 | `paper/main.tex` |
| `compile.engine` | 编译引擎 | `latexmk` |
| `tests.enabled` | 启用测试（仅在有实验代码时需要开启） | `false` |
| `tests.command` | 测试命令 | `pytest` |
| `experiment_map.enabled` | 启用实验知识图谱 | `true` |
| `experiment_map.auto_update` | 每轮自动更新映射 | `true` |
| `git.auto_checkpoint` | 自动提交并打 tag | `true` |
| `notification.method` | 通知方式（V1 仅支持 file） | `file` |

## 安全机制

- 每轮修改前自动创建 git tag 检查点
- 编译或测试失败时，尝试修复一次，仍失败则自动回滚
- 修改按风险分级：低风险自动执行，高风险需确认
- 所有操作产物完整记录在 `reviews/` 和 `logs/` 中

## License

MIT
