# DELIVER 门控、代记、状态信封

> 蒸馏自契约一、四、五a、五b、五c、六节。DELIVER = 定向传递(动词统一 `to`);三道保险 = 门控、代记、审计;回调 = status 四态信封。

## 门控判据（v2:TUI 实况尾窗检测）

- 不看状态字段,看 TUI 实况;复杂判断全隐藏命令内,调用方零感知
- 实现形:读格可见内容**尾 12 行**(对话框按钮与页脚区),对目标格 TUI 家族判标族匹配(四家:claude/codex/grok/kimi 实测文案,家族缺省回落 claude);命中即拒;正文里的文档引用(如信任屏教学文)不算屏上对话框,不误判
- **操作对话框即拒**(信任屏/权限屏/模式选择);**空 TUI 可投**;**busy 排队不拦**(各家 TUI 自带消息排队,working 不是拒投理由)
- 判标族保守清单,误拒优于误投
- `--force` 跳门控强投;任意参数位识别(v3 文法),不占尾参位

## status 四态信封（纪律:错误要暴露,状态要回调）

`--json` 时 DELIVER 的 data 恒带 `status`,四态:

| status | 判定 | 说明 |
| --- | --- | --- |
| `delivered` | 投出且 15s 内目标转 working | 目标已开始处理才算送达 |
| `deferred` | 门控拒投,已代记 | 退出码仍 1;stdout 仍出 `"ok":true` 信封,判定看退出码与 status,勿单信 ok |
| `stalled` | 写入但 15s 未转 working | 收编 herdr agent_prompt_stalled/timeout |
| `engine_fail` | 引擎写败 | data 带 `engine_error`(引擎 stderr 摘要,原文不吞不裁透传) |

- 退出码不变(0/1/2);状态分型走 data.status,不新码
- 实现形:`herdr agent prompt <格> <文本> --wait --until working --timeout 15000`,返回码与 stderr 关键词归四态
- 收件面(read)另出目标态信封:idle/done 即得即回,忙候超时出 `timeout-working`(内容仍全量附上,exit 0);read 是收件反射,与 DELIVER 四态分立

## --force 审计（契约面）

- 每次 force 强投追记 `room/force-audit` 流:src、目标、域、id;不记正文
- 查审计:`streams view room/force-audit`
- 3.0.0a1 未落(python 形;shell 形曾落);强投前自问必要性

## 拒投代记与补收

- 拒投时意图自动记入 `room/deferred/` 流(全域含 agents to,R0 补齐),退出码仍 1,CTA 注明代记;agents 域代记含原文截 80 字,shares 域注明键待达,人不丢件
- 收方补收:`streams view room/deferred/<落点>`;**落点键两形并存**:v3 python 形用目标格 pane id(`room/deferred/w8:p1` 形),shell 形旧流按收方名(`room/deferred/hst_rs` 形),两边都看
- streams 域拒投:**不写流不保原文**,代记只记流名与待递;要留消息改走 `streams append`(OPERATE 无门控)或 `--force` 重发
- 消息不静默丢失:拒投不等于没发,意图在代记流里等你

## 幂等 id 与版本字段

- `v=1` 字段行恒带(信封 v2 已落,缺省 1);新字段只加行尾;主版本收方不识 = 不执行取用行(记 engine_fail)
- 字段行尾可选 `id=<一次传递的标识>`(契约面):重发沿用同 id,收方按见过即弃; id 未落,重发防重靠收方自觉比对 seq 与正文

## 信封 v2 定稿四行形（2026-10-15 用户样例令三次定形;真源 prim msg.py,render 落形随版滚）

```
[<域>] @<收方> <一句话>
<空行>
from=<host_label>:<agent别名> to=<id> <域字段...> v=1
use: <可复制命令行>
```

- 定稿四行形:头行 `[域] @收方 <一句话>` 合一带全部路由面,空行,from 字段行与 use 行沉底(结构行居后);同日五行头序曾定谳旋即被本形取代
- grok TUI 输入面拍扁粘贴换行属收方显示怪癖,记坑不降协议(claude 面跨机逐字回执实证)
- 双轨制:消息收发用 机:agent别名(名即路由键),窗格布局操作才用 机:格;无名格信封退化 机:格(正名走 herdr agent rename)
- `from` 机器段 = host_label(PRIM_HOST_LABEL 优先,linux/mac 机 hostname 即注册名);hostname 直落 from 属故障不是正常形

- 头行兼容 IM 直觉,正文一句话在头行;字段行与 use 行禁改写(自然语言信封的失败处 = 对方改写取用命令)
- `from=` 与 `to=` 恒在;`v=` 恒带;域字段随域:shares = key/name;streams = stream;tasks = cwd;pipes/ports = addr;agents 自由文
- 回信取用行 = `agents to <裸别名> reply`(reply 为字面量;streams 域附 `(stream <流> attached)`);shares 键与 streams 流名在字段行 key=/stream=,不占 use 行;tasks 取用 = `tasks view`,pipes 取用 = `tailcat <addr>`,ports 取用 = `tailcat forward <addr> [0:]<端口>`(addr 在字段行;send 原语缺口记档);发话格无别名退化 `agents to <机:格> reply`,格未定降级 `agents view, locate the sender pane on <机>, then agents to <机:agent别名> reply`
- 收方机读:`parse_fieldline` 解析字段行,缺 from/to 视为旧形(src= 时代)记 compatibility 警
- use 行前缀恒 `use:`(2026-10-15 英文令:指令面全英文,prim msg.py use_line 渲染);收方动作 = 执行取用行,失败时回信给 from(先核验,见 addressing.md)
- 回信直答:裸别名 `agents to <from 的别名段>`;`local:<格>` 只用于窗格操作(keys/split/zoom/close)
