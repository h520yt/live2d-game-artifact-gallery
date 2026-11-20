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

## 5. 角色换装模型与完整场景（2026-11-20）

NIKKE 的角色换装通常是独立 Spine 资源，例如 `c090` 和 `c090_02`，
不能把一个角色的骨骼文件与另一个皮肤的 png 图集强行互换。

本项目增加了“同角色皮肤切换”，仅在本地已经存在两套以上同家族模型时显示。
模型仍保留完整的 fb / cover / aim 姿态和动作，切换时会销毁旧 Spine Player 再加载新资源，
不建立新的首页分类。

**补齐现有精选角色的其他皮肤（在项目根目录执行）：**

```powershell
git pull origin main
python nikke/scripts/install_skins.py --plan
python nikke/scripts/install_skins.py
python -m unittest discover -s nikke/tests -v
```

也支持仅安装某个角色家族的皮肤：

```powershell
python nikke/scripts/install_skins.py --base c090 c810 --plan
python nikke/scripts/install_skins.py --base c090 c810
```

`--all-indexed` 扩大为 Nikke-db 索引中全部皮肤，**没有人工外观审核**，不作为默认操作。
这些命令只会查到上游 `l2d.json` 已列出的换装，**不是 NIKKE 全皮肤的完整目录**；
下载失败、索引缺项或后续新增皮肤需继续补来源。

### 背景与专属大厅演出的区别

1. **普通大厅／剧情背景**：背景本身通常是独立的图片资源；可按本文第 3 节放进
   `nikke/data/backgrounds/` 供任意 Spine 角色选择。这属于“自选组合”，不能标为官方配套皮肤。
2. **高级抽奖皮肤的 Burst／Lobby 演出**：可能是独立的 `eventscene`、`skillcut`、
   `livewallpaperprefabs` 等 Unity 资源，常包含自己的角色动作、背景、遮罩或特效层。
   它们不等于常规 `fb` 模型的附加 png，不能只凭同角色 ID 推断配对。
3. **当前状态**：角色模型换装切换已接入；旧版背景图库继续可用，
   但**官方专属场景的自动提取、正确配对和多层还原尚未完成**。不能声称全部完整场景已支持。

官方场景匹配需要先取得原始场景包或可信资产清单，验证 `ID → 场景资源 → 背景层／前景层`
关系，再在现有展示器中还原。不能把不相关的背景随意拼成“原版场景”。

## 6. 场景自动导入与人物背景合成（2026-11-20）

已加入 Nikke-db 的 [341 项背景索引](https://github.com/Nikke-db/nikke-db-vue/blob/main/src/utils/json/backgroundImages.json)
和 [30 个地点映射](https://github.com/Nikke-db/nikke-db-vue/blob/main/src/utils/json/locationBackgroundMappings.json)。
这些 JSON 仅包含文件名，不含背景原图；可从其 [Background Image Pack 入口](https://github.com/Nikke-db/nikke-db-vue/blob/main/src/components/common/Spine/Tools/BackgroundImagePack.vue)
取得供个人本地查看的背景素材包。

在仓库根目录执行，替换为你实际下载的 ZIP 或已解压目录：

~~~powershell
git pull origin main
python nikke/scripts/install_backgrounds.py --source "D:\Downloads\NIKKE-backgrounds.zip" --plan
python nikke/scripts/install_backgrounds.py --source "D:\Downloads\NIKKE-backgrounds.zip"
~~~

可使用 --force 覆盖已安装背景。脚本只导入索引中有的图片，且校验文件内容；
输出到 Git 忽略的 nikke/data/backgrounds，不将游戏原图提交仓库。
此外可以尝试从客户端的明文 UnityFS 缓存中提取图片（会跳过 NKAB）：

~~~powershell
python nikke/scripts/install_backgrounds.py --scan-cache --cache-root "Q:\NIKKE_Assets" --max-bundles 200 --plan
python nikke/scripts/install_backgrounds.py --scan-cache --cache-root "Q:\NIKKE_Assets" --buckets 00 01
~~~

背景安装后，打开 NIKKE 角色时默认显示实时 Spine＋背景，
没有背景则自动退回透明模型。背景支持按地点切换和保存皮肤偏好。

如需列表卡片显示完整人物＋背景，先启动本地 Web 服务：

~~~powershell
python -m http.server 8000
~~~

再打开第二个终端，在仓库根目录执行：

~~~powershell
python nikke/scripts/install_skins.py
npm install --no-save playwright
npx playwright install chromium
node nikke/scripts/render_art.mjs --all
python nikke/scripts/render_scene_previews.py --all
python nikke/scripts/gen_nikke_manifest.py
python -m unittest discover -s nikke/tests -v
~~~

进入 http://127.0.0.1:8000/nikke/viewer/ 查看。卡片采用本地生成的静态合成预览，
点击后仍为真实 Spine 动画。缺透明角色图时打印缺失原因并保留旧卡片封面。

**不要把一般背景组合误认为皮肤专属场景。** nikke/scene_bindings.json 目前为空，
以后仅接受有 evidence 核验依据、且所引用背景真实存在的绑定。
高级皮肤的 Burst / Live Wallpaper 原版动态场景（场景节点、特效、前后景）
仍需另行提取与核对，尚未完成完整还原。
