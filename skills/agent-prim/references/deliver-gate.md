# DELIVER 门控、代记、状态信封

> 蒸馏自契约一、四、五a、五b、五c、六节。DELIVER = 定向传递(动词统一 `to`);三道保险 = 门控、代记、审计;回调 = status 四态信封。

## 门控判据（v2:TUI 实况尾窗检测）

- 用户令(2026-10-13):不看状态字段,看 TUI 实况;复杂判断全隐藏命令内,调用方零感知
- 实现形:读格可见内容**尾 12 行**(对话框按钮与页脚区),对目标格 TUI 家族判标族匹配(四家:claude/codex/grok/kimi 实测文案,家族缺省回落 claude);命中即拒;正文里的文档引用(如信任屏教学文)不算屏上对话框,不误判 [实证:包源直读;evo 实弹案 = working 格读 skill 文档整屏扫描假阳性,尾窗后 delivered]
- **操作对话框即拒**(信任屏/权限屏/模式选择);**空 TUI 可投**;**busy 排队不拦**(各家 TUI 自带消息排队,working 不是拒投理由)
- 判标族保守清单,误拒优于误投
- `--force` 跳门控强投;任意参数位识别(v3 文法),不占尾参位

## status 四态信封（v2.8 纪律:错误要暴露,状态要回调）

`--json` 时 DELIVER 的 data 恒带 `status`,四态:

| status | 判定 | 说明 |
| --- | --- | --- |
| `delivered` | 投出且 15s 内目标转 working | 目标已开始处理才算送达 |
| `deferred` | 门控拒投,已代记 | 退出码仍 1;stdout 仍出 `"ok":true` 信封,判定看退出码与 status,勿单信 ok [实证] |
| `stalled` | 写入但 15s 未转 working | 收编 herdr agent_prompt_stalled/timeout |
| `engine_fail` | 引擎写败 | data 带 `engine_error`(引擎 stderr 摘要,原文不吞不裁透传) |

- 退出码不变(0/1/2);状态分型走 data.status,不新码
- 实现形:`herdr agent prompt <格> <文本> --wait --until working --timeout 15000`,返回码与 stderr 关键词归四态 [实证:包源直读]
- 收件面(read)另出目标态信封:idle/done 即得即回,忙候超时出 `timeout-working`(内容仍全量附上,exit 0);read 是收件反射,与 DELIVER 四态分立 [实证:双态实测]

## --force 审计（契约面）

- 每次 force 强投追记 `room/force-audit` 流:src、目标、域、id;不记正文
- 查审计:`streams view room/force-audit`
- [实证] 3.0.0a1 未落(python 形;shell 形曾落);强投前自问必要性

## 拒投代记与补收

- 拒投时意图自动记入 `room/deferred/` 流(全域含 agents to,R0 补齐),退出码仍 1,CTA 注明代记;agents 域代记含原文截 80 字,shares 域注明键待达,人不丢件
- 收方补收:`streams view room/deferred/<落点>`;**落点键两形并存**:v3 python 形用目标格 pane id(`room/deferred/w8:p1` 形),shell 形旧流按收方名(`room/deferred/workbench-claude-1` 形),两边都看 [实证:两形流俱在册]
- streams 域拒投:**不写流不保原文**,代记只记流名与待递;要留消息改走 `streams append`(OPERATE 无门控)或 `--force` 重发 [实证]
- 消息不静默丢失:拒投不等于没发,意图在代记流里等你

## 幂等 id 与版本字段

- `v=1` 字段行恒带(信封 v2 已落,缺省 1);新字段只加行尾;主版本收方不识 = 不执行取用行(记 engine_fail)
- 字段行尾可选 `id=<一次传递的标识>`(契约面):重发沿用同 id,收方按见过即弃;[实证] id 未落,重发防重靠收方自觉比对 seq 与正文

## 信封 v2 三行形（逐字稳定;pydantic 真源 prim/src/prim/msg.py）

```
[<域>] @<收方> <一句话动作>
from=<host>:<pane> to=<id> <域字段...> v=1
取用:<可复制命令行>
```

- 人话行带 `@收方`(兼容 IM 直觉),正文自由;字段行与取用行禁改写(自然语言信封的失败处 = 对方改写取用命令)
- `from=` 与 `to=` 恒在;`v=` 恒带;域字段随域:shares = key/name;streams = stream;tasks = cwd;pipes = addr;agents 自由文
- 收方机读:`parse_fieldline` 解析字段行,缺 from/to 视为旧形(src= 时代)记 compatibility 警
- 第三行前缀一律 `取用:`;收方动作 = 执行取用行,失败时回信给 from(先核验,见 addressing.md)
