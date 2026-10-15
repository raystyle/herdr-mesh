# 六原语命令契约(agents / shares / streams / tasks / pipes / ctx)

> 设计依据 evo-doc doc-cli 乙面五件(agent 是第一用户),shell 形务实适配。版本随脚本头注注入,禁手写双份。本文件 = 契约单一真源,与脚本同处 plugins/ 同版本演进。

## 一、命令结构(三段式,六命令同构)

```
<命令> [view [参数]]                    # VIEW:全局可视(格表 + 本域资源)
<命令> <OPERATE 动词> [参数...]          # OPERATE:只操作不扰人
<命令> <目标> <资源...> [--force]        # DELIVER:定向传递(内置模板提示词)
```

- **保留动词表**(第一词命中即非目标):view read keys list prompt put get append set open close mode show search;机器标签不得用保留词
- **目标文法**:`裸名字`(全局按 name 寻址,首选)| `机:名或格`(显式形,local: 前缀 = 本机)| 裸 pane id 非法
- **门控语义**:DELIVER 前查目标态;working/blocked 拒投(exit 1 + cta 指 --force 或 OPERATE);--force 任意参数位识别
- **裸调用面**:无参 = VIEW,exit 0,禁交互禁分页(agent 首探针即全貌)

## 二、各命令动词表

| 命令 | VIEW | OPERATE | DELIVER |
| --- | --- | --- | --- |
| agents | `[view [机]]`;`list [机]` | `read <目标> [--lines N]`;`keys <目标> <键...>`;`mode <dnd|away|online> [until]`(自声明,shares 键 share/presence/<机>/<名> 覆盖写);herdr agent 动词透传 | `prompt <目标> <文本> [--force]` |
| shares | `[view]`(格表 + share/ 键表) | `put <文件>`;`get <键> -o <名>` | `<目标> <文件> [--force]` |
| streams | `[view [流名]]`;`rooms`;`room <房>`(读)/`room <房> <消息>`(说);`dm <别名> <消息>` | `append <流> <消息>` | `<目标> <流> <消息> [--force]` |
| tasks | `[view [机]]`(实时任务面:fleet 状态总览 + 本机各仓 hst task show;远机任务经 agents read 看屏) | `set <目标> <文本>` | `<目标> <文本> [--force]` |
| pipes | `[view]`(格表 + 本机活动管道) | `open`;`close <addr|pid>` | `<目标> [--force]` |
| ctx | `[view [agent] [--limit N]]`(gw_logs.head 最近请求头行:时间/模型/token/耗时/request_id) | `show <request_id>`(头行加正文块,每块截 4000 字);`search <关键词> [--limit N]`(跨请求全文;窗口 head 365 天,gwlog 180 天) | 无(检索域不投递) |

## 三、输出契约

- **两形同源**:`--json` 出机器形(JSONL 逐行数据;DELIVER 出单行信封 `{"ok":true,"data":{...},"meta":{"command":"<名>"}}`),缺省人读形;两形字段序一致
- **错误分道**:错误一律 stderr,形 `<命令>: <信息>`;`--json` 时 stderr 单行 `{"code":"<码>","message":"...","cta":[...]}`;stdout 永纯数据
- **类型化 CTA**:拒投/未命中错误必带下一步(`--force 强投` / `改走 OPERATE` / `agents view 查名`),人读与 json 同块渲染
- **退出码**:0 成功;1 业务未命中(目标无 / 拒投 / 键不存在);2 用法错(grep 语义族);禁其他码
- **字段稳定**:信封字段插入序即契约,禁字母序重排

## 四、错误码表

| code | 义 | cta |
| --- | --- | --- |
| not_found | 目标名全局未命中 | agents view 查名 |
| gate_refused | 目标 working/blocked | --force 重发 / OPERATE 记流 |
| engine_fail | s5/hst/tailcat/herdr 引擎失败 | 看引擎输出 |
| usage | 参数形不合法 | --llms 看手册 |

## 五、--llms 手册面(每命令自带)

