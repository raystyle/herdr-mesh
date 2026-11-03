---
patterns: [实时字节, 日志尾随, tail, stream bytes, 实时喂字节, pipes, pipe]
---

## pipes 实时字节域操作指导

- 听侧 `open <addr>` 起听,写侧 `send <addr> <字节>`;`close <addr>` 停听
- 用途:实时喂字节、日志尾随(tail live stdout)、还在长的流
- 不要用于:跟房间消息(走 streams)、传写完的文件(走 shares)
