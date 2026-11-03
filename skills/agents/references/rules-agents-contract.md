---
patterns: [--llms, --json, 错误码, not_found, gate_refused, engine_fail, 退出码, 信封, CTA, 七原语, 文法]
---

## agents 域文法与输出契约(七原语共享面)

- 文法:`<命令> [全局旗标] <动词> [旗标] [位置参]`;全局七旗标任意槽;未知词 usage 退 2 禁静默 shift
- 两形同源:`--json` 机器形(单行信封 ok/data/meta,data 恒带 status 四态),缺省人读形,字段序一致;错误一律 stderr,stdout 永纯数据
- 错误码四枚:not_found(名或机未命中,同名多格也走此)/ gate_refused(门控拒,--force 重发)/ engine_fail(引擎原文透传)/ usage(退 2);CTA 统一『下一步:』前缀
- 退出码 0/1/2 禁其他:拒投时 stdout 仍出 ok:true 信封但 exit 1,判定看退出码与 data.status 勿单信 ok;裸调用 = VIEW,exit 0
- 五域速查:agents(to/read/keys/mode/start/split/tab/zoom/trust 等)、shares(put/get/to)、streams(room/dm/append/to)、tasks(set/to)、pipes/ports/mcps/ctxs 同族
- 门控 v2:TUI 实况尾窗判标,只拒操作对话框,busy 排队不拦,误拒优于误投
