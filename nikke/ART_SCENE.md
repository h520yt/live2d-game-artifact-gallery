# NIKKE 原画 / 动态 / 场景展示

本项目的原始角色资源是 Spine 2D（骨骼 `.skel`、图集 `.atlas` 和贴图 `.png`）。**图集不是可直接显示的完整人物原画**。

现在的 NIKKE 查看器有三种模式：

- **原画 / 静态**：有独立静态图时优先显示它；否则自动从当前 Spine 姿态渲染静态透明图。这种渲染图不是官方单独发布的原画。
- **动态模型**：使用既有 Spine 4.0 / 4.1 加载逻辑、姿态和动画列表，保留透明人物背景。
- **场景合成**：Spine 动画叠加用户导入的背景（并非该皮肤的官方配对背景）。可以导出当前帧的合成 PNG。

## 1. 获取 Spine 与生成 manifest

在仓库根目录执行：

```powershell
python nikke/scripts/fetch_nikke.py c272_01 c202_01 c090_02 c200_01 c352_01 c112_01
python nikke/scripts/gen_nikke_manifest.py
python -m http.server 8000
```

浏览器访问：`http://127.0.0.1:8000/nikke/viewer/`。

## 2. 静态原画和透明 Spine 渲染图

如果你有**单独取得的原画图片**，放到 `nikke/data/<角色ID>/art.png`（也支持 `art.jpg` / `art.webp`），例如：

```text
nikke/data/c272_01/art.png
```

如果没有，查看器会从 Spine 渲染一帧；也可以批量生成高清静态 PNG：

```powershell
# 依赖 Playwright 和 Chromium：若未安装
npm install --no-save playwright
npx playwright install chromium

# 先在另一个终端运行 python -m http.server 8000
node nikke/scripts/render_art.mjs c272_01 c202_01 c090_02 c200_01 c352_01 c112_01

# 或全部已有 fb 角色（可能需要很长时间）
node nikke/scripts/render_art.mjs --all

python nikke/scripts/gen_nikke_manifest.py
```

渲染结果存为 `nikke/data/<角色ID>/art_render.png`；已有 `art.png` 优先于 `art_render.png`。脚本默认跳过已有图片，可用 `--force` 强制重新生成 `art_render.png`（不会覆盖 `art.png`）。

批量脚本默认使用 1440×1900 浏览器视口、2 倍设备像素比，**最终分辨率取决于 Spine 渲染画面与裁剪尺寸，不等于原生独立原画**。如果模型因资源缺失加载失败，脚本会记录失败，不会生成虚假空图。

## 3. 补充背景图库

场景图片版权属于 NIKKE 游戏方；仓库**不附带第三方声称拥有的 339 张背景图**。将你有权用于个人查看的背景图片（png / jpg / jpeg / webp）放进：

```text
nikke/data/backgrounds/
  ark-office.png
  beach.webp
```

可选在 `nikke/backgrounds.json` 为文件配置显示名和分类（key 必须等于真实文件名），例如：

```json
{
  "ark-office.png": {
    "name": "指挥官办公室",
    "category": "方舟"
  },
  "beach.webp": {
    "name": "海边",
    "category": "夏日"
  }
}
```

然后执行：

```powershell
python nikke/scripts/gen_nikke_manifest.py
```

只收录磁盘上确实存在且非空的图片，生成到 `nikke/viewer/nikke_manifest.json` 的 `backgrounds` 数组。进入任意角色，切到「场景合成」即可选择背景。也可以点「导入背景」临时加载本机图片；临时导入只在当前页面有效，不会保存到磁盘。

## 4. 导出 PNG

在三种模式中点击「导出 PNG」：

- **原画 / 静态**：导出完整静态图原分辨率（或 Spine 透明渲染帧）。
- **动态模型**：按当前动作画面导出透明、裁边的 PNG。
- **场景合成**：按当前舞台大小将背景与 Spine 人物叠加到 PNG。没选背景时透明。

目录 `nikke/data/` 已被 .gitignore 忽略；不会把受版权保护的大型图片直接提交到 Git。

**注意：** 不是每个角色都有独立官方原画文件，也不是每套皮肤都有专属背景；本工具明确区分「官方独立原图」与「Spine 渲染帧」。原画仅根据本地文件是否存在决定显示，无法自动核实图片出处。
