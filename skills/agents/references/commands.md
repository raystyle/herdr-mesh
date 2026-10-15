# agents 域文法与六原语共享输出契约

> 蒸馏自契约二、三、四、五d 节(真源 ai-ccoe plugins/CONTRACT.md);标注 的行为以本机 wrapper 实读为准(以 `--llms` 实查为准)。通则、错误码表、六域速查与差异表为六原语共享面,六 skill 共参本篇(ctx 域 = 对话历史检索,read 实时屏对 ctx 历史档案)。

## 通则（文法与输出契约）

- **文法模板**:`<命令> [全局旗标] <动词> [动词旗标] [位置参数...]`;全局七旗标(`--help -h --llms --json --format --full-output --filter-output --schema`)任意槽;`--format` 与 `--filter-output` 带值;`--` 逃生口;未知词 usage 退 2 禁静默 shift
- **两形同源**:`--json` 出机器形(DELIVER 出单行信封 `{"ok":true,"data":{...},"meta":{"command":"<名>"}}`,data 恒带 status 四态);缺省人读形;两形字段序一致
- **错误分道**:错误一律 stderr;`--json` 时 stderr 单行 `{"code":"...","message":"...","cta":[{"command":"...","description":"..."}]}`;stdout 永纯数据
- **CTA 专业标准**:错误必带下一步,统一『下一步:』前缀与 target= 键值形,俚语清零(『开吃/候/强投』不再出);例 `目标存在操作对话框,已拒投并代记;下一步:--force 跳过门控重发`
- **退出码**:0 成功;1 业务未命中(目标无、拒投、键不存在);2 用法错;禁其他码。拒投时 stdout 仍出 ok:true 信封 + exit 1,判定看退出码与 data.status 勿单信 ok
- **裸调用**:无参 = VIEW,exit 0,不进交互(agent 可放心探测)

## 错误码表

| code | 义 | cta |
| --- | --- | --- |
| not_found | 目标名或机器全局未命中(同名多格也走此码,信息注多名) | agents view 查名 / agents machines 列机 |
| gate_refused | 目标格有操作对话框(门控 v2:TUI 实况判标) | --force 重发 / 消息改走 OPERATE 记流 |
| engine_fail | s5/hst/tailcat/herdr 引擎失败(原文透传不吞不裁) | 看引擎输出(data 带 engine_error) |
| usage | 参数形不合法或未知词 | --llms 看手册 |

## 五域速查表（v3 动词面）

| 命令 | VIEW | OPERATE | DELIVER |
| --- | --- | --- | --- |
| agents | `view [机]`;`machines`;`list [机]` | `read <id> [--lines N] [--timeout S]`(收件面);`keys <id> <键>`;`mode <dnd|away|online> [until]`;`start <名> --kind <类>`;`ws <label>`/`ws list`/`ws close`;`shell <机> <仓>`;`dev <机> <仓> [--kind]`;`split <id> [--direction]`;`tab list/create/close`;`zoom <id>`;`trust`;`sync` | `to <id> <文本> [--force]`(prompt = 别名) |
| shares | `view`(share/ 键表) | `put <文件>`;`get <键> [-o|--output 名]` | `to <id> <文件> [--force]` |
| streams | `rooms`;`room <房名>`(读房);`view [流名] [--from <seq>\|--resume] [-n N] [-f]` | `room <房名> <消息>`;`dm <别名> <消息>`(均可 `--file <文件> [--lines N:M]`);`append <流> <消息>` | `to <id> <流> <消息> [--force]` |
| tasks | `view [机]`(实时任务面:fleet 总览加本机 hst 直读,远机经 agents read;收方取用行 = `tasks view`) | `set <id> <文本>` | `to <id> <文本> [--force]`(= set 加知会) |
| pipes | `view [机]` | `open [--keep]`;`close <addr|pid>` | `to <id> [--force]` |
| ctx | `view [agent] [--limit N]` |  | `show <request_id> [--around <词>] [--window N]`;`search <词> [--term <词>]...`(历史检索,非投递) |