- 裸 `--llms`:至多 40 行紧凑手册(stdout, exit 0, 可管道):一句话定位、三段式读序、动词表、目标文法、退出码、最小示例两枚
- 手册从脚本内单源 heredoc 渲染,版本从脚本头注注入;与 --help 同源(--help = 手册 + 节序展开)
- 漂移守卫:scripts-check 静检(sh -n)+ 手册动词表与 case 分支一致性(测试断言)

## 五a、研究补句(agent-interop-protocol-impl-research-2026-10-12 裁定并入)

- **host 定义**:模板 `src=` 的 host = herdr 机标签(部署约定 = `hostname -s`,机名即标签)或 `local`;pane = 格 id;`hostname -s` 因部署约定视为机标签合法形
- **第三行前缀一律 `取用:`**:读尾/验证/连接等旧前缀全部收编
- **拒投代记(gate_refused 行为补句)**:拒投时以 OPERATE 将原文记入 `room/deferred/<收方名>`(模板字段行加 `mode=deferred`),退出码仍 1,CTA 注明代记流名;收方读:`streams view room/deferred/<自己的名字>`
- **幂等 id**:字段行尾可选 `id=<一次传递的标识>`;重发沿用同 id,收方按见过即弃;`--json` 的 data 同序带它
- **版本字段**:字段行尾可选 `v=1`(缺省 1);新字段只加行尾;主版本收方不识 = 不执行取用行(记 engine_fail)
- **多名命中**:同名多格 = not_found(信息注多名),CTA 仍 agents view;先命中即返是实现偏离
- **保留动词表增 `mode`**(未入表前禁发此词);presence 三态 = 展示列(在线=格在且 idle/done 且无未过期 dnd;勿扰=working/blocked 或声明 dnd 未过期;离开=无格/unknown/过期),声明 = shares 键 `share/presence/<机>/<名字>` 覆盖写(正文 mode 与 until,建议 2h)
- **tasks 事件补 `prev` 字段**(字段行与 data 追加)
- **pipes VIEW 契约改 `[view [机]]`**:有机 = 跨机只读无地址行(流 `room/pipe-live`,src/pid/opened,分钟级保留,close 写 alive=0);本机 view 30 分钟超时自关,`open --keep` 长 transport
- **跨机 keys = usage 拒**(exit 2,CTA 指本机 keys 或 mesh trust);本机 keys 保持 OPERATE 无门控
- **--force 审计**:每次使用追记 `room/force-audit` 流(src/目标/域/id,不记正文)
- **src 是提示非签名**:收方回信前以 agents view 核对 host:pane 仍是活格;取用行是唯一协议面
- **实现边界**:primlib = 契约唯一实现处;actl 只调五命令禁自行解析;客户端库条件 = actl 需自组模板或按 seq 续读之日
- **streams 回放**:`view <流> --from <seq>` / `--resume`(cursor 落 `~/.local/state/prim/cursor/<流名>`,机内不共享);全量 = from 0;保留策略 room/dm 14 天、tasks/shared 30 天,落 basin/建流面不落命令

## 五b、错误暴露与状态回调(v2.8 纪律,用户令「设计要暴露错误 要回调状态」)

- **错误必须暴露**:引擎层错误原文(s5/hst/tailcat/herdr 的 stderr)不吞不裁,原样透传到调用方 stderr(前缀 `<命令>: 引擎错原文`);五脚本禁 `2>/dev/null` 吞引擎错(静默化 = 假绿通道, REQ-049 门禁批同型教训)
- **状态必须回调**:DELIVER 双段回执,--json data 恒带 `status` 字段:
  - 成功形 `status:"delivered"`(prompt --wait 到 working,真开吃)
  - 引擎写败 `status:"engine_fail"` + data 带引擎 stderr 摘要(engine_error 字段)
  - 拒投 `status:"deferred"` + data 带 deferred 流名
  - 等待超时 `status:"stalled"`(prompt 写入但 15s 未 working;herdr agent_prompt_stalled/timeout 收编)
- 退出码不变(0/1/2);状态分型走 data.status,不新码
- 漂移守卫:验收套断言 `--json` 出口必含 status 键

