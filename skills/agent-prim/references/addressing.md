# 目标文法与全局寻址

> 蒸馏自契约一、五a、五d 节。目标 = 五命令共用的寻址面;解析唯一实现处在 primlib(契约边界)。v3 定形:id 单类型三分产生式,机不再占位置参数。

## id 三产生式

| 产生式 | 义 | 例 |
| --- | --- | --- |
| 无冒号 | 全局名:按 name 寻址,本机先,后在册机逐台查 | `tasks to workbench-claude-1 "收束后发版"` |
| `机:余段` | 显式跨机;首冒号前 = 机标签,余段整段 = 名或格(格 id 自带冒号不冲突,按首冒号切) | `agents read host-a:w13:p1` |
| `local:余段` | 本机显式形 | `agents keys local:w8:p1 Enter` |

- 裸 pane id 非法(契约文法):无冒号只按名查。[实证] 3.0.0a1 名字解析同时命中 pane_id,属实现偏离,勿依赖
- 机标签合法性 = 在册机表(`agents machines` 查)或 `local`;不在册报 not_found,CTA 指 `agents machines` [实证:实测「机器不在册」]
- 机标签 = herdr 机名(`hostname -s` 部署约定);`hostname -s` 因部署约定视为合法形

## 解析算法（primlib resolve）

1. 带冒号:机标签在册(或 local)则直取余段
2. 无冒号:本机 agent 表按 name 精确匹配
3. 未中:遍历在册机(enabled)逐台查
4. 全未中:not_found,CTA 指 `agents view`;**多名命中 = not_found**(信息注多名),契约规定不取先命中

## 命名标准（用户令 2026-10-13:工作台-agent类型-编号,不乱取;已收编契约八）

- **标准形**:`<工作台标签>-<agent类型>-<编号>`,全小写 kebab;例 `workbench-claude-1`、`workbench-kimi-2`、`cloud-grok-1`
- 三段义:工作台标签 = 工作台别名,台以仓为单位建(`agents ws <标签>`,即仓短名,如 evo、hst、pi、s5);agent类型 = TUI 家族(claude/codex/grok/kimi);编号 = 工作台窗格位序号,名与格一一对应
- **窗格位与布局(用户令 2026-10-13)**:工作台默认至多四窗格,田字布局顺时针开(TL-TR-BR-BL 即 1 至 4);第五格起自动开新 tab(新格进新 tab),编号续增;名里的编号即格位(如 `workbench-claude-2` = evo 台 2 号格的 claude)
- 结构性全局唯一:一格一名,格位即编号,同台不撞;跨台台标签分域;裸名全局寻址下同名多格 = not_found,标准形从根上免撞
- **起名校验**:`agents start <名>` 非标准形 stderr 提示不拦截(正则 = 台标签-类型(-编号 可选),类型族 claude/codex/grok/kimi/pi,台标签字母数字下划线);存量名兼容 [实证:非标准名起格实测出提示,命名后照常流转]
- **起格必带名**:`agents start <名> --kind <类>`;无名格在裸名寻址里不可达,只能 `local:<格>` 或 `<机>:<格>` 显式形
- 名即身份:跨机递件、dm 流名、deferred 流名(shell 形)、presence 键都拿名字做键;改名 = 换身份;存量名(workbench-claude-1、workbench-claude)兼容在役,新起一律标准形
- 查名面:`agents view`(全局格表:HOST、NAME、PANE、STATUS、KIND、CWD)

## 隐式路由（各端一致）

- 调用方只给名字或 `机:格`;local 与 `--machine` 由 primlib resolve 与 herdr 调用层自适,调用方零感知
- 同一文法在任何端点可用;远端解析走 `herdr --machine` 转发,零 ssh 零旁路
- 本机名取 `hostname -s`;与机册注册名不合时可 `PRIM_HOST_LABEL` 覆写(如 win 机)

## 回信地址与 from 核验（信封 v2）

- 投递方自动附 `from=<host>:<pane>`(以 cwd 匹配本机格得出;匹配不中退化为仅 host)加 `to=<收方 id>`;你在格的仓目录里投的件,回信地址就指向你那格
- **from 是提示非签名**:收方回信前以 `agents view` 核对 host:pane 仍是活格;取用行是唯一协议面(见 deliver-gate.md 信封节)
- **在格 cwd 里投递**:cwd 无格匹配时 caller_addr 退化 host-only 并 stderr 告警 [实证:/tmp 直调实测],取用行自动降级指 `agents view` 定位再 `agents to <机:格>`;判例 = from=HOSTNAME 的降级形 `取用:agents view(定位 HOSTNAME 上发话格后 agents to <机:格> <回复>)`;在格 cwd 里投递即回直答形
- **from 的 host 是 hostname 非在册机标签**:同机回信按名或 `local:<格>`;hostname 与本册标签不合时 from 形同册不可解析(判例:本机 hostname host-b 对在册标签 local,`agents to host-b:w8:p1` 同机 not_found,workbench-grok-4 按名回信成) [实证:批 143 实弹]
- **同 cwd 多格歧义不猜**(ef8fca6 修):caller_addr 多命中时退化机名并告警,不取首格(批判例:w8:p1 与 w8:p4 同仓,旧形误指) [实证:批 147 自探针回环,告警与退化取用行双落地]

## 坑簿

- 无名格别裸写:`to w8:p1` 首冒号先当机标签,报「机器 w8 不在册」;要打该格用 `local:w8:p1` [实证]
- 裸名先本机后远程:同名本机远程都有时,本机优先;要打远程格用 `机:名` 显式形
- 离线机不挂死(rc=124 容错,view 单行告警跳过);知道机仍写 `机:名` 一次命中,免逐台轮询
- `hostname -s` 与 herdr 机标签不一致的机,裸名跨机查不到;用 `机:名` 并报总台对齐(判例:win 机裸 hostname HOSTNAME 对在册名 host-a,已配 PRIM_HOST_LABEL=host-a,旧进程未续属一次性,新会话起生效)
