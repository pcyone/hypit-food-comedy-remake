# hypit-food-comedy-remake


https://github.com/user-attachments/assets/97aa547e-b763-4578-b74f-4c33548c711f



https://github.com/user-attachments/assets/ce5e134d-2887-4b87-92a2-3af79bab7656



用 Hypit 与 HypiHub 复刻约 13 秒餐饮催菜短剧的 Codex Skill。

这个 Skill 固化了一个餐饮短剧工作流：顾客催菜，老板误解成给菜“加油”，最后对着菜品连续喊“四遍加油”直到片尾。它适合把爆款参考视频里的剧情结构、镜头节奏和喜剧关系，替换成本店人物、餐厅场景和菜品。

当前默认案例：

- 顾客女主：歪博云
- 老板男主：克托炎
- 菜品：客家酿豆腐
- 场景：用户餐厅实拍图
- 成片规格：约 13 秒，9:16，720x1280，30fps，H.264/AAC MP4
- 字幕样式：顶部居中白字，轻阴影，无黑底
- 关键桥段：老板连续四遍喊“豆腐加油”直到片尾

“加油”是给菜鼓劲，不是往菜里倒食用油。

## 安装

把仓库放到 Codex Skills 目录中：

```sh
mkdir -p ~/.codex/skills
git clone https://github.com/<your-name>/hypit-food-comedy-remake.git ~/.codex/skills/hypit-food-comedy-remake
```

安装后，在 Codex 中可以这样调用：

```text
使用 $hypit-food-comedy-remake，沿用歪博云、克托炎和餐厅，菜品换成盐焗鸡，复刻催菜加油短剧。
```

## 依赖

使用前需要本机已有：

- Codex 本地环境
- Hypit Skill
- HypiHub / Hypit 可用账号
- Hypit 命令可运行
- ffmpeg 和 ffprobe
- Python 3
- Pillow

本 Skill 不会自动登录、充值、上传或生成。真正调用 Hypit / HypiHub 前，应先 check、plan、pricing，确认当前请求和费用。

## 三种工作模式

### 复用模式

用于恢复上次成片、打开预览、只改字幕、只改声音或重新合成已有素材。

```sh
python3 scripts/prepare_project.py --output <新项目绝对目录> --mode reuse
```

复用模式不会为了取回已有视频再次调用云端生成。它会恢复 V3 成片、无字幕无声画面、完整配音母带、字幕时间轴和预览素材。

### 新作模式

用于换菜品、换角色、换餐厅、换参考视频，重新制作一条同款短剧。

```sh
python3 scripts/prepare_project.py --output <新项目绝对目录> --mode new
```

新菜名不能只改字幕，必须同步修改食物参考、画面描述、台词、字幕、配音和验收标准。

### 返修模式

用于处理已有项目的具体反馈，例如：

- 尾部没声音
- 配音和原音重叠
- 字幕位置不对
- 声音不够激情
- 口型节奏不贴
- 人物脸型或身份不稳

返修时保留旧版本，只处理反馈涉及的段落，避免覆盖可用成果。

## 核心规则

- 原参考视频只提供剧情、镜头和节奏，不保留原真人、原包子、原街边摊。
- 角色图提供身份，餐厅图提供空间，菜品素材提供食物。
- 新菜品不能只改在字幕里。
- 最终视频必须彻底隔离原音，只挂一条完整配音母带。
- 当前同款必须四遍喊到片尾，最后一遍“油”不能被截断。
- “有激情”需要重新表演，单纯放大旧声音不算重配。
- 时间对齐不等于逐字口型重建；需要真正修口型时应重新生成说话画面。
- 机器检查只能证明硬指标，不能代替人工听审和看口型。

## 本地合成

```sh
python3 scripts/finalize.py \
  --video <无字幕画面.mp4> \
  --voice <完整母带.wav> \
  --captions <字幕时间轴.json> \
  --output <新版本成片.mp4>
```

这个脚本会移除画面原音、添加顶部白字阴影字幕，并挂载唯一完整配音母带。

## 验收

```sh
python3 scripts/verify_delivery.py \
  --video <新版本成片.mp4> \
  --duration 13 \
  --speech-through 12.9 \
  --min-final-second-active 0.55
```

默认检查：

- 完整解码
- 约 13 秒
- 720x1280
- 30fps
- H.264/AAC
- 单音轨
- 无双配音
- 尾部没有缺声
- 字幕无黑底

## 素材说明

公开仓库不包含当前同款案例的私有参考素材、V3 成片和本地复用媒体。仓库只保留流程、脚本、模板和占位目录。

公开使用时，请根据自己的项目放入人物、餐厅、菜品和参考片，并确认素材授权。完整私有案例包只保留在本机安装版中。

## 目录结构

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   ├── baseline-v3/
│   ├── project-template/
│   └── reference/
├── references/
│   ├── asset-manifest.json
│   ├── baseline.md
│   └── workflow.md
└── scripts/
    ├── finalize.py
    ├── prepare_project.py
    └── verify_delivery.py
```

## 常用调用

```text
使用 $hypit-food-comedy-remake，恢复上次催菜加油短剧预览。
```

```text
使用 $hypit-food-comedy-remake，沿用歪博云、克托炎和餐厅，菜品换成砂锅粥，复刻催菜加油短剧。
```

```text
使用 $hypit-food-comedy-remake，只返修 0:08 以后“豆腐加油”的配音，声音更有激情，节奏贴近原参考视频。
```

```text
使用 $hypit-food-comedy-remake，字幕改成顶部白字、轻阴影、无黑底，保留当前画面和声音。
```
