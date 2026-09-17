# QQ 邮箱 IMAP 接入

- 验证时间：2026-09-08 16:38（北京时间）。
- 状态：本机已接通 `gao_rh@foxmail.com`，默认只读收件箱 `INBOX`、近 14 天。
- 凭据位置：macOS 钥匙串，服务名 `local.qq-mail-reader.imap`。本页不保存授权码。
- 本地工具：[qq_mail.py](/Users/gaoronghui/.local/share/qq-mail-reader/qq_mail.py)；[完整说明](/Users/gaoronghui/.local/share/qq-mail-reader/README.md)。工具属于这台 Mac 的本地配置，不随学习仓库同步。

后续查看应聘邮件，先通过脚本取得候选邮件头，再按 UID 读取相关正文：

```sh
python3 /Users/gaoronghui/.local/share/qq-mail-reader/qq_mail.py scan
python3 /Users/gaoronghui/.local/share/qq-mail-reader/qq_mail.py read --uid 邮件UID --max-chars 5000
```

连接验证入口：

```sh
python3 /Users/gaoronghui/.local/share/qq-mail-reader/qq_mail.py check
```

实际验证了 TLS 连接、钥匙串取凭据、IMAP 登录、只读检索和正文读取。当时收件箱近两周共 38 封邮件，关键词筛出 10 条候选，其中 1 条是 QQ 系统反诈提醒；小红书正文中的「商业化-AI Native Engineer」及「2026-09-16 19:00」已核对。

`scan` 按发件人和主题筛选，会有少量误匹配，也可能漏掉只在正文含招聘词的邮件。HTML 正文先转成纯文字，再截断输出，避免重复读取网页布局。已验证范围是当前账号的收件箱；其他账号、其他文件夹及其编码兼容性尚未验证。读取使用 `EXAMINE` 与 `BODY.PEEK`；本工具不提供发信、删除、移动或修改已读状态的功能。尚未创建邮箱定时任务。

[返回招聘投递记录](../README.md)
