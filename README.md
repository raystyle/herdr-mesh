# herdr-mesh

多端点 agent 网格互操作体系:六原语命令、消息契约、操作技能。

多个端点上运行多个编码 agent(herdr 窗格为执行单元),六条命令将消息、文件、流、管道、持久任务、对话历史检索统一为一套全局协议。任意端点共享同一命令文法,跨机操作不依赖 ssh。

## 架构总览

```
端点(局域网物理节点 + 云 VPS 节点)
  herdr server(窗格物理层: workspace > tab > pane)
    pane 内运行 CLI agent(claude / codex / grok / kimi)
      agent 经五原语互操作
        agents  消息域: 窗格检索 / 屏幕读取 / 提示词投递 / 工位管理 / 会话重载
        shares  文件域: S3 语义中转(内容哈希键)
        streams 流域:  S2 语义持久流(流即房间,回执主频道)
        tasks   持久任务域: hst task 远程控制
        pipes   实时字节域: tailcat 管道(本机接收,对端发送)
        ctx     历史检索域: ClickHouse gw_logs 对话历史(view/show/search)
          引擎层: herdr(窗格) + s5(对象与流) + hst(任务) + tailcat(管道) + clickhouse(历史检索)
          协议层: 五命令 + pydantic 消息契约(本仓 src/)
```

核心设计:

- 隐式路由: 调用方提供 agent 名或 机:格 标识,本机与跨机路由由命令内部自适应,同一文法适用于任意端点
- 原子化投递: 投递动词统一为 to;写入不等于执行(--wait 等待目标进入 working 状态);status 四态信封返回结果
- 门控 v2: 读取目标 TUI 尾窗实况检测操作对话框(信任确认/权限确认);对话框存在时拒绝投递,空闲终端可投递,working 状态消息排队不拦截
- 拒投代记: 被拒绝的投递意图自动记录至 room/deferred/<格> 流,消息不丢失
- 消息信封 v2: 三行格式(摘要行含 @收方 / 字段行含 from、to、域字段、v / 取用行),机器可解析
- 全局 id 三产生式: 裸名全局寻址 / 机:名或格 / local:格

## 目录

- CONTRACT.md: 五原语命令契约(动词表/输出契约/错误码/信封/布局/命名标准),单一真源
- src/: prim v3 源码(uv python CLI,六命令入口)
- skills/agent-prim/: agent 操作技能(意图路由 + 反射规则 + 已知问题表)
- docs/: 架构文档

## 安装

```
uv tool install --force git+https://github.com/raystyle/herdr-mesh#subdirectory=src
```

六命令(agents shares streams tasks pipes ctx)进入 PATH;ctx 连接经 CTX_HOST/CTX_CONTAINER 环境变量配存储节点。各命令 --llms 输出手册。

## 技能安装

skills/agent-prim 复制到 agent 技能目录(Claude Code 为 ~/.claude/skills/ 或经插件市场)。

## 演进

契约升版本以本仓 CONTRACT.md 为准,src 与 skills 同批次对齐;实装差异与已知问题见 skills/agent-prim/references/commands.md。
