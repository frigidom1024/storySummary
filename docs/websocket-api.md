# WebSocket 消息协议文档

## 连接方式

```
WebSocket URL: /books/{book_id}/ws
```

前端通过订阅指定书籍的 WebSocket 频道来接收分析进度更新。

## 消息格式

所有 WebSocket 消息均为 JSON 格式，由 `ProgressMessage` Schema 定义：

```json
{
  "progress": 0-100,
  "message": "string",
  "status": "processing" | "completed" | "failed",
  "type": "analyze" | "manuscript"
}
```

### Schema 定义

```python
class ProgressStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProgressType(str, Enum):
    ANALYZE = "analyze"
    MANUSCRIPT = "manuscript"

class ProgressMessage(BaseModel):
    progress: int  # 0-100
    message: str
    status: ProgressStatus
    type: ProgressType  # analyze | manuscript
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| progress | int | 进度百分比 (0-100)，超出范围会校验失败 |
| message | string | 状态描述文本 |
| status | ProgressStatus | 枚举值：`processing`(进行中) / `completed`(已完成) / `failed`(失败) |
| type | ProgressType | 枚举值：`analyze`(书籍分析) / `manuscript`(口播稿生成) |

### status 状态类型

| 状态 | 说明 |
|------|------|
| `processing` | 进行中 |
| `completed` | 已完成 |
| `failed` | 失败 |

### type 任务类型

| 类型 | 说明 |
|------|------|
| `analyze` | 书籍分析 |
| `manuscript` | 口播稿生成 |

## 书籍分析消息

### 进度推送

| progress | message 示例 | 说明 |
|----------|--------------|------|
| 0 | "开始解析文件..." | 开始解析 |
| 5 | "文件解析完成" | 文件解析完成 |
| 10 | "开始分章..." | 开始分章 |
| 20 | "分章完成，共 X 个章节" | 分章完成 |
| 20-80 | "正在分析第 1/10 章..." | 节点生成中 |
| 80 | "错误: 第 X 章分析失败: 服务器内部错误，请稍后重试" | 章节分析失败 |
| 80 | "错误: 所有章节分析失败，未能生成任何节点" | 全部失败 |
| 80 | "节点生成完成，正在构建结构..." | 开始构建结构 |
| 95 | "保存完成" | 保存完成 |
| 100 | "解析完成！" | 全部完成 |

### 错误消息

当分析过程中发生错误时，`message` 字段会包含以下格式的错误信息：

| 错误类型 | message 示例 | 说明 |
|----------|--------------|------|
| API 内部错误 | "错误: 第 X 章分析失败: 服务器内部错误，请稍后重试" | LLM API 返回 400/500 等错误 |
| API 认证失败 | "错误: 第 X 章分析失败: API认证失败，请检查配置" | API Key 无效或缺失 |
| 请求频率过高 | "错误: 第 X 章分析失败: 请求频率过高，请稍后重试" | 触发限流 (429) |
| 请求超时 | "错误: 第 X 章分析失败: 请求超时，请稍后重试" | API 请求超时 |
| 文件不存在 | "未找到书籍文件" | 书籍文件丢失 |
| 分析异常 | "解析失败: {error}" | 捕获的异常信息 |

> **注意**: 用户可见的错误消息已经过脱敏处理，不会暴露原始 API 错误详情（如 `tool_calls` 相关错误）。

## 口播稿生成消息

口播稿生成同样使用 WebSocket 推送进度：

| progress | message 示例 | 说明 |
|----------|--------------|------|
| 0 | "正在启动生成..." | 开始生成 |
| ... | "正在生成口播稿第 X/Y 章..." | 生成中 |
| 100 | "生成完成！共 X 章" | 生成完成 |
| 0 | "生成失败: {error}" | 生成失败 |

## 心跳机制

前端可以发送 `ping` 字符串进行心跳检测，服务端会响应 `pong`：

```
Client -> Server: "ping"
Server -> Client: "pong"
```

## 前端接收示例

```javascript
const ws = new WebSocket(`ws://localhost:8000/books/${bookId}/ws`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.status) {
    case 'processing':
      console.log(`进度: ${data.progress}% - ${data.message}`);
      updateProgressBar(data.progress);
      break;
    case 'completed':
      console.log('分析完成:', data.message);
      showSuccess(data.message);
      break;
    case 'failed':
      console.error('分析失败:', data.message);
      showError(data.message);
      break;
  }
};

ws.onclose = () => {
  console.log('WebSocket 连接已关闭');
};
```

## 完整消息流程示例

### 成功流程

```
{"progress": 0, "message": "开始解析文件...", "status": "processing", "type": "analyze"}
{"progress": 5, "message": "文件解析完成", "status": "processing", "type": "analyze"}
{"progress": 10, "message": "开始分章...", "status": "processing", "type": "analyze"}
{"progress": 20, "message": "分章完成，共 5 个章节", "status": "processing", "type": "analyze"}
{"progress": 25, "message": "正在分析第 1/5 章...", "status": "processing", "type": "analyze"}
{"progress": 40, "message": "正在分析第 2/5 章...", "status": "processing", "type": "analyze"}
{"progress": 55, "message": "正在分析第 3/5 章...", "status": "processing", "type": "analyze"}
{"progress": 70, "message": "正在分析第 4/5 章...", "status": "processing", "type": "analyze"}
{"progress": 85, "message": "正在分析第 5/5 章...", "status": "processing", "type": "analyze"}
{"progress": 90, "message": "节点生成完成，正在构建结构...", "status": "processing", "type": "analyze"}
{"progress": 95, "message": "保存完成", "status": "processing", "type": "analyze"}
{"progress": 100, "message": "解析完成！", "status": "completed", "type": "analyze"}
```

### 失败流程

```
{"progress": 0, "message": "开始解析文件...", "status": "processing", "type": "analyze"}
{"progress": 20, "message": "分章完成，共 5 个章节", "status": "processing", "type": "analyze"}
{"progress": 30, "message": "正在分析第 1/5 章...", "status": "processing", "type": "analyze"}
{"progress": 80, "message": "错误: 第 1 章分析失败: 服务器内部错误，请稍后重试", "status": "failed", "type": "analyze"}
```
