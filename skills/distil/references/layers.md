# 三层聚合:唯一出处层、双链知识与标准面

> 原语沿知识库三层聚合(sources、knowledge、operations 单向支撑),在技能自进化语境下各层收窄定形:sources = 唯一出处层(自产轨迹、自产证据件、外档信源原档),knowledge = 带版本的双向链接关联结构化知识,operations = 标准面(标准 skill 与 how-to 手册)。本篇管三层结构、写法与流转;环与闸门见 loop.md 与 gate.md,双端加载见 backends.md。

## 三层结构(单向支撑)

| 层 | 承载 | 回答 | 形态 |
| --- | --- | --- | --- |
| `sources/` | 唯一出处层:自产轨迹(会话、日记、回执、门禁输出、评审记录按时间收束)、自产证据件(REQ trace 证据、工件包、门禁输出)、外档信源原档 | 发生过什么、出处是什么 | 带时点的出处件,只增不改 |
| `knowledge/` | 带版本、双向链接关联的结构化知识(模式页、防重提页、索引与流水) | 是什么、为什么 | 版本化知识页,[[双链]] 关联 |
| `operations/` | 标准面:标准 skill 与 how-to 标准手册(Claude Code 与 Codex 双端支持) | 怎么做、验收什么 | 标准页集,过闸才进 |

- 单向支撑:knowledge 页靠 sources 撑,标准 skill 靠 knowledge 撑,反向不成立
- 记忆类型映射(CoALA):sources 约等于 episodic,knowledge 约等于 semantic,operations 约等于 procedural;会话上下文约等于工作记忆,不进三层;外档靠 relation 类型判别,不设第四层
- 硬规则:模式页无 trace 引文标 unverified,不得当提案依据;标准 skill 无 knowledge 链接不得当规范执行;原理不进标准页,步骤不进知识页,正文不进索引
- 流转:新轨迹入库 = 新建或追加 sources 件加更新对应 knowledge 页并链接;模式已稳要落地 = 提案进 operations(走闸门);标准页与知识冲突 = 带 sources 的 knowledge 页为准

## sources 唯一出处层

- 每条轨迹总结带时点(日期加场景标识),一段收束一个执行片段:做了什么、结果、证据指针(会话文件路径、commit sha、门禁退出码);不贴原始长转录,留指针
- **三类出处分根收口**:自产轨迹(diary 族)、自产证据件(REQ trace 证据、工件包、门禁输出、回执)、外档信源原档(verbatim 留底);一层一索引盖全根;项目级自持,跨仓材料以内嵌链接与 verbatim 留底进本层,不设跨仓共享知识库
- **证据分级靠 relation 不靠目录**:derived_from(自产)撑模式页,cited_source(外档)撑综述与研究结论页(词表见 knowledge 节)
- **资格过滤在前**:零工具调用、空输出、启动失败的回合不进样本也不进分母;死会话对陈旧交付物的打分是假证据,资格检查没接通前不开蒸馏;接通最低形态 = 每条样本带可回查指针(git sha 或会话文件路径),判据内联实证(逐条「实证: 日期加证据」回填)为最小范本形,人肉筛达标口径同此,蒸馏样本破两位数再立工具化
- 只增不改:轨迹是历史,修正走新条目,不回写旧条;一天一篇的轨迹总结写法与升格分流见 trajectories.md

## knowledge 双链知识层

- **模式页**(patterns):PROBLEM、ROOT CAUSE、FIX 三段,10 至 30 行;FIX 只许一句非步骤结论(不含命令与步骤,可执行步骤只出现在标准 skill 页);约束升格:坑复现条件可机器化时,约束断言进门禁,模式页只记约束指针(断言本体在门禁配置,判例:坑表同型二犯起配 lint);写行动模式不抄报错;对照成功轨迹保留有效行为;必带 trace 引文(sources 路径加时点或片段),无引文标 unverified;合并重复,不发明轨迹不支持的模式
- **防重提页**(skill-impact):收被拒提案全文与 diff,只由闸门追加;蒸馏与提案角色对它只读,丢失或改写即本轮蒸馏失败;提案前必读,防重复已拒路线
- **索引与流水**:索引是可再生成的导出物(不是唯一入口,漏行不能让磁盘上的模式页不可见);强形 = 双链图机器再生,每次蒸馏后重跑,节点与边计数随流水记录,漂移可检;流水按轮次记蒸馏、提案、闸门三行结论
- **双链与版本**:知识页 frontmatter 登记 `links`(target 加 relation)与版本,形状定式:

```yaml
version: 1
links:
  - target: sources/diary/2026-10-10-主题
    relation: derived_from
```

  正文 `[[路径去 .md]]` 双链,单独成行挂主题、句中作参见;检索跟双链展开默认最多 2 跳,要出处再进 sources
- **relation 词表**:资格判据只认两根词(derived_from 自产、cited_source 外档);仓内细分词与 supersedes 归白名单,不进资格判定;新轨迹否定旧模式时新开版本或挂 supersedes 关系,不原地改写使旧 trace 对不上正文

## operations 标准面层(技能与 how-to 手册)

