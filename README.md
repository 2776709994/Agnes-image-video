# Agnes AI 图像 & 视频生成 Skill

一个开箱即用的 WorkBuddy Skill，封装了 **Agnes AI 国内版 API** 的图像生成与视频生成能力。对 AI 助手说一句"帮我生成一张图 / 一段视频"即可自动完成调用、下载和交付。

- 官方文档：https://www.agnes-ai.cn/zh-Hans/docs/overview
- API 网关：`https://api.agnes-ai.cn/v1`（国内版，直连可用，无需代理）
- 协议：OpenAI 兼容

## 功能特性

| 能力 | 模型 | 说明 |
| --- | --- | --- |
| 文生图 | `agnes-image-2.1-flash`（默认） | 高信息密度、复杂构图优化；支持 1K–4K 档位 × 8 种宽高比 |
| 图生图 / 图像编辑 / 多图合成 | `agnes-image-2.1-flash`（默认） | 2.1 支持全部图像工作流；本地图片自动转 Data URI 上传。可选 `agnes-image-2.0-flash`（编辑榜 Top 20，用精确尺寸） |
| 文生视频 / 图生视频 | `agnes-video-v2.0` | 异步任务自动轮询；支持时长、分辨率、反向提示词、随机种子 |

- **自动选模型**：图像场景一律默认 `agnes-image-2.1-flash`，视频默认 `agnes-video-v2.0`；你点名模型时直接用你指定的（如图生图想用 2.0，说一声即可）
- **零依赖**：调用脚本只用 Python 3 标准库，不需要 pip install 任何东西
- **异步视频自动等待**：提交任务后自动轮询直到完成并下载 mp4

## 目录结构

```
agnes-ai/
├── SKILL.md              # Skill 定义（AI 助手读取的入口）
├── README.md             # 本文档
├── scripts/
│   └── generate.py       # 统一调用脚本（图像 + 视频）
└── references/
    └── api.md            # 完整 API 参考（端点、参数、错误码、限额）
```

## 安装

把整个文件夹复制到 WorkBuddy 的用户级 skills 目录：

- **Windows**: `C:\Users\<你的用户名>\.workbuddy\skills\agnes-ai`
- **macOS / Linux**: `~/.workbuddy/skills/agnes-ai`

重启或新开会话后，对 AI 说"用 Agnes 生成一张……"即可触发。

## 配置 API Key（必做）

本 skill **不包含 API Key**，每个人需要配置自己的 key（免费获取）：

1. 打开 https://platform.agnes-ai.cn/ 并登录
2. 进入 **API Key** 页面，创建并复制 key（`sk-` 开头）
3. 用以下**任一**方式配置：

```bash
# 方式一：环境变量（推荐）
export AGNES_API_KEY="sk-你的key"
# Windows PowerShell:  $env:AGNES_API_KEY="sk-你的key"

# 方式二：写入用户级 key 文件（脚本自动读取）
mkdir -p ~/.agnes-ai && echo -n "sk-你的key" > ~/.agnes-ai/api_key

# 方式三：写入 skill 内的 scripts/api_key（自包含，适合单机自用）
echo -n "sk-你的key" > scripts/api_key
```

脚本按 环境变量 → `~/.agnes-ai/api_key` → `scripts/api_key` 的顺序自动查找。

> ⚠️ **安全提醒**：key 是敏感凭证。如果你要转发/公开这个 skill，**切勿**把 `scripts/api_key` 一起发出去；泄露后请立即在控制台重置。

## 使用方法

### 方式一：自然语言（推荐，由 AI 助手自动处理）

```
用 Agnes 生成一张赛博朋克城市夜景，霓虹灯光，电影风格，16:9 横版
把这张照片转成水彩风格（附图片）
用 Agnes 生成一段 5 秒视频：一只猫在夕阳下的沙滩上奔跑，电影感
```

AI 会自动选模型、拼参数、调用脚本并把成品文件交付给你。想换模型直接说，例如"用 2.1 模型做图生图"。

### 方式二：命令行直接调用

```bash
# 文生图（默认 agnes-image-2.1-flash）
python3 scripts/generate.py image \
  --prompt "赛博朋克城市夜景，霓虹灯光，电影风格" \
  --size "2K" --ratio "16:9" \
  --output "city.png"

# 图生图（图像默认 agnes-image-2.1-flash）
python3 scripts/generate.py image \
  --prompt "转成水彩风格，保留原构图" \
  --image "photo.jpg" --size "1K" \
  --output "watercolor.png"

# 文生视频（默认 agnes-video-v2.0，自动轮询）
python3 scripts/generate.py video \
  --prompt "一只猫在夕阳下的沙滩上奔跑，电影感" \
  --duration 5 \
  --output "cat.mp4"
```