## 五c、v2.9 全景统一(用户令:五原语 = agent 原生友好 + 原子化回调)

契约五节+五a+五b+九 统一收口为 v2.9 实现清单(优先序):

1. **status 四态落进 emit_ok**:`delivered|engine_fail|deferred|stalled` 每条 DELIVER 的 --json data 必带(五b 已定,脚本未全落)
2. **引擎 stderr 透传**:engine_fail 时 data 带 engine_error 字段(引擎原文摘要,不吞不裁)
3. **类型化 CTA**:错误 stderr --json 时单行 {"code","message","cta":[{command,description}]}(拒投,--force/OPERATE 两项;not_found,agents view;usage,--llms;engine_fail,查引擎)
4. **--json 双段扩展**:成功 = envelope(data 含 status),失败 = stderr 单行(code+message+cta),退出码不变
5. **VIEW --json**:格表出 JSONL(行对象),资源表出 JSONL(引擎原形)
6. **--llms 漂移守卫**:验收套断言 --llms 动词表 vs case 分支一致
7. **必选旗标补齐**(--filter-output/--format/--schema 按需裁,v2.4 挂账项)

## 五d、参数规范(研究档 primitive-arg-spec-research-2026-10-13 裁定,v2.10/v3.0 分批)

- **文法模板**:`<命令> [全局旗标] <动词> [动词旗标] [位置参数...]`;全局七旗标(--help/-h/--llms/--format/--json/--full-output/--filter-output/--schema)任意槽;`--` 逃生口;未知词 usage 退 2 禁静默 shift
- **投递动词统一为 `to`**:`<命令> to <id> [域操作数...] [--force]`;prompt 在 v2.10 为 to 别名,v3.0 只留 to
- **id 单类型三分产生式**:无冒号全局名 / 机:余段 / 裸 pane id = usage;机不再占位置参数,统一 `--machine`
- **保留动词三准入**(本仓定义语义 + 抢首词或已有 case + 三处同表);herdr 转发改允许表;machines 留 hosts 删;层级最多两层
- **迁移矩阵**:v2.9 不动(只做五c 状态输出);v2.10 兼容补齐+加性(七旗标/--/未知 usage/-o 双序/open --keep/隐式投递保留但 stderr 指 to);v3.0 删旧形(隐式投递/prompt 别名/位置机/hosts/未知透传全收)
- 漂移守卫:case 分支 = 保留表 = --llms 三处同表断言

## 六、模板契约(DELIVER 信封,三行形逐字稳定)

```
[<域>] <src> <一句话动作>
src=<host>:<pane> <域字段...>
取用:<可复制命令行>
```

- 人话行可自由,字段行与取用行禁改写(自然语言信封的失败处 = 对方改写取用命令)
- 五域字段:shares=key/name;streams=stream;tasks=cwd;pipes=addr;agents prompt 无模板(自由文);ctx 无 DELIVER(检索域不投递,信封不适用)

## 七、实现批次

