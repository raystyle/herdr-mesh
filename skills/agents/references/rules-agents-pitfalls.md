---
patterns: [寻址歧义, not_found, 拒投, 代记, 同名多格, hostname 回投, cursor, 尾读]
---

## agents 现行坑指导

- 无名格裸写格 id(`to w8:p1`)被当机标签:用 `local:<格>` 或 `<机>:<格>`;同名多格 = not_found,用 `机:名` 显式形
- 拿 hostname 形回投不可解析:同机 `local:<格>`,跨机用在册别名
- 拒投代记流键两形并存(实装 `room/deferred/<格 pane id>`、shell 旧流按收方名),补收两边都看;streams 域拒投不写流不保原文,要留消息走 `streams append` 或 `--force` 重发
- from 机器段按目标感知(同机 local、跨机别名);同 cwd 多格 caller_addr 歧义不猜,按名寻址
- 读流默认尾读 100 行(`-n N` 调,全量 `--from 0`);cursor 机内不共享,换机从 0 起
