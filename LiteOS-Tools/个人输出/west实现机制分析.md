## zephyr&west介绍

Zephyr 采用多仓库结构，通过 west 工具统一管理。除了主仓库，还有：
- hal_xxx：各芯片厂商的硬件抽象层（HAL）。
- mcuboot：默认的安全 Bootloader。
- modules/：第三方库（如 mbedTLS、LVGL、zcbor 等）。
- sdk-ng：Zephyr 官方 SDK（交叉编译工具链）。

Zephyr 项目开发一般使用west进行项目构建和管理，west的作用如下：
- 多仓库管理：Zephyr 本身依赖多个 Git 仓库（内核、驱动、HAL、测试、工具链支持等），west 负责统一拉取和同步。
- 构建前端：封装了 CMake/Ninja 的调用，简化应用构建、烧录等操作。
- 可扩展性：支持插件机制，可以编写自定义的 west 子命令。

### west内置命令

#### 多仓库管理

| 命令            | 功能                                        |
| ------------- | ----------------------------------------- |
| west init     | 初始化 west workspace，克隆 manifest 仓库         |
| west update   | 按 west.yml manifest 拉取/更新所有项目到指定 revision |
| west list     | 列出 manifest 中的项目                          |
| west manifest | 解析、导入、冻结、校验 manifest（--freeze 导出锁定版本）     |
| west compare  | 比较本地项目与 manifest 约定的差异                    |
| west diff     | 所有项目执行 git diff                           |
| west status   | 所有项目执行 git status                         |
| west forall   | 在所有项目上执行任意 shell 命令                       |
| west grep     | 跨所有项目的内容搜索                                |

#### 其他
	help、config（分层配置管理：system/user/workspace）、topdir、self-update（隐藏命令，自更新 west）

#### 核心能力

- manifest 机制：west.yml 声式描述整个 Zephyr 多仓库结构（支持 import、groups、filter、blob、allowlist/blocklist）
- 扩展机制：任意项目可注册 west-commands.yml 注入自定义命令
- Python API：west.manifest、west.configuration 可作为库使用


### zephyr扩展命令

**Zephyr 通过 scripts/west-commands.yml 注册这些命令**

#### 开发构建
- west build — 编译应用（封装 CMake/ninja）
- west twister — 测试框架 wrapper
- west sign — 为 bootloader（如 MCUboot）链式加载签名镜像
- west simulate — 板级仿真
#### 烧录调试
- west flash — 烧录并运行
- west debug / debugserver / attach — 交互调试 / 启动 GDB server / 附加调试
- west rtt — SEGGER RTT 终端
- west reset — 复位板子
#### 板卡与元信息
- west boards / west shields — 列出支持的板子和扩展板
- west bindesc — 解析二进制描述符（构建元数据）
- west spdx — 生成 SPDX SBOM
#### 环境/模块管理
- west sdk — 管理 Zephyr SDK
- west packages — 管理主机依赖包
- west zephyr-export — 导出 CMake config package
- west blobs — 管理二进制 blob（如 firmware）
- west patch — 管理模块补丁
#### 工具
- west completion — shell 补全脚本
- west gtags — 生成 GNU global 标签



典型工作流：west update → west boards → west build -b （board）> → west flash → west debug。


## West v1.4.0 源码深度解析


west (console script)
 └─ src/west/__main__.py → main()                    
     └─ WestApp.run(argv)                         
         ├─ ① parse_early_args(argv)                 # 手写解析 -h/-V/-v/-q/-z 和命令名
         ├─ ② setup_west_logging / colorama.init()
         ├─ ③ west_topdir()                          # util.py 向上找 .west 目录
         ├─ ④ Configuration(topdir)                  # 三层配置
         ├─ ⑤ load_manifest()                        # 失败不崩溃，存入 self.mle 延迟处理
         ├─ ⑥ load_extension_specs()                 # 扫描 west-commands.yml
         ├─ ⑦ load_aliases()                         # alias.* 配置
         ├─ ⑧ setup_parsers()                        # argparse + 扩展桩解析器
         └─ ⑨ run_command()                          # 别名展开 → 分发 → 异常兜底

