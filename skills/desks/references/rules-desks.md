---
patterns: [工位, 工作台, 窗台, 开台, 开格, 起格, 分屏, 切tab, 关格, 聚焦, 翻台, 信任屏, 拓扑, desks]
---

## desks 工位与窗格拓扑操作指导

- 开台:`desks ws <label> [--cwd DIR]`(按仓路径开工作台);起格:`desks start <名> --kind <类> [--cwd DIR]`;分屏:`desks split <id> --direction right|down`;切页:`desks tab <list|create|close>`;聚焦:`desks zoom <id>`
- 拓扑真视图:`desks view`(窗台 w -> tab -> 工位 pane 三层分组,▍ 焦点工位,活动列 = 终端标题);`ws` 裸调用即列台
- 命名契约四层:机册 label(herdr 真源)> workspace w 编号(唯一寻址键,label 是显示名非寻址键,禁斜杠形)> tab t 编号 > pane p 编号(尾缀字母系统指派无词义规则,角色槽不进寻址)
- 寻址优先级:裸别名 > `机:别名` > `机:格`;方向词仅分裂时存在;无 focus/neighbor/layout 动词,空间关系从 view 人读
- 坑:`ws list` 的 list 被当机标签(用 `ws` 裸调用列台);空 pane = 异常态须补 agent 或 close
- 消息与等回信走 agents;机册管理走 machines;desk 为旧名单字别名
