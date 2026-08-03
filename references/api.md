# Agnes AI API Reference（国内版）

> 来源：https://www.agnes-ai.cn/zh-Hans/docs/overview （2026-08 抓取整理）

## Base URL 与认证

```
https://api.agnes-ai.cn/v1
Authorization: Bearer <api_key>
```

API Key 在 https://platform.agnes-ai.cn/ 控制台创建。兼容 OpenAI 风格接口。

## 模型一览

| 模型 ID | 类型 | 说明 |
| --- | --- | --- |
| `agnes-image-2.1-flash` | 图像 | 升级版：文生图/图生图/多图合成，高信息密度优化；档位尺寸 1K-4K + ratio |
| `agnes-image-2.0-flash` | 图像 | 文生图/图生图/多图合成，图像编辑能力强（ELO 1184）；精确尺寸如 1024x768 |
| `agnes-video-v2.0` | 视频 | 文生视频/图生视频/关键帧动画，异步任务 API |
| `agnes-2.0-flash` / `agnes-2.5-flash` | 文本 | 聊天补全（本 skill 不涉及） |

---

## 图像生成

```
POST https://api.agnes-ai.cn/v1/images/generations
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `model` | string | 是 | `agnes-image-2.1-flash` 或 `agnes-image-2.0-flash` |
| `prompt` | string | 是 | 图像生成/编辑指令 |
| `size` | string | 是 | 2.1 推荐档位 `1K`/`2K`/`3K`/`4K`；2.0 用精确尺寸如 `1024x768`。不支持的精确尺寸会被标准化 |
| `ratio` | string | 否 | 配合档位 size：`1:1` `3:4` `4:3` `16:9` `9:16` `2:3` `3:2` `21:9`，默认 `1:1` |
| `image` | string[] | 图生图必填 | 输入图像数组，公网 URL 或 Data URI Base64（放在 `extra_body.image`） |
| `return_base64` | boolean | 否 | 文生图需要 Base64 返回时使用 |
| `extra_body.response_format` | string | 否 | `url` 或 `b64_json` |

### 重要禁忌（官方明确）

- **不要**把 `response_format` 放在请求体顶层 → 必须放 `extra_body` 内
- **不要**传 `tags: ["img2img"]` → 图生图不需要

### 输出尺寸对照（档位 × ratio）

| Ratio | 1K | 2K | 3K | 4K |
| --- | --- | --- | --- | --- |
| 1:1 | 1024x1024 | 2048x2048 | 3072x3072 | 4096x4096 |
| 3:4 | 864x1152 | 1728x2304 | 2592x3456 | 3456x4608 |
| 4:3 | 1152x864 | 2304x1728 | 3456x2592 | 4608x3456 |
| 16:9 | 1312x736 | 2624x1472 | 3936x2208 | 5248x2944 |
| 9:16 | 736x1312 | 1472x2624 | 2208x3936 | 2944x5248 |
| 2:3 | 832x1248 | 1664x2496 | 2496x3744 | 3328x4992 |
| 3:2 | 1248x832 | 2496x1664 | 3744x2496 | 4992x3328 |
| 21:9 | 1568x672 | 3136x1344 | 4704x2016 | 6272x2688 |

### 请求示例（文生图，2K/16:9）

```bash
curl https://api.agnes-ai.cn/v1/images/generations \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-image-2.1-flash",
    "prompt": "A cinematic product hero image, clean lighting, high detail",
    "size": "2K",
    "ratio": "16:9",
    "extra_body": { "response_format": "url" }
  }'
