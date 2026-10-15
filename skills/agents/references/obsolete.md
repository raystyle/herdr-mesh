# 废止敲法（拿旧输出对照时读）

- 信封字段行 `src=<host>:<pane>`:v2 起改 `from=` 加 `to=` 加 `v=`
- `hst goal` 命令族:正名 `hst task`;取用行旧形 `cd <cwd> && hst task show` 已废,现取用行 = `tasks view`
- herdr 裸命令操作面(herdr agent prompt/read/start 等):agents 域全吸收,走 `agents to/read/start`
- 旧插件 evo-doc、evo-herdr、evo-distil、evo-lint、evo-agent:市场改 dev 与 evo
- `tasks view` 读 tasks/shared 事件流:转实时任务面,事件流旧档只读
- `agents prompt` 裸走门控无代记:现与 `to` 同形,拒投自动代记
