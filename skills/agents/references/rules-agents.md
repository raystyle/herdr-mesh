---
patterns: [tell, ask, ping, reply, inbox, 等回话, 等回信, 读屏, 按键, 派单, 私信, 回执, 翻台, 在场, to, wait, read]
---

## agents 消息域操作指导

- 投递:`agents to <id> <文本>`(门控在役时拒投代记 room/deferred,--force 跳过);等回信:`agents wait <id> [--timeout N]`(事件道,免轮询读屏)
- id 三产生式:裸别名(消息面唯一推荐)> `机:别名` > `机:格`;`local:格` 仅本机调试,禁入跨机信封主 to
- 命名标准:`<台名>-<类型>-<编号>`(如 myws-kimi-1);工位 id 与 agent 名两套键:操作格用 pane id,投递用别名
- 信封 v2:from/to/v=1 形;status 四态(working/idle/blocked/done);在场声明 `mode` 与同格重载 `reload` 恒在 agents 面
- 读屏:`agents read <id>`(实时屏);历史对话走 ctxs,不走 agents
- 不要用于:文件(shares)、房间留痕(streams)、跨回合任务(tasks)、开格分屏(desks)