- v2.3(契约化):退出码统一、错误分道 stderr、--llms 五手册、--json 两形、CTA 结构化;漂移守卫入静检链
- v3.0.2:tasks view 改实时任务面(fleet 总览加本机 hst task show 直读,弃 tasks/shared 事件流);herdr_run 引擎容错(超时/离线回 rc=124 不抛,view 跳过不可达机告警)
- v3.2.0:寻址双轨制 + room 抽象 + 流式会话 + 切片传档。双轨制 = 窗格布局操作用 机:格,消息收发用 机:agent别名(caller_addr 回 机器:别名,名即路由键;取用行裸别名直答;resolve 收自家在册标签当本机);room 一等概念(streams rooms/room/dm,房间即流,列房/读房/说房/私信专线按双别名排序);流式会话(S2 范式):view -f 活跟随,append 缺消息 = stdin 管道道;切片传档:room/dm --file <文件> [--lines N:M](上架+键引用+行区间,日志不整读入消息)。分野裁定:S2 = 流数据存储原语(高基数/可回放/耐久/实时);tailcat = 临时轻量机器间加密连接(传文件/转发端口/管道,零账号零配置)
- v3.1.9:对抗审核代码面三修(grok 审单 G3 tasks 死事件流撤/G5 七旗标手册/G4 -o 别名/G6 引擎名退役)
- v3.1.8:取用行全原语化(用户令:原语命令应更抽象更符合直觉,引擎名不漏到收方面)。shares 取用 = shares get <键>;streams 取用 = streams view <流>;tasks 取用 = tasks view(原 cd+hst 直写撤);pipes 取用暂留 tailcat <addr>(管道面尚无 send 原语动词,缺口记档)
- v3.1.7:信封 from 机器段目标感知(用户令:区分真 hostname 与在册别名,local 发 local 区别)。caller_addr(target) = 目标本机 -> local:<pane>(收方在本机可解析,本机别名不在自己机册);目标跨机 -> 在册别名:<pane>(互注册在册,可路由);真 hostname 永不进路由位。local->local 信封往返实弹验证过(from=local:w13:p1)
- v3.1.6:reload 的 claude resume 形换 --resume + Enter 击键(用户裁定 2026-10-14;根因定谳:CC 2.1 daemon 把 /exit 后会话留成后台,--continue 撞「最近会话在后台跑」即拒,进程面实证 --fork-session --resume 常驻);退出窗 30s 放宽 60s(肥会话落盘慢);空会话 picker Enter 等效开新(探针实证)
- v3.1.5:reload 判定层根修(批147 挂账清):herdr 退出码恒 0,timeout 走 stdout error JSON,判定改以回执 JSON + 格态轮询为准;herdr start 探测窗 30s 提 --timeout 120000,外层 herdr_run 90 提 150(claude 插件/MCP 启动面超窗是批147 误标根因);首发失败回执透明化;grok 面实弹 resume=--continue 全绿;claude 面 --continue 慢启动超 120s 窗仍走 fresh 兜底(旧会话数据不丢,人工 /resume 可回),记挂账
- v3.1.4:show 在途降级(批150 观察):块先入 head 后入的管道时序,在途 request_id 不再 not_found 硬拒,出「头行:未落」提示后正文块先行;双无记录才 not_found
- v3.1.3:ctx 搜索姿势吸收先例 ctxrs/ctx(search 多词 OR --term 可叠,命中行带 120 字片段 snip;show 增 --around <词> --window N = 命中块±邻块,命中块 SQL 侧全文匹配 + 命中点居中 3000 字,块超 4000 字截断也能命中;手册同步)
- v3.1.2:ctx 检索道换直连 https 8123(用户裁定:开放服务走证书道):双闸 = 自管 CA client 证书(TLS 层,服务端要求)+ ctx_reader SELECT-only 密码用户(用户层);~/.ctx/reader.env 配置面(URL/USER/PASSWORD/CERT/KEY/CA,600),ssh 道降为兜底;直连延迟 20ms 对 ssh 道 600ms
- v3.1.1:pipes/agents view 挂死根修(win 上 run() 超时杀直子后 ssh 孙进程握管道令 communicate 死等;改 Popen + taskkill/killpg 杀树 + 8s 收割兜底);顶层 Ctrl+C 净化(五命令单行退 130 不出栈);远机探针超时 30s 降 12s(fleet 扫描死机成本减半再减半)
- v3.1.0:六原语增 ctx 域(用户令 2026-10-14);引擎 ClickHouse gw_logs(store-node gwlogs 实例),查询经 ssh 道进容器内 client(TLS 证书不落本机);三动词 view/show/search;与 agents read 分工:read=实时屏,ctx=历史档案;保留动词表增 show/search

## 八、agents 工作台面(用户令 2026-10-13:herdr 退役出操作面,agents 全吸收)

