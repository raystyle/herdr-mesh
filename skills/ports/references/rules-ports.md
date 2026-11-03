---
patterns: [端口转发, port-forward, expose a port, 映射服务口, ports, tailcat]
---

## ports 端口映射域操作指导

- 暴露本机口:`ports open`;访问对方已开的口:`ports fwd`;`close` 停映射;`view` 看映射表
- 引擎 tailcat serve;spec = 端口表/定点映射/all/exit-node;取用行 tailcat forward
- 与 pipes 分野:ports 是端口映射域(服务口),pipes 是临时管道域(一次性字节流)
- 不要用于:文件或消息
