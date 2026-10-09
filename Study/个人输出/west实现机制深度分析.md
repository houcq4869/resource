
## zephyr&west

Zephyr 采用 多仓库结构，通过 west 工具统一管理。除了主仓库，还有：
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

多仓库管理（main.py:1204 BUILTIN_COMMAND_GROUPS）：

	
	
	
west manifest	
west compare	
west diff	
west status	
west forall	在所有项目上执行任意 shell 命令
west grep	跨所有项目的内容搜索

| 命令          | 功能                                        |
| ----------- | ----------------------------------------- |
| west init   | 初始化 west workspace，克隆 manifest 仓库         |
| west update | 按 west.yml manifest 拉取/更新所有项目到指定 revision |
| west list   | 列出 manifest 中的项目                          |
|             | 解析、导入、冻结、校验 manifest（--freeze 导出锁定版本）     |
|             | 比较本地项目与 manifest 约定的差异                    |
|             | 所有项目执行 git diff                           |
|             | 所有项目执行 git status                         |
|             |                                           |

其他：help、config（分层配置管理：system/user/workspace）、topdir、self-update（隐藏命令，自更新 west）
核心能力（不仅是命令）：
- manifest 机制：west.yml 声式描述整个 Zephyr 多仓库结构（支持 import、groups、filter、blob、allowlist/blocklist）
- 扩展机制：任意项目可注册 west-commands.yml 注入自定义命令
- Python API：west.manifest、west.configuration 可作为库使用


### zephyr扩展命令
