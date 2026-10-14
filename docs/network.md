# 网络层设计:lan 节点与云节点

## 节点两类

| 类 | 形态 | 网络面 | 承载 |
| --- | --- | --- | --- |
| lan 节点 | 家庭/办公交换机下的物理机 | LAN 段互访 + tailnet 叠加 | 重负载工位(编译/构建/长跑)、模型网关与日志存储 |
| 云节点 | 云 VPS(公网侧,NAT 后) | 仅 tailnet 入内 | 轻负载常驻(网关/服务/探针) |

判据: LAN 段可达 = lan 节点;只有 tailnet 道的 = 云节点。两类在同一 mesh 内平权寻址。

## 通道三层

```
LAN 直连(lan 节点互访首选,延迟最优)
  tailnet 私网(全节点互通: lan + 云;lan 节点间也走,但 LAN 可达时直连优先)
    子网路由(云节点回访 LAN 段服务: 经 lan 侧网关路由器暴露家庭段)
```

- lan 节点互访: 命令面走 LAN 直连,零隧道税
- 云节点入网: 仅 tailnet 一条道(公网 VPS 无 LAN 可言);要访问 LAN 段内服务走子网路由
- lan 节点出门(外网场景): 自动回落 tailnet,身份与寻址不变

## tailnet 组成(自建)

- 控制面 headscale 自托管(节点注册/策略/密钥全自主)
- 数据面节点间直连,DERPER 中继兜底(NAT 打不通时)
- 地址: v4 CGNAT 段 + v6 ULA 双栈;服务端绑 v4 段最稳(部分客户端 v6 无监听)

## magic dns

- 控制面开 magic dns: 节点短名直接解析(节点名即主机名),云节点与 lan 节点同名同权
- ssh 与原语寻址免记 IP: `ssh <节点短名>`、herdr machine add <短名> 即达
- 自定义域后缀可选;节点短名与 mesh 机标签对齐是正配

## tailscale ssh(策略层 ssh)

- tailscaled 接管 22 端口: banner = SSH-2.0-Tailscale,身份授权走 tailnet 策略(免分发钥匙)
- 平台缺口: 部分 GUI 客户端(如 mac)做不了 tailscale-ssh 客户端握手;该类节点互补道:
  - lan 节点: 普通 ssh 走 LAN 地址,钥匙互信分发
  - 云节点: 目标侧开 sshd 副端口(避 22 被接管),经 tailnet IP 直达
- 策略示例(headscale 形):

```json
{
  "ssh": [
    {"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self"], "users": ["autogroup:nonroot"]}
  ]
}
```

## 与 mesh 的关系

- 五原语跨机面走各端 herdr server 的 api 转发(--machine),承载网 = LAN 直连(可达时)或 tailnet
- tailscale ssh 是运维兜底道(装机/救援/首配),不是原语数据面
- 云节点跑常驻服务(网关/看板)时,lan 节点经 tailnet 访问其服务端口;云节点采集 lan 侧数据走子网路由
