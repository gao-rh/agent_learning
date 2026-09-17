# 本地 API Key 管理

- `keys.env`：真实密钥，只保存在本机，已被实验目录的 `.gitignore` 排除。
- `keys.env.example`：可提交的空模板，不允许写入真实密钥。
- 当前 3-1/3-2 只需要填写 `MOONSHOT_API_KEY`。其他字段是后续官方实验的预留位。
- 不要在对话、实验记录、终端截图或 Git 提交中暴露文件内容。

Kimi 国内开放平台默认使用 `https://api.moonshot.cn/v1`。如果 Key 来自国际平台，运行时追加：

```bash
--endpoint https://api.moonshot.ai/v1
```
