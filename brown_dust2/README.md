# 棕色尘埃2 · Prestige Skin 尊爵皮肤首批

本模块接入最高规格的 **Prestige Skin** 外观系列，并非普通五星战斗服装。首批共六款：尤丝缇亚 Hot Summer Dream、泰瑞丝 Milky Bikini、洁尼斯 Stranger Bunny、莉贝尔塔 Hedonist、莎赫拉查德 Deliberate Ace、尤里 Forever Mascot。

资源目录来自 myssal/Brown-Dust-2-Asset；前四款角色、技能、互动模型路径有明确映射，后两款角色和技能路径已确认，互动场景尚未建立对应关系，因此不会虚构对应动作。

## Windows PowerShell 运行

1. 在项目根目录先执行 git pull origin main。
2. 检查资源计划：python brown_dust2/scripts/install_prestige.py --plan
3. 下载本批：python brown_dust2/scripts/install_prestige.py
4. 离线核验：python brown_dust2/scripts/install_prestige.py --verify
5. 启动服务：python -m http.server 8000

打开 http://127.0.0.1:8000/brown_dust2/viewer/index.html 。

支持仅安装某款：python brown_dust2/scripts/install_prestige.py --only justia-hot-summer-dream（其它 ID 见 curated_prestige.json）。下载中断可重跑，文件大小匹配时会跳过。GitHub API 403 限流可在环境变量 GITHUB_TOKEN 中配置令牌，勿把令牌写入代码。

## 展示范围

* Spine 4.1 动态角色、技能演出、已定位的互动动画，支持动作选择、切换和 PNG 当前帧导出。
* 完整性检查要求 skel、atlas、atlas 引用的全部 PNG 均真实存在，缺一不进入网页已安装清单。
* 资源只下载到 brown_dust2/data/，代码仓库不追踪游戏美术文件；版权归游戏权利人所有。
* 技能动画的附加背景、复杂分层、音频、秘密剧情及全部游戏触摸逻辑暂未完整还原。PNG 是当前画布截图，不保证等价于官方静态原画。

测试：python -m unittest discover -s brown_dust2/tests -v