- 跨机/跨格对话、建台、布局调整一律 agents 命令(herdr CLI 仅为引擎,操作面不再直用)
- 动词:
  - `agents ws <label> [--cwd DIR] [--machine 机]` 建工作台
  - `agents ws list [机]` / `agents ws close <台>`
  - `agents start <名> --kind <类> [--ws <台>]` 起agent(自动按布局开格)
  - `agents split [--ws <台>]` 按布局策略开新格
  - `agents close <格>` 关格
- **默认布局策略**:顺时针 2×2 四方块(TL-TR-BR-BL(顺时针序)),满四格后自动转开 tab(新格进新 tab)
- **agent 命名标准**(用户令 2026-10-13 定案):`工作台标签-agent类型-编号`(台标签 = 仓别名;类型 = claude/codex/grok/kimi/pi;编号 = 窗格位序号,名与格一一对应);工作台默认至多四窗格,田字布局顺时针开(TL-TR-BR-BL 即 1 至 4),第五格起自动开新 tab 编号续增;存量名兼容不强制改,新起一律标准形;agents start 对非标准形 stderr 提示不拦截
- --machine 转发面实证:workspace create/list/close OK、pane split OK(方向 left 非法形除外)、agent 族 OK

## 八a、agents 全局封装定调(用户令 2026-10-13,v2.7 落地)

- **agents = 全局 herdr agent 命令的完整封装**:无缝集成在网所有 herdr 服务:看所有机器的可操作 agent,操作指定工作台(以目录仓库为单位),调整窗格布局,对任意 agent 发消息
- 动词全景:VIEW(view/list)+ OPERATE(read/keys/mode/prompt/split/layout/tab/zoom/ws/start/trust/sync)+ 透传(其余 herdr agent 子命令)
- **其他四原语同机制**:shares/streams/tasks/pipes 同以 --machine 全路由 + primlib 共享文法为底,各自骑其引擎(s5/hst/tailcat);跨机 = 引擎命令 + --machine,零 ssh 零旁路
- **id 模型三分**(用户令 2026-10-13 终形):
  1. **在线 agent = agent id**(全局唯一名,操作不关心机器,如 `agents prompt hst_rs "..."`,,primlib 自动寻址)
  2. **机器 + 工作台 shell**:`agents shell <机> <仓库目录>`(开某机器某仓库的工作台 shell 格)
  3. **机器 + 工作台 agent**:`agents dev <机> <仓库> [--kind claude]`(开某机器某仓库工作台并起 agent;工作台 = 项目目录带 git 仓库的概念,agents ws 以仓为单位建台)
- 隐式路由不变:调用方只给名字/机/仓,local 与 --machine 由 primlib 自适
- **窗格拓扑三分定义**(用户令 2026-10-13):
  1. **跨工作台**:不同 workspace 之间的操作(agents ws/machines 面;agent id 全局寻址天然跨台)
  2. **工作台邻居窗格(neighbor)**:同台同 tab 内的相邻格(2x2 顺时针布局里的左右上下;`agents split --direction` 创建,`agents zoom/focus` 导航)
  3. **工作台 tab 窗格**:同台不同 tab 下的格(满四格后自动开新 tab;`agents tab list/create/close` 管理)
  - 操作语义:read/keys/prompt 按 agent id 定位(台无关);split/layout/tab 按 `<机:格>` 或 `<机>` 定位(拓扑面);ws 以仓库为单位建台

## 九、doc-cli 对齐差距(v2.4 批挂账,2026-10-13 用户纠「没有按照设计走」)

实测差距(vs doc-cli 乙面五件):
1. --llms:五命令已带但为 case 臂手维护(primlib 加载后,缺依赖端未达手册即错);无 --llms --json 机器形;零漂移守卫(手册与 case 分支无断言)
2. 信封:--json 仅 DELIVER 成功形;错误 stderr 仍人读文,未落单行 {"code","message","cta"}(第三节承诺未兑)
3. 必选旗标七件:--filter-output/--format/--full-output/--schema 四件缺
4. VIEW/OPERATE 无 --json 两形
5. 已合:裸调用=VIEW exit 0;退出码三态;错误分道 stderr
v2.4 批 = 补齐上四项 + 漂移守卫(手册动词表对 case 分支断言)进静检链