## agents（消息域）

- **收件面(隐式等待)**:`agents read <id> [--lines N] [--timeout S]`(默认 20 行、90 秒);目标 working 则内候(5s 轮询)到闲/完成或超时;status 随信封出(闲 = idle/done,超时未闲 = timeout-working,内容仍全量附上,exit 0);无内容才 engine_fail 加 CTA `--timeout 加长重试`
- 读屏即收件:等队友回话就用 read,勿手写轮询
- 全局面:`agents view` 跨全部在册机出格表(HOST、NAME、PANE、STATUS、KIND、CWD);`agents machines` 出机表与可达性
- 投递:`agents to <id> <文本>` 过门控 v2 投信封 v2 定稿四行形;成功面 `已投递,目标已开始处理(target=…)`,拒投自动代记 room/deferred(含原文截 80 字)并 stderr `下一步:--force 跳过门控重发`
- 工位管理:`agents start <名> --kind <类>` 起格(非标准名 stderr 提示不拦截,标准形见 addressing.md 命名标准)、`ws`/`shell <机> <仓>`/`dev <机> <仓>` 开台起 agent、`split`/`tab`/`zoom` 布局、`trust` 信任屏放行、`sync` 机册面;tab id 解析 = `机:tabid`
- 在场声明:`agents mode <dnd|away|online> [until]`(自声明,写 shares 键 `share/presence/<host>/<格>` 覆盖,正文 mode 与 until;勿扰与离开建议短窗,过期自动回落)
- 按键:`agents keys <id> <键>`;跨机 = usage 拒,CTA 指本机 keys 或 mesh trust(契约面)

## 本机实装差异表（契约面 vs 本机实装）



| 契约面 | 本机实装 |
| --- | --- |
| VIEW 与 OPERATE 的 --json 两形 | 未落(--json 仅 DELIVER 信封与错误 stderr 生效) |
| tasks view 转实时任务面本机实查 | 本机 hst 直读加 fleet 总览,远机经 agents read 看屏;机过滤在位,id 带参未收;tasks/shared 事件流已弃 |
| --force 审计 room/force-audit | 未落(五域皆无;强投前自问必要性) |
| 幂等 id | 未落(v=1 已随信封 v2 落,from/to 恒在;tasks 事件 prev 随事件流弃用销账) |
| 拒投代记流键 = 收方名 | 用目标格 pane id;shell 形旧流按名仍在,补收两边都看 |
| presence 声明键 = share/presence/<机>/<名>(五a) | 实装用 <机>/<格> pane 形 |
| streams 拒投代记含原文 | 只记意图行(流名加待递),不含消息体;须 --force 重发或改走 append |
| 裸 pane id = usage | 偏离:名字解析同时命中 pane_id,勿依赖此偏离 |
| --help = 手册加节序展开 | --help 与 --llms 同面(无节序展开) |
| layout 动词(契约八节) | 挂账:herdr 0.9.3 无 layout 子命令(preview 面,候 herdr 后续版) |
| from=<host> 可直接回投 | 已落(双轨制):`from=<host_label>:<别名>`,取用行裸别名直答;身份 session 直配,cwd 唯一命中兜底 |
| 房间抽象与流式面(rooms/room/dm、`-f`、stdin、`--file`) | 已落;`--file` = 文件整档上架 shares 键,消息带键引用与行区间 |
| 信封取用行 | 消息三域(agents/shares/streams)已裸别名;tasks 仍 `tasks view`、pipes 仍 `tailcat <addr>` |
| 手册 close 语义 = 代码零击杀 | 漂移:手册仍书「分裂格杀 shell」,码已是 /exit 优雅退加 shell exit 零击杀(报总台) |

- 用前实查:`command -v agents` 等五命令在不在、`<命令> --llms` 看手册面;差异面如实报,不猜不代装(分发归宿主工具链 omc 与 ark)
