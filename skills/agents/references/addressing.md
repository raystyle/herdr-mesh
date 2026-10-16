# 目标文法与全局寻址

> 蒸馏自契约一、五a、五d 节。目标 = 五命令共用的寻址面;解析唯一实现处在 primlib(契约边界)。v3 定形:id 单类型三分产生式,机不再占位置参数。

## id 三产生式

| 产生式 | 义 | 例 |
| --- | --- | --- |
| 无冒号 | 全局名:按 name 寻址,本机先,后在册机逐台查 | `tasks to web-agent-1 "收束后发版"` |
| `机:余段` | 显式跨机;首冒号前 = 机标签,余段整段 = 名或格(格 id 自带冒号不冲突,按首冒号切) | `agents read node-b:repo-claude-1` |
| `local:余段` | 本机显式形 | `agents keys local:w13:p1 Enter` |

- 裸 pane id 非法(契约文法):无冒号只按名查。 3.0.0a1 名字解析同时命中 pane_id,属实现偏离,勿依赖
- 机标签合法性 = 在册机表(`agents machines` 查)或 `local`;不在册报 not_found,CTA 指 `agents machines`
- 机标签 = herdr 机名(`hostname -s` 部署约定);`hostname -s` 因部署约定视为合法形

## 解析算法（primlib resolve）

1. 带冒号:机标签在册(或 local)则直取余段
2. 无冒号:本机 agent 表按 name 精确匹配
3. 未中:遍历在册机(enabled)逐台查
4. 全未中:not_found,CTA 指 `agents view`;**多名命中 = not_found**(信息注多名),契约规定不取先命中

## 命名标准（台名-agent类型-编号）

四概念:节点名(舰队注册名)、工作台名(= 项目仓库,创建时烙印目录名,1-22 字符,超长截断加短哈希)、窗格名(`<台>:<格>` 形,窗格操作寻址面)、agent 别名(格内 agent 注册名,消息收发路由键)。寻址双轨:消息 = 节点:别名或裸别名;窗格操作 = 节点:格。

- **标准形**:`^[a-z][a-z0-9-]{0,30}-(claude|codex|grok|kimi|pi)(-[0-9]{1,2})?$`,字母开头禁下划线,类型段小写,编号两位内;例 `myrepo-claude-1`、`myrepo-grok-1`、`docs-kimi-2`
- 三段义:台名 = 工作台别名(台以仓为单位建,即仓短名);agent 类型 = TUI 家族(claude/codex/grok/kimi/pi);编号 = 出生序号,该台该类型从 1 起不复用
- **出生序号非格位**:田字顺时针(TL-TR-BL-BR 序)只约束创建顺序与默认布局,满四开新 tab 续编;编号不等于当前格位
- **别名活注册**:退出/释放/替换即注销,同名可再授后来 agent;飞行中旧名解析 not_found,不另造永久 id
- **起名两闸**:`agents start` 拒新非标形(存量名兼容);起名全局扫全舰队,撞名拒;两闸皆 rc=2
- **起格必带名**:`agents start <名> --kind <类>`;无名格在裸名寻址里不可达,只能 `local:<格>` 或 `<机>:<格>` 显式形
- 名即身份:跨机递件、dm 流名、deferred 流名(shell 形)、presence 键都拿名字做键;改名 = 换身份;存量旧名可兼容在役,新起一律标准形
- 查名面:`agents view`(全局格表:HOST、NAME、PANE、STATUS、KIND、CWD)

## 隐式路由（各端一致）

- 调用方只给名字或 `host:pane`;local 与 `--machine` 由 primlib resolve 与 herdr 调用层自适,调用方零感知
- 同一文法在任何端点可用;远端解析走 `herdr --machine` 转发,零 ssh 零旁路
- 本机名取 `hostname -s`;与机册注册名不合时可 `PRIM_HOST_LABEL` 覆写(如 win 机)

## 回信地址与 from 核验（信封 v2）

- 投递方自动附 `from=<host_label>:<agent别名>`(session 直配本进程所在格;格未定才退化机名)加 `to=<收方 id>`;你在格里投的件,回信地址就指向你那格
- **from 是提示非签名**:收方回信前以 `agents view` 核对 host:alias 仍是活格;取用行是唯一协议面(见 deliver-gate.md 信封节)
- **取用行裸别名直答**:回信 = `agents to <别名> reply`;发话格无别名退化 `agents to <host:pane> reply`(正名走 herdr agent rename);格未定降级 `agents view, locate the sender pane on <host>, then agents to <host:alias> reply`
- **from 机器段 = host_label**:PRIM_HOST_LABEL 优先,linux/mac 机 hostname 即注册名;hostname 直落 from 属故障不是正常形
- **身份判定 session 直配**:CLAUDE_CODE_SESSION_ID 直配 herdr agent_session(同 cwd 双格歧义废),cwd 唯一命中兜底

## 坑簿

- 无名格别裸写:`to w8:p1` 首冒号先当机标签,报「机器 w8 不在册」;要打该格用 `local:w8:p1`
- 裸名先本机后远程:同名本机远程都有时,本机优先;要打远程格用 `机:名` 显式形
- 离线机不挂死(rc=124 容错,view 单行告警跳过);知道机仍写 `机:名` 一次命中,免逐台轮询
- 裸名跨机寻址依赖在册别名;端上别名与 hostname 不合时设 `PRIM_HOST_LABEL` 对齐
