# 双端执行面:Claude Code 与 Codex 项目级

> 标准 skill 的家在项目仓(唯一权威源),两端各按项目级面加载;验证轮用私有配置目录隔离,transcript 先过滤再当证据。命令面活权威是本机实查,不照抄外部文档句子。

## 项目级加载

- **Claude Code**:项目级技能目录 `.claude/skills/<名>/SKILL.md`,随仓走、团队共享;标准集以它为挂接面;仓内 `.claude/` 整体 ignore 的存量仓,先以忽略登记划界(仅放行 `.claude/skills/`)再挂接
- **Codex**:项目 `.codex-plugin/plugin.json` 的 `skills: ./skills/` 挂接项目技能目录(本插件仓即此形态),或经 `$CODEX_HOME/skills` 符号链接用户级挂接;项目仓持有唯一权威源,符号链接只是视图
- 两端同读一份标准 SKILL.md(agentskills 官方 spec 形态),不分发第二份;frontmatter 只留官方字段,双端才都认

## 验证轮隔离

- 隔离的意义:闸门只对「候选标准集」评分,agent 必须恰好看见候选集,不能带上用户主目录技能与记忆
- Claude Code:工作区私有 `CLAUDE_CONFIG_DIR`;Codex:工作区私有 `CODEX_HOME`(凭据按需引导副本)
- **凭据副本不进项目 git**:工作区私有配置目录整体 gitignore;隔离防的是技能集泄漏,不是秘密泄漏,别写成「无秘密」
- **每回合按当前技能集重建链接**:清空私有技能目录的旧链接再链候选集;执行回合不带框架角色技能(蒸馏者、提案者的技能只在蒸馏提案回合链入)

## transcript 资格过滤

- 回合收束先归一 transcript,首行记 `backend`、`tool_call_count`、`message_count`
- 零工具调用回合:不进蒸馏样本、不进分数分母(它多半是启动失败或被吞单,不是行为证据)
- 空 stdout 时删掉旧 session 文件,防上一回合的陈旧转录被当成这一回合

## 无头模式与审批档位(生成维护 SKILL 的环默认形态)

- **三档**:有人值守(问询审批形,越界弹问)、无头边界内(沙箱加自动审或越界即失败,不弹屏)、全开 yolo(绕沙箱绕审批)
- **四端无头边界内推荐形**(蒸馏、提案、验证轮):

```text
claude -p "<提示词>" --output-format stream-json --permission-mode auto --permission-prompts none
codex exec "<提示词>" -s workspace-write --approve-for-me --json
grok -p "<提示词>" --output-format streaming-json --permission-mode auto --sandbox workspace
kimi: 无对等档,见下
```

- kimi 无沙箱:`-p` 固定走不再询问档且危险命令拦截在该档关闭,用 `kimi -p` 只能按全开处置(仅外部隔离工作区);可用 `--skills-dir <候选集目录>` 收窄技能面、`KIMI_CODE_HOME` 换配置目录,但都不是沙箱 [实证: 2026-10-10 四端 --help 与官方参考实查,claude 2.1.270、codex-cli 0.154.0、grok 1.0.13、kimi 2.1.1]
- 旗标陷阱:grok 全开写 `--always-approve`(help 可见;`--yolo` 是文档别名不写进命令);kimi 的 `-y/--yolo` 是更严档不是全开,交互全开是 `--auto`,且 `-p` 不能叠加审批旗标;claude 边界内关键半句是 `--permission-prompts none`(会弹窗的调用自动拒绝);codex `--approve-for-me` 绑定 workspace-write 沙箱语义
- **环的分工**:蒸馏与提案回合、验证轮默认无头边界内跑;全开 yolo 仅限外部隔离环境(独立工作区、无生产凭据与数据;git 分支不构成隔离)
- 接受与发布恒停在人裁(与 gate.md 发布纪律同源),无头只覆盖生成与验证,不覆盖发布

## 命令面(活权威实查)

- 活权威 = 本机 `claude --help` 与 `codex exec --help`;写进脚本或文档前先实查干跑,禁止让任何外部 README 的句子当唯一规范 [实证: 2026-10-10 本机双端 --help 实查(codex-cli 0.154.0),下列参数在位]
- Claude Code 非交互回合:`claude -p --output-format stream-json --verbose --model <模型> --permission-mode <模式> --allowedTools <工具表>`(回合上限类参数以当次 help 实查为准,不预设);全开形 `--dangerously-skip-permissions` 仅外部隔离环境用
- Codex 非交互回合:`codex exec "<提示词>" -s <沙箱模式> --approve-for-me --skip-git-repo-check --json`(沙箱与审批旗标形态随版本演进,以当次 exec help 实查为准,不写死旧形态);全开形 `--dangerously-bypass-approvals-and-sandbox` 仅外部隔离环境用;配置覆盖用 `-c <键=值>`,分层配置用 `--profile`
- 参数面随版本漂移:每轮跑环前重查一次 help,漂移即先改命令再跑
