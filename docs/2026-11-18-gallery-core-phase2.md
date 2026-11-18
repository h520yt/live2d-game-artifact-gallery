# 多游戏展示柜 · 第二阶段重构记录（2026-11-18）

## 已经落地的范围

本次在已有 `refactor/gallery-core-20261118` 分支上继续改造，
不移动/删除本地版权素材，不重写四款游戏的渲染器，也不合并到 `main`。

### 一、所有精选批次统一配置

`azur_lane/config/curated_collections.json` 现在包含：

| 批次 | 条目 | ID 策略 |
|---|---:|---|
| 第二批 | 10 | 固定历史 skin_id，保持原有档次字段 |
| 第三批 | 12 | 固定历史 skin_id |
| 第四批 | 12 | 固定历史 skin_id；保留双模型变体验收 |
| 第五批 | 20 | 运行时元数据映射；歧义严格报错 |
| 第六批 | 20 | 运行时元数据映射；允许未知 ID 下载原始资源 |

合计 74 个批次候选条目，不代表 74 个独立角色，也不代表全部下载成功。
第 2`4 批由 `gallery_core.collections.load_skin_batch` 读取；
第 5`6 批继续由 `load_batch_candidates` 读取并动态映射 skin ID。

原命令保持不变：

```powershell
python azur_lane/scripts/install_batch2.py --plan
python azur_lane/scripts/install_batch3.py --plan
python azur_lane/scripts/install_batch4.py --plan
python azur_lane/scripts/install_batch5.py --plan
python azur_lane/scripts/install_batch6.py --plan
```

### 二、下载/缓存基础设施初步复用

`gallery_core/storage.py` 提供：

- `file_ready`：非空文件、可选大小校验、可选流式 MD5 校验
- `atomic_write_bytes`：预先校验、同目录临时文件、fsync、原子替换、失败清理

已接入：

- **碧蓝航线**：安装器的 AssetBundle MD5 验证调用公用 `file_ready`
- **棕色尘埃2**：下载完成后用 `atomic_write_bytes` 替换原本的临时写入，保留现有 URL 白名单与重试方式
- **NIKKE**：atlas 下载写入使用公用原子写入；非空本地缓存判断统一复用

**明确限制：** 本阶段只把跨游戏真正相同的存储/校验操作抽取出来；
各游戏远程传输的鉴权、限流、代理、CDN、Spine 格式和 Unity AssetBundle
逻辑并没有被强行统一。NIKKE 的流式骨骼/贴图下载保持原有实现。

### 三、统一前端目录

新增 `gallery/index.html`、`gallery/styles.css`、`gallery/app.js`：

- 按游戏、角色/皮肤关键词、资源 ID、动画格式和已标注标签筛选
- 根据本地可选的核验报告显示入口文件状态
- 本地浏览器收藏；分页加载；静态预览图在本地缺失时正常降级
- 所有 HTML 数据均使用 DOM `textContent` 赋值，不执行资源元数据里的 HTML
- 点击「进入游戏查看器」进入该游戏现有操作台；**不会假装已自动定位或播放指定皮肤**

根目录 `index.html` 新增入口，原四张游戏卡片和 URL 保留。

## 推荐使用方式（Windows，项目根目录）

```powershell
git fetch origin
git switch refactor/gallery-core-20261118
git pull --ff-only origin refactor/gallery-core-20261118

# 自动构建索引、核查文件并启动仅本机可访问的展柜服务
python scripts/gallery.py serve --port 8000
```

浏览器访问：
- 游戏主页：`http://127.0.0.1:8000/`
- 跨游戏资源目录：`http://127.0.0.1:8000/gallery/`

`serve` 只监听 `127.0.0.1`，不需要额外前端依赖，也不会下载素材。
如果在服务运行期间新增了游戏资源，重新运行索引命令或重启服务即可刷新：

```powershell
python scripts/gallery.py sync-index
python scripts/gallery.py verify
```

如果端口占用，修改 `--port` 即可。按 `Ctrl+C` 停止本地服务。

## 回归与验收范围

自动化流水线增加：

- 原有四游戏清单生成索引
- 5 个批次 JSON 数量、顺序、ID 验证
- 原子写入成功/失败场景与 MD5 校验
- 第二、三、四批 `--help` 命令调用兼容性
- 浏览器 JavaScript `node --check` 语法验证
- 原有碧蓝航线和棕色尘埃2测试

需要在 Windows 本地进一步人工验收：

1. 原四个专属游戏查看器都能打开，并可播放原来支持的模型动作。
2. 已存在资源无需重复下载；本地 `verify` 状态与实际资源一致。
3. 点击统一目录的游戏操作台后，使用资源 ID 搜索目标皮肤。
4. 仅在有完整实际资源时，验证特殊动作、双形态、前景隐藏和独立互动。

**不要把自动化通过误解成**全部原画/骨骼/动作/互动完整；跨游戏统一目录当前只负责索引、静态缩略图和导航，底层各渲染器仍独立维护。

## 下一步技术债

- 完善统一资源的数据标准（一个角色多皮肤、多姿态、多动作、场景审核状态）。
- 将其余下载逻辑接入可插拔传输接口，补可靠的失败/恢复报告。
- 统一动画控制器 API，逐个接入专属查看器，保留游戏特有动作与交互。
- 在不破坏现有动作播放前提下，支持「从统一目录一键进入并选中皮肤」。

