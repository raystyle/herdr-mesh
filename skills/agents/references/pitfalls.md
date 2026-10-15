# 现行坑(需反例才能敲对)

## 寻址

- 无名格裸写格 id(如 `to w8:p1`)被当机标签解析:用 `local:<格>` 或 `<机>:<格>`
- 同名多格 = not_found(信息注多名):用 `机:名` 显式形一次命中
- 裸 pane id 非法但实装名字解析仍命中 pane_id:勿依赖此偏离,起格必带名
- 拿 hostname 形回投(如 `<hostname>:<格>`)不可解析:同机用 `local:<格>`,跨机用在册别名

## 投递与信封

- 拒投代记流键两形并存:实装用目标格 pane id(`room/deferred/w8:p1` 形),shell 形旧流按收方名仍在;补收两边都看
- streams 域拒投不写流不保原文:要留消息改走 `streams append` 或 `--force` 重发
- from 机器段按目标感知(同机 local、跨机别名):拿旧 hostname 形当回信地址会 not_found
- 同 cwd 多格 caller_addr 歧义不猜:退化机名加告警,按名寻址

## 读流

- 默认尾读最近 100 行:`-n N` 调量,全量 `--from 0`
- cursor 机内不共享:换机从 0 或显式 seq 起