- 收两类候选,皆过闸:**标准 skill**(双端支持的标准项目级 SKILL.md:frontmatter 只留官方字段,禁 version 等非官方字段;正文含 When to Apply 与 When NOT to Apply(不适用面是防「一个失败模式写成通用技能」的槽)与步骤;不点名外部仓库)与 **how-to 标准手册**(挂知识底座链);reference 与 explanation 归 knowledge,教材类不进标准层(Diátaxis 判据)
- **页头闸门记录段**:过闸产物页头自记三证据(门禁当轮实跑无回归、翻转的点名义务、链到带 sources 的知识页)加一行回指(正文指回促成它的模式页),出处与过闸证据就地可见,不依赖翻 commit 消息与流水
- **工件包拆层**:how-to 手册(挂知识底座链)留本层;纯工件(配置、sql、conf 等交付工件)归 sources 证据面,不混装
- **加载视图**:operations 层根(如 docs/operations)收两类;技能安装路径(.claude/skills 等)是技能子集的加载视图(符号链接或投影加同步守卫),手册不进安装路径,不分发第二份;常驻面只有 frontmatter 的 name 与 description,正文与 references 按需加载(渐进披露三级);触发用例集随技能入库(evals 件(references 目录,3 至 5 条,过闸产物,渐进披露第三级)
- **version 纪律**:顶层 version 恒禁(agentskills spec 官方字段面);仅「跟踪上游已接受代」的字节拷贝分发形可写 spec 官方 metadata.version 且登记在册,比对义务为上游代或哈希二选一(只比版本串会漏字节改而标签不改);仓内标准技能不写(唯一权威源加视图守卫加版本线三件套已覆盖);校验器仅豁免形认 metadata.version,顶层 version 一键即红
- **git 协议,两层时点拆明**:operations 候选先落未提交工作区,接受才 commit,拒绝即 reset 或路径级 restore 回基线;knowledge 蒸馏完即提交,先于提案与闸门,拒绝不回收;「独立 git」语义由 git 边界或纪律承担,保证点同为 knowledge 永不随标准集回滚(边界三选一见建仓五步)
- 执行回合不整层注入 knowledge:执行者读知识层实证降效,知识面经标准页回指按需读
- 唯一权威源在项目仓;双端按各自项目级面加载(见 backends.md),不分发第二份

## 建仓五步

1. 立三层目录与各自索引,git 边界三选一:**分仓** / **分目录分 git**(外层仓 .gitignore 登记该目录防嵌套 .git 被追踪,外层文档门禁对三层目录的豁免显式声明)/ **单仓纪律形**(提交分层:知识先于标准独立成 commit;路径级回滚:闸门拒绝只 restore 技能安装路径,knowledge 路径永不 reset;适用单人单仓、knowledge 随主仓备份)。排除形:agent 记忆库内嵌技能(技能与记忆同一 git)。层根位置仓自选仓根或 docs/,全仓唯一
2. 首批轨迹总结带时点入库,既有项目经验先收口(首轮收口天然超取样窗,豁免)
3. 蒸馏首批模式页,带 trace 引文与 links
4. 立防重提页与流水,空态也要立(见 gate.md);防重提页只收被拒提案,不兼做事实否证账(否证走 supersedes 关系,见 knowledge 节)
5. 标准 skill 集从空态起步,一切进集走闸门;存量手册族整族一案补闸口径

既有仓迁移形:存量 docs 全家桶仓不推倒重来;先在层索引落旧名到字母表的映射注记,目录名统一走 git mv 保史加现役面引用同步,迁移引用面清单(入口合同 Read first、README 地图与层索引、门禁脚本路径断言与骨架目录断言、用户裁定红线),mv 后 rg 旧名清零为验,先改断言再 mv 防门禁红;历史轨迹不回写(首轮收口豁免可援引第 2 步);约百件量级迁移已有判例实测。仓内 `.claude/` 整体 ignore 的存量仓,先以忽略登记划界(仅放行 `.claude/skills/`)再挂加载视图(见 backends.md)。

## 归档统一字母表

| 字母 | 语义 | 归层 |
| --- | --- | --- |
| ADR-NNNN | 不可逆裁定 | knowledge/adr |
| REQ-NNNN | 需求登记 | knowledge/req(弃 requirements 名) |
| R-NNNN | 参考知识(reference,事实不解释) | knowledge/references |
| G-NNN | how-to 标准手册 | operations |
| M-NNN | 坑模式(蒸馏产物) | knowledge/mistakes |
| P-NNNN | 判例实弹记录 | sources 证据面 |
| S-NNNN | 研究档案结论页 | knowledge/research(原档 sources/external) |
| diary | 日轨迹 | sources/diary |

一字母一类不混挂;前缀混挂修正走退役不复用律(旧号退役留档注记,内容升新号);既有仓前缀与字母表语义撞义时按语义归族(如手册形 R 号升 G 新号,旧号退役注记),不字面迁移;退役编号在索引留档注记不回收,缺号可检;doc-gov 工件归层同此表,doc-gov SKILL 意图路由互指。
