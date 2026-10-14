# herdr-mesh

跨端点 agent 网格的互操作体系:五原语命令 + 消息契约 + 操作技能。

多机多端点上运行多个编码 agent(herdr 窗格为物理单元),五条命令把消息/文件/流/管道/持久任务统一成一套全局协议。任何端点同一文法,零 ssh。

## 架构总览

```
端点(win / linux / mac / pi)
  herdr server(窗格物理层: workspace > tab > pane)
    pane 内跑 CLI agent(claude / codex / grok / kimi / pi)
      agent 经五原语互操作
        agents  消息域: 找格 / 读屏 / 派单 / 工位管理 / 翻台
        shares  文件域: S3 形中转(内容哈希键)
        streams 流域:  S2 形持久流(流即房间, 回执主频道)
        tasks   持久任务域: hst task 全局遥控
        pipes   实时字节域: tailcat 管道(本机收对方发)
          引擎层: herdr(窗格) + s5(对象与流) + hst(任务) + tailcat(管道)
          协议层: 五命令 + pydantic 消息契约(本仓 src/)
```

核心设计:

- 隐式路由: 调用方只给 agent 名或 机:格,本地与跨机由命令内部自适,同一文法任何端点可用
- 原子化投递: 投递动词统一 to,写入不等于执行(--wait 到目标开吃),status 四态信封回执
- 门控 v2: 读目标 TUI 尾窗实况判操作对话框(信任屏/权限屏),对话框拒投,空屏可投,busy 排队不拦
- 拒投代记: 意图自动落 room/deferred/<格> 流,人不丢件
- 消息信封 v2: 三行形(人话行 @收方 / 字段行 from to 域字段 v / 取用行),机器可解析
- 全局 id 三产生式: 裸名全局寻址 / 机:名或格 / local:格

## 目录

- CONTRACT.md: 五原语命令契约(动词表/输出契约/错误码/信封/布局/命名标准),单一真源
- src/: prim v3 源码(uv python CLI,五命令入口,pyproject 同装)
- skills/agent-prim/: agent 操作技能(Claude Code 技能面,意图路由 + 反射 + 坑表)
- docs/: 架构文档

## 安装

```
uv tool install --force git+https://github.com/raystyle/herdr-mesh#subdirectory=src
```

五命令(agents shares streams tasks pipes)进 PATH。各命令 --llms 出手册。

## 技能安装

skills/agent-prim 复制到 agent 技能目录(Claude Code 面为 ~/.claude/skills/ 或经插件市场)。

## 演进

契约升版以本仓 CONTRACT.md 为准,src 与 skills 随批对齐;差异与坑见 skills/agent-prim/references/commands.md。
