# NIKKE：原版角色、皮肤与场景还原

核心原则：**只展示经核对属于当前角色/皮肤的原版场景。找不到正确关联，就展示透明 Spine 模型。绝不自动选择其它游戏场景补背景。**

NIKKE 的角色资源是 Spine 骨骼（skel/atlas/PNG），普通立绘与 Burst、Lobby Wallpaper 大厅动态壁纸属于不同资源链，不能把“剧情背景图库”当作“皮肤专属背景库”。

## 已支持

- 独立角色、换装 Spine 模型，包含 fb / cover / aim 姿态和动作切换。
- 透明模型帧导出与静态立绘。
- **经核实的关联**：仅当 manifest 中有已确认的场景，且场景所需素材已安装时才显示场景入口。
- **无关联时**：不显示场景入口、不提供随机选背景或任意导入、不显示旧版错误拼接预览。
- 高级皮肤原版 Lobby / Burst 的完整前后景、特效和镜头动态 **仍待独立提取**。

## Windows 本地操作

在项目根目录运行：

~~~powershell
git pull origin main
python nikke/scripts/install_skins.py --plan
python nikke/scripts/install_skins.py
python nikke/scripts/gen_nikke_manifest.py
python -m http.server 8000
~~~

打开 http://127.0.0.1:8000/nikke/viewer/ ，优先浏览已经装好的独立皮肤模型。

如需透明静态角色图，先启动上述 HTTP 服务，再在第二个终端执行：

~~~powershell
npm install --no-save playwright
npx playwright install chromium
node nikke/scripts/render_art.mjs --all
python nikke/scripts/gen_nikke_manifest.py
~~~

## 原版背景匹配规则

1. 首先获得该皮肤对应的游戏内 Lobby/Burst 画面与**原始资源标识**。
2. 必须核实皮肤资源 ID 与 Lobby、Burst、Prefab 或场景配置的关联。
3. 若是只有一张确定匹配的静态背景，可建立“已核实静态底图”配对，但不声称还原了整个动态演出。
4. 如果原版场景包含独立的动画、前景、遮挡、特效、滤镜或镜头，必须逐层还原才能称为完整原版场景。
5. 没有可信证据时保持原样，不产生背景配对。

已确认的静态底图绑定存于 nikke/scene_bindings.json。数据格式如下，**以下全部是占位文字，不能直接作为已确认资源使用**：

~~~json
{
  "cNNN_XX": {
    "background": "核实后真实存在的背景图片.png",
    "source_asset": "原始 Unity bundle / prefab / 场景配置的精确标识",
    "evidence": "可以追溯皮肤 ID 与场景配对的核实记录",
    "confirmed": true
  }
}
~~~

背景图片还必须真实存在于 nikke/data/backgrounds 才会进入 manifest。
当前 scene_bindings.json 仍为空，**目前尚未确认任何皮肤的原版背景配对**。
不能为了让界面显示背景而伪造 source_asset 或 evidence。

仅对上述已核实的配对才能运行：

~~~powershell
python nikke/scripts/gen_nikke_manifest.py
python nikke/scripts/render_scene_previews.py --all --plan
python nikke/scripts/render_scene_previews.py --all
python -m unittest discover -s nikke/tests -v
~~~

旧版随机合成的 scene_preview.webp 即使仍在硬盘中，也不会被当作官方场景显示。
新预览必须同时有 scene_preview.meta.json，且其中的背景文件名及原始资源标识与绑定一致。

## 普通背景图库与高级动画

之前导入的 Nikke-db 341 张普通游戏背景及其地点索引，只能用来查询素材或供核实，
**不再用于自动给所有皮肤套背景**。
已有 install_backgrounds.py 可作为本地素材勘察工具，不代表这些背景与任何角色有关。

下一步的重点是从 NIKKE 游戏资源中的 Lobby Wallpaper、Burst Cutscene、
EventScene 等真正带有角色、背景、效果层的素材入手。
本地 UnityFS 扫描只能读取明文资源，遇到 NKAB 加密包会跳过；
若无法找到某套皮肤的原始演出，不可拿无关背景顶替。

所有游戏美术资源仅用于个人本地研究、预览，不随 Git 源码分发。


## 原始动态场景候选核查

为直接寻找游戏里的 Lobby Wallpaper / Burst 演出，新增**只读资源核查脚本**。
它不自动将任何素材判定为官方配对，绝不修改现有皮肤场景绑定。

先从你本机已提取的资料里定位：

~~~powershell
python nikke/scripts/audit_original_scenes.py --from-data
~~~

若本地有 NIKKE 客户端缓存，可限定 00/01 两桶扫描明文 UnityFS：

~~~powershell
python nikke/scripts/audit_original_scenes.py --scan-cache --cache-root "Q:\NIKKE_Assets" --buckets 00 01 --max-bundles 200
~~~

核查结果在 nikke/data/_original_scene_candidates.json，其中包含原始对象名、
素材类型、客户端包位置、可能的角色 ID 提示，所有条目的 verified 均为 false。
**名字中出现角色 ID 不代表已经确认这就是该皮肤的场景。**
只有进一步核对出原版对应关系并提取齐全场景资源后，才允许将它接入展示柜。

本脚本不会解密 NKAB 或跳过游戏权限，也不会上传素材。
