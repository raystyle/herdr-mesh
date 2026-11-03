---
patterns: [last request, request_id, transcript, token cost, 上次请求, 历史对话, 查记录, ctxs, 全链检索]
---

## ctxs 对话历史域操作指导

- 三动词:`view [agent] [--limit N]`(头行:时间/模型/token/时长/request_id)、`show <request_id> [--around <词>] [--window N]`(单请求全文,--around 命中块加邻块)、`search <词> [--term <词>]... [--limit N]`(跨请求全文,多词 OR)
- 窗口:头行 365 天、正文 180 天;search 默认 --days 1(慢查询防护),宽窗用 --since/--before 分片
- request_id 从 view 尾列或 search 首列取;「头行:未落」是正常降级非 not_found;空表带表头即链路通
- 引擎 ClickHouse gw_logs(head 表索引 + gwlog 表正文);实时屏走 agents read,ctxs 只管已结束请求
- 语料批量导出不走 ctxs(片段面),走 ClickHouse 直连(reader.env 只读道)