```

### 请求示例（图生图 / 多图合成）

```json
{
  "model": "agnes-image-2.0-flash",
  "prompt": "Transform the scene into a rain-soaked cyberpunk night while preserving the original composition",
  "size": "1024x768",
  "extra_body": {
    "image": ["https://example.com/input.png"],
    "response_format": "url"
  }
}
```

### 响应

```json
{
  "created": 1780000000,
  "data": [
    { "url": "https://storage.googleapis.com/agnes-aigc/xxx.png", "b64_json": null, "revised_prompt": null }
  ]
}
```

取图路径：`data[0].url` 或 `data[0].b64_json`。

> ⚠️ **国内网络实测**：响应中的 `url` 托管在 `storage.googleapis.com`，国内无法下载。
> 请务必使用 Base64 输出：文生图传 `return_base64: true`，图生图传 `extra_body.response_format: "b64_json"`。

---

## 视频生成（异步任务）

### 创建任务

```
POST https://api.agnes-ai.cn/v1/videos
```

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `model` | string | 是 | `agnes-video-v2.0` |
| `prompt` | string | 是 | 视频内容描述 |
| `image` | string | 否 | 图生视频的输入图片 URL |
| `mode` | string | 否 | 生成模式，如 `ti2vid` 或 `keyframes` |
| `width` / `height` | int | 否 | 默认 1152x768，自动映射到 480p/720p/1080p 标准档位 |
| `num_frames` | int | 否 | 必须 ≤ 441 且遵循 **8n+1** 规则 |
| `frame_rate` | number | 否 | 1–60，默认建议 24 |
| `num_inference_steps` | int | 否 | 推理步数 |
| `seed` | int | 否 | 随机种子，可复现结果 |
| `negative_prompt` | string | 否 | 反向提示词 |
| `extra_body.image` | array | 否 | 关键帧模式下的输入图片 URL 数组 |
| `extra_body.mode` | string | 否 | 附加模式，如 `keyframes` |

**时长公式**：`seconds = num_frames / frame_rate`

| 目标时长 | 推荐参数 |
| --- | --- |
| ~3 秒 | num_frames: 81, frame_rate: 24 |
| ~5 秒 | num_frames: 121, frame_rate: 24 |
| ~10 秒 | num_frames: 241, frame_rate: 24 |
| ~18 秒（上限） | num_frames: 441, frame_rate: 24 |

### 创建任务响应

```json
{
  "id": "task_xxx", "task_id": "task_xxx", "video_id": "video_xxx",
  "object": "video", "model": "agnes-video-v2.0",
  "status": "queued", "progress": 0,
  "created_at": 1780457477, "seconds": "10.0", "size": "1280x768"
}
```

### 获取结果（推荐：video_id）

```
GET https://api.agnes-ai.cn/agnesapi?video_id=<VIDEO_ID>
```

兼容旧版：`GET https://api.agnes-ai.cn/v1/videos/<TASK_ID>`

**任务状态**：`queued` → `in_progress` → `completed` / `failed`

**完成响应**：最终视频 URL 在 `metadata.url`；`metadata.size_mapping` 记录尺寸标准化信息。

```json
{
  "id": "task_xxx", "video_id": "video_xxx", "status": "completed", "progress": 100,
  "seconds": "5.0", "size": "832x448",
  "metadata": {
    "size_mapping": { "adjusted": true, "resolution": "480p", "ratio": "16:9", "width": 832, "height": 448 },
    "url": "https://platform-outputs.agnes-ai.space/videos/agnes-video-v2.0/task_xxx.mp4"
  }
}
```

---

## RPM 限制与配额（公开参考值，2026-06）

| 模型 | 免费用户 | 企业认证 | Token Plan |
| --- | --- | --- | --- |
| 文本 | 30 RPM | 60 RPM | 1000 RPM |
| 图像 1K | 30 RPM | 60 RPM | 120 RPM |
| 图像 2K | 20 RPM | 40 RPM | 120 RPM |
| 图像 3K/4K | 1-2 RPM | 1-2 RPM | 1-2 RPM |
| 视频 | 2 RPM（实际 1） | 2 RPM | 6 RPM（实际 5） |

Token Plan 配额：图像每天 4,000 张；视频每天 500 秒。同类型多把 key 共享同一个限制池。

## 常见错误码

| 状态码 | 含义 |
| --- | --- |
| 400 | 请求参数错误（检查 size/ratio/num_frames） |
| 401 | 未授权（检查 API Key） |
| 402 | 余额/配额不足 |
| 404 | 任务或视频未找到 |
| 429 | 触发 RPM 限制，等一分钟重试 |
| 500 / 503 | 服务器错误/繁忙，稍后重试 |

## 定价（当前）

图像 $0/张（标准价 $0.003/张）；视频 $0/秒（标准价 $0.005/秒）。
