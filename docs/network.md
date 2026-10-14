# 网络层架构:自建 tailnet + tailscale ssh + magic dns

## 拓扑

```
自建控制面(headscale,自托管)
  tailnet 私网(100.64.0.0/10 CGNAT 段 + fd7a::/48 ULA v6)
    端点甲(控制台宿主,双栈: LAN + tailnet)
    端点乙组(LAN 成员: 交换机下互通,LAN 段直连优先)
    端点丙(NAT 后远端: 仅经 tailnet,LAN 段不可达)
    网关路由器(子网路由: 暴露家庭段给 tailnet 成员)
```

设计要点:

- 控制面自托管,节点间数据面直连(DERPER 兜底中继)
- 端点双栈: v4 CGNAT 段 + v6 ULA;部分客户端 v6 无监听时服务端绑 v4 段
- NAT 后远端访问 LAN 段服务 = 经网关路由器的子网路由;直达走 tailnet IP

## magic dns

- 控制面开 magic dns: 节点短名直接解析(节点名即主机名)
- ssh 免记 IP: `ssh <节点短名>` 直达
- headscale 形: 节点在册后短名入解析;自定义域后缀可选

## tailscale ssh(策略层 ssh)

- tailscaled 接管 22 端口: banner = SSH-2.0-Tailscale,身份与授权走 tailnet 策略(action accept,src autogroup:member,dst autogroup:self 或收紧)
- 客户端免钥: tailscale ssh 按节点身份认证,普通 ssh 客户端走 tailscaled 代理
- 平台缺口(mac 客户端): 部分 GUI 客户端做不了 tailscale-ssh 客户端握手(`failed to get connection info`),该类端点走普通 ssh 道互补:
  - LAN 成员: ssh 直连 LAN 地址(钥匙分发互信)
  - 无 LAN 段远端: 目标侧开 sshd 副端口避 22 被接管
- 策略示例(headscale 形):

```json
{
  "acls": [
    {"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self:*"]}
  ],
  "ssh": [
    {"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self"], "users": ["autogroup:nonroot"]}
  ]
}
```

## 与 mesh 的关系

- 五原语的跨机面走各端 herdr server 的 api 转发(--machine),承载网即 tailnet;tailscale ssh 是运维兜底道(装机/救援),不是原语数据面
- LAN 成员间的命令面走 LAN 直连(延迟优),tailnet 为跨网段与远端道
- wt 控制台(windows terminal)开远端视图: `ssh -t <节点> herdr` 即可,显示面不涉策略