### 常用参数速查

**图像**

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--prompt` | 描述/编辑指令（必填） | — |
| `--size` | `1K`/`2K`/`3K`/`4K` 档位（2.1 模型推荐）或 `1024x768` 精确尺寸（2.0 模型） | `1K` |
| `--ratio` | `1:1` `16:9` `9:16` `4:3` `3:4` `2:3` `3:2` `21:9` | `1:1` |
| `--image` | 输入图片（图生图/多图合成），本地路径或 URL，可多张 | — |
| `--model` | 手动指定模型，覆盖默认推荐 | 按场景自动 |

**视频**

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--prompt` | 视频描述（必填） | — |
| `--duration` | 目标时长（秒），自动换算为合法帧数，最长约 18 秒 | `5` |
| `--image` | 图生视频的输入图片 | — |
| `--width` `--height` | 分辨率（自动映射到 480p/720p/1080p） | `1152x768` |
| `--frame-rate` | 帧率 1–60 | `24` |
| `--negative-prompt` | 反向提示词 | — |
| `--seed` | 随机种子，复现结果 | — |

## 切换默认模型（进阶）

### 临时切换（不修改任何文件）

- **对话里**：直接点名模型，例如"用 agnes-image-2.0-flash 做图生图"，AI 会用 `--model` 参数执行
- **命令行**：加 `--model` 参数覆盖当次调用

```bash
python3 scripts/generate.py image --prompt "..." --model "agnes-image-2.0-flash" --image in.png --size "1024x768" --output out.png
```

### 永久修改默认模型

默认模型定义在 `scripts/generate.py` 顶部的三个常量（约第 40 行），改值即生效：

```python
DEFAULT_IMAGE_MODEL = "agnes-image-2.1-flash"   # 图像默认（文生图/图生图/多图合成）
FALLBACK_IMAGE_MODEL = "agnes-image-2.0-flash"  # 图像备选（--model 指定时用）
DEFAULT_VIDEO_MODEL = "agnes-video-v2.0"        # 视频默认
```

修改时注意两点：

1. **尺寸写法要跟着模型走**：2.1 用档位（`1K`/`2K` + `--ratio`），2.0 用精确像素（`1024x768`）。若把图像默认改成 2.0，建议同时把 CLI 的 `--size` 默认值从 `1K` 改为 `1024x1024`。
2. **文档要同步**：`SKILL.md` 的"模型选择"表格是 AI 助手运行时读取的指引，只改脚本不改它，AI 仍会按旧文档描述行为。`README.md` 的"功能特性"表格也建议一并更新。

如果你把 skill 复制到了 WorkBuddy skills 目录，运行的是那份拷贝——改完记得同步覆盖过去。

## 限额说明（免费用户）

- 图像：1K 约 30 RPM、2K 约 20 RPM、3K/4K 仅 1–2 RPM
- 视频：约 1–2 RPM，**生成慢、排队久是正常现象**，请耐心等待脚本轮询
- 需要更高限额可在控制台订阅 Token Plan（图像每天 4,000 张、视频每天 500 秒）

## 故障排查

| 问题 | 处理 |
| --- | --- |
| `AGNES_API_KEY not found` | 按上文"配置 API Key"任一方式配置 |
| 401 Unauthorized | key 错误或已失效，去控制台重新创建 |
| 429 Too Many Requests | 触发 RPM 限制，等 1 分钟再试 |
| 400 Bad Request | 检查 size/ratio 写法；2.1 模型用档位（如 `2K`），2.0 模型用精确尺寸（如 `1024x768`） |
| 视频等很久 | 免费用户视频仅 1–2 RPM，正常；脚本最长等 10 分钟 |
| 想要 1920x1080 | 请求 `size=2K, ratio=16:9`（输出 2624x1472）再自行裁剪 |
| 图像 url 下载失败（10054/连接重置） | API 返回的图像 url 托管在谷歌存储，国内不可达。脚本已默认用 Base64 输出规避，请勿自行改回 url 模式 |
| 视频 url 下载失败 | 视频结果托管在 `platform-outputs.agnes-ai.space`，部分国内网络不可直连；可复制 url 到可访问的网络环境下载 |

完整 API 细节见 [references/api.md](references/api.md)。

## 许可与声明

- 本 skill 为对 Agnes AI 公开 API 的社区封装，与 Agnes AI 官方无隶属关系
- 生成内容的使用须遵守 [Agnes AI 服务条款](https://www.agnes-ai.cn/zh-Hans/docs/terms-of-service)
- 请勿在公开仓库中提交任何真实 API Key
