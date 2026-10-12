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

### 架构流程分析

west (console script)
 └─ src/west/__ main __ .py → main()                    
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


```python
# ============ 入口（main.py 1228 行的真实内容）============
def main():
    topdir    = 向上找 .west 目录()            # util.west_topdir，86 行小函数
    config    = 读三级配置文件(topdir)          # configuration.py
    manifest  = 解析 west.yml()                 # manifest.py ★大脑
    extensions = 扫描 west-commands.yml()       # 只登记名字，不加载模块！
    command   = 解析命令行()

    if command 在内置表里:
        内置表[command].run(topdir, manifest, config)
    else:
        extensions[command].加载模块并run(...)   # 此刻才 import

# ============ manifest.py 2784 行的真实内容 ============
def 解析 west.yml():
    数据 = yaml.safe_load(文件)
    pykwalify校验(数据, schema文件)             # 报错全是 MalformedManifest
    ctx = Ctx(projects={})                      # ★ 全局唯一的项目登记表

    解析本文件(数据, ctx)                        # 逐条 projects: 变成 Project
    处理 self: import:(数据, ctx)               # 递归 ↓
    处理 各项目的 import:(..., ctx)             # 递归 ↓

def 处理 import(子清单数据, ctx):
    child = ctx._replace(path_prefix=前缀拼接)   # 标量字段换新的一层
    解析 west.yml(子清单数据, child)             # ★ 递归调用！但 projects
                                                #   dict 还是同一个对象
def 解析本文件(数据, ctx):
    for 每个项目 in 数据['projects']:
        if 项目.name not in ctx.projects:       # ★ 先到先得
            ctx.projects[name] = 算url算path(项目)

# ============ project.py 2331 行的真实内容 ============
def west_update(项目):
    没克隆就 git init + remote add
    git fetch <url> <revision 或 refs/heads/*:refs/west/*>
    git update-ref refs/heads/manifest-rev <新sha> -m 'west update: ...'
    删掉 refs/west/*
    决定策略: 保留后代分支? / rebase? / checkout --detach <sha>   # 见实验D
    git submodule update ...

# ============ commands.py 721 行的真实内容 ============
class WestCommand:                # 所有命令（内置+扩展）的基类
    def run(self, args, topdir, manifest, config):
        self.config = config; self.manifest = manifest; self.topdir = topdir
        for hook in self.hooks: hook(self)       # 延迟的警告/错误在这里吐
        self.do_run(args)                        # ← 每个命令真正的逻辑
```

### 命令跟踪——west update

把整条执行链想象成你走进一栋大楼办事：
你说："我要办 update 业务"（敲 west update）
  → 门口保安室：看你是谁、要不要讲解耳机（第 2 讲：手搓解析器）
  → 查园区门牌：你属于哪个小区？（第 3 讲：找 .west）
  → 调档案：你的偏好设置（第 4 讲：读配置）
  → 查项目名录：这栋楼里有哪些仓（第 5 讲：解析 west.yml）
  → 查窗口名录：楼里有哪些额外服务（第 6 讲：扫描扩展）
  → 带你去对应窗口（第 9 讲：分发）
  → 窗口办事员领三样资料开工（第 10 讲：三件套注入）
  → 办事员干 update 的活（第 11-13 讲：git 编排）

#### 0. pyproject 入口 → WestApp()

- 敲下west update后，首先发生**包安装时的约定**

```toml
# pyproject.toml
[project.scripts]
west = "west.app.main:main"     # pip 装包时据此生成 ~/.local/bin/west
```

- ~/.local/bin/west：执行 `from west.app.main import main; main()`

```python
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import re
import sys
from west.app.main import main
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main())              
```

- 造一个应用对象，把命令行参数交给它。真正的逻辑在 WestApp 类里

```python
# main.py:1196-1199
def main(argv=None):
    # Create the WestApp instance and let it run.
    app = WestApp()
    app.run(argv or sys.argv[1:])
```

- WestApp.__ init __ ：整个west的状态清单，后续即给这些字段填值

```python
def __init__(self):
    self.topdir = None          # 工作区根    ← 第 2 步 west_topdir() 填
    self.config = None          # 三级配置    ← 第 3 步 Configuration() 填
    self.manifest = None        # 清单对象    ← 第 4 步 load_manifest() 填
    self.mle = None             # 清单加载失败的异常 ← 第 4 步失败时存，第 9 步引爆
    self.builtins = {}          # 命令名 → 内置命令实例 ← ★本步就填
    self.extensions = {}        # 扩展命令名 → spec  ← 第 5 步填
    self.aliases = {}           # 别名 → 命令实例    ← 第 6 步填
    self.builtin_groups = OrderedDict()   # 组名 → 命令列表（west help 分组显示用）
    self.extension_groups = OrderedDict() # 项目路径 → 扩展列表
    self.west_parser = None     # 主 parser   ← 第 7 步填
    self.subparser_gen = None   # 子命令生成器
    self.cmd = None             # 最终要执行的命令实例 ← 第 8 步选定
    self.queued_io = []         # 排队等待输出的消息 ← 第 9 步挂 hook
```

- 实例化 13 个命令对象

```python
# main.py:218-221
for group, classes in BUILTIN_COMMAND_GROUPS.items():
    lst = [cls() for cls in classes]                              # ① 全部 new 一遍
    self.builtins.update({command.name: command for command in lst})  # ② 存字典
    self.builtin_groups[group] = lst                              # ③ 存分组
# 数据源是文件末尾那张注册表（main.py:1204-1225）：
BUILTIN_COMMAND_GROUPS = {
    'built-in commands for managing git repositories': [
        Init, Update, List, ManifestCommand, Compare, Diff, Status, ForAll, Grep,
    ],
    'other built-in commands': [Help, Config, Topdir],
    None: [SelfUpdate],    # None 组 = 隐藏，不出现在 west help 里
}
```


```
回车  → ~/.local/bin/west（pip 按 \[project.scripts] 生成）
     → main()（main.py:1196，两行）
     → WestApp()：13 个命令对象就位，其余 13 个字段全是 None
     → app.run(\['update'])
```

#### 1. parse_early_args

argparse 要建一棵完整的命令树（west 支持哪些命令、每个命令有什么参数）。对 west 来说，这棵树有个麻烦：
想建完整的命令树
  ↓ 为什么？
树上必须包含"扩展命令"（west build / west flash ……这些不是 west 自带的）
  ↓ 它们从哪来？
从各项目的 west-commands.yml 里读 → 得先解析 west.yml（清单）
  ↓ west.yml 在哪？
写在 .west/config 里 → 得先找到 .west 目录（工作区）
  ↓ 可是！
用户可能敲的是 west -V（只想看版本号）
  ——他根本不在工作区里，也根本不需要什么命令树！

- 先扫一遍argv，只提取“在任何情况下都需要尽早知道”的信息，其余全部留给后面的 argparse

```python
# main.py:70-92
class EarlyArgs(NamedTuple):
    # We do some manual parsing of the command-line arguments before
    # delegating the hard parts to argparse. This extra work figures
    # out the command name, verbosity level, etc.
    #
    # This is necessary for:
    #   - nicer error-handling in situations where the command is an
    #     extension but we're not in a workspace
    #   - setting up log levels from the verbosity level

    help: bool                  # -h 是否出现
    version: bool               # -V 是否出现
    zephyr_base: Optional[str]  # -z 的值
    verbosity: int              # -v 加、-q 减，净计数
    command_name: Optional[str] # ★ 第一个非选项 token
    unexpected_arguments: list[str]  # 其他 - 开头的，先记账不报错
```

- 朴素状态机

```python
for arg in argv:
    if expecting_zephyr_base:          # 上一个是孤立的 -z，这个 token 是它的值
        zephyr_base = arg
    elif arg.startswith('-h'):  help = True; consume_more_args(arg[2:])
    elif arg.startswith('-V'):  version = True; consume_more_args(arg[2:])
    elif arg == '--version':    version = True
    elif arg.startswith('-v'):  verbosity += 1; consume_more_args(arg[2:])
    elif arg.startswith('-q'):  verbosity -= 1; consume_more_args(arg[2:])
    elif arg == '--verbose':    verbosity += 1
    elif arg == '--quiet':      verbosity -= 1
    elif arg.startswith('-z'):  # 三种形态：-z /path、-z=/path、-z/path
        ...
    elif arg.startswith('-'):   unexpected_arguments.append(arg)   # ★ 只记账
    else:
        command_name = arg      # ★★ 第一个不以 - 开头的 token = 命令名
        break                   # ★★ 后面的 token 全是命令自己的参数，与我无关
```

- run()：early_args 的四个消费者

```python
# main.py:235-250
early_args = parse_early_args(argv)

# ① 静音 pykwalify：校验库会把校验错误打到 ERROR 日志，
#    west 要自己控制报错文案（MalformedManifest 的格式），不能让库抢话筒
logging.getLogger('pykwalify').setLevel(logging.CRITICAL)

# ② ★ verbosity → west.manifest logger 的级别（:669-683）
#    >=2 → DEBUG，1 → INFO，0 → WARNING，-1 → ERROR
#    这一步在 load_manifest（第4步）之前！所以 -v 能看到清单解析日志
self.setup_west_logging(early_args.verbosity)

# ③ colorama.init()：Windows 下让 ANSI 颜色码生效；输出不是终端时自动剥色
colorama.init()

# ④ 接下来：self.topdir = west_topdir() 
```

```
app.run(\['update'])
  → parse_early_args(\['update'])          # 80 行 if-elif 状态机
  → EarlyArgs(help=F, version=F, zephyr_base=None,
              verbosity=0, command_name='update',   # ★ 本步最重要产物
              unexpected_arguments=[])
  → 静音 pykwalify / 按 verbosity 设日志级别 / colorama 初始化
  → 即将进入：west_topdir()
```

#### 2. west_topdir()

- west init 落地产物即
west-lab/                 ← 工作区根（topdir）
├── .west/                ← ★ 路标：它的存在本身就是"根在这里"的声明
│   └── config            ← 藏宝图，就 3 行（实验2 实测）：
│       \[manifest]
│       path = manifest   # 清单仓在根下的相对路径
│       file = west.yml   # 清单文件名
├── manifest/             ← 清单仓（west.yml 住这里）
├── lib/                  ← 项目仓（west update 克隆的）
└── app/


```python
# util.py:65-86
def west_topdir(start=None, fall_back=True):
    cur_dir = pathlib.Path(start or os.getcwd())   # ① 起点默认 cwd

    while True:
        if (cur_dir / WEST_DIR).is_dir():          # ② 探测：这里有 .west 吗
            return os.fspath(cur_dir)              #    有 → 我就是根，返回

        parent_dir = cur_dir.parent                # ③ 没有 → 上移一级
        if cur_dir == parent_dir:                  # ④ 到文件系统根了吗？
            if fall_back and os.environ.get('ZEPHYR_BASE'):
                return west_topdir(os.environ['ZEPHYR_BASE'],
                                   fall_back=False)   # ⑤ 换个起点再试一次
            else:
                raise WestNotFound('Could not find a west workspace '
                                   'in this or any parent directory')
        cur_dir = parent_dir                       # ⑥ 继续向上

```


```
app.run()
  → west_topdir()                      # 22 行向上遍历
  → 找到 .west → topdir = west-lab      # .west = 路标目录，内含 config 藏宝图
  → 找不到 → WestNotFound → topdir=None # 不立刻死，第 10 步由命令自己决定
  → self.config = Configuration(topdir) # ← 第 3 步：读 .west/config + 全局配置
```

#### 3. Configuration(topdir)：读 .west/config + ~/.westconfig + /etc/westconfig

- 入口：topdir 在这里被消费：Configuration 拿着它拼出 .west/config 的路径，一次性把三级配置文件全部读进内存

```python
# main.py:260-266
self.config = west.configuration.Configuration(topdir=self.topdir)   # ① 本步
self.config._copy_to_configparser(west.configuration.config)          # ② 遗留兼容
```

- 三个 \_InternalCF，可能为 None

```python
# configuration.py:163-179（删注释）
def __init__(self, topdir=None):
    local_path = _location(ConfigFile.LOCAL, topdir=topdir,
                           find_local=False) or None          # ★ 细节见下
    self._system_path = Path(_location(ConfigFile.SYSTEM))
    self._global_path = Path(_location(ConfigFile.GLOBAL))
    self._local_path  = Path(local_path) if local_path else None

    self._system = _InternalCF.from_path(self._system_path)   # 文件不存在 → None
    self._global = _InternalCF.from_path(self._global_path)   # 文件不存在 → None
    self._local  = _InternalCF.from_path(self._local_path)    # 文件不存在 → None
```





```
run()
  → Configuration(topdir)                 # 读三层文件 → 三个 _InternalCF（或 None）
  → _copy_to_configparser(全局config)      # 兼容旧扩展
  → 产出：self.config
      读：ALL = local > global > system，KeyError 逐级下落，默认值兜底
      写：默认 LOCAL，懒建文件，立即全量重写，无并发保护
  → 即将进入：load_manifest()             # ← 第 4 步：用 manifest.path/file 找到 west.yml
```
#### 4. load_manifest()：west.yml →校验→ Project 图（import 递归合并）【失败仅存 self.mle】

- 把 west.yml 这份**意图声明**变成程序可操作的对象图

```python
# main.py:280-303
def load_manifest(self):
    if not self.topdir:
        return                                    # 工作区都没有，跳过
    try:
        self.manifest = Manifest.from_topdir(topdir=self.topdir,
                                             config=self.config)
    except (ManifestVersionError, MalformedManifest, MalformedConfig,
            ManifestImportFailed, FileNotFoundError, PermissionError) as e:
        self.mle = e                              # ★ 失败不 die！存起来
```

- 解析流水线

```
.west/config 说 manifest.path=manifest, file=west.yml
  → Manifest.from_topdir → from_file（:1233-1301）
  → _load：yaml.load(SafeLoader/CSafeLoader :211)
  → validate()（:537-601）：
      ① 顶层必须有 'manifest' 键
      ② version 预检查（对照 SCHEMA_VERSION='1.2' + _VALID_SCHEMA_VERS 白名单）
      ③ pykwalify.core.Core(source_data, manifest-schema.yml).validate()
         → SchemaError 包装成 MalformedManifest（附文件路径 + schema 路径）
  → _load_validated（:1992 起）语义解析：
      ① self: → ManifestProject（名字硬编码 'manifest'，FIXME #327）
      ② defaults/remotes → _defaults NamedTuple + url_bases 字典
      ③ projects 逐条 _load_project（:2337-2459）：
           url 优先级：显式 url > remote+repo-path > defaults.remote
           url = url_bases[remote] + '/' + (repo-path 或 name)
           path = path_prefix / 显式path 或 name（路径逃逸校验 :2429-2457，
                  拒绝绝对路径/../进 .west）
      ④ import 递归合并（见下）
      ⑤ _check_paths_are_unique（:2728）
      ⑥ ManifestProject 硬插 projects[0]
```

- import递归
	- **机制：递归构造新 Manifest 实例 + 共享同一个可变 `_import_ctx`**（manifest.py:2225-2242 / 2583-2608）：

```python
child_ctx = self._ctx._replace(
    path_prefix=self._ctx.path_prefix / imap_path_prefix,   # 标量字段换新的一层
    current_data=data, manifest_west_commands=[])
Manifest(topdir=self.topdir, internal_import_ctx=child_ctx) # 递归！但 ctx.projects
                                                            # 还是同一个 dict 对象
```



```
app.run()
  → Configuration(topdir)                    # 第 4 讲：拿到藏宝图
  → load_manifest()                          # 本讲：
      from_topdir → 五道关卡 → Project 对象图
      import 递归：新实例 + 旧登记簿 + 先到先得
  → 成功：self.manifest = 一张项目图          ★ 三件套最后一件到位！
    失败：self.mle = 异常（第 10 讲裁决，白名单 6 个命令可继续）
  → 即将进入：load_extension_specs()          # ← 第 6 讲：扫描扩展命令（只登记不加载）
```

#### 5. load_extension_specs()



```
app.run()
  → load_manifest()                       # 第 5 讲：一张项目图
  → load_extension_specs()                # 本讲：扫出一张扩展登记表
      遍历 projects → 每个有 west-commands 的项目：
      路径安全闸 → yaml 解析 → pykwalify 校验 → 造 WestExtCommandSpec（含欠条 _ExtFactory）
      影子/重名过滤 → self.extensions = {'hello': spec, ...}
      ★ 全程零 import（铁证：import 时副作用文件不存在）
  → 即将进入：load_aliases()              # ← 第 7 讲：别名表（最短的一讲）
```

#### 6. load_aliases()

- 管家在档案室里再撕一张便利贴：用户自定义的命令快捷方式（别名）

```python
def load_aliases(self):
    if not self.config:                                  # ①
        return
    self.aliases = {                                     # ②
        k[6:]: Alias(k[6:], v)
        for k, v in self.config.items()
        if k.startswith('alias.')
    }
```



```
app.run()
  → load_manifest() / load_extension_specs()   # 第 5、6 讲
  → load_aliases()                             # 本讲：配置 [alias] 节 → 别名对象表
      7 行字典搬运 + Alias 对象（shlex 拆词、永不亲自执行）
  → 产出：self.aliases = {'h': Alias对象, ...}   ★ 柜子填上
      兑现在第 9 讲的 while 展开循环（链式、pop 防环、argv 替换）
  → 即将进入：setup_parsers()                  # ← 第 8 讲：搭 argparse 树
```
#### 7. setup_parsers()



```
app.run()
  → load_manifest / load_extensions / load_aliases   # 第 5-7 讲：情报就绪
  → setup_parsers()                                  # 本讲：
      make_parsers 造树干（5 个全局选项 + subparsers 挂钩）
      内置 13 个真注册（update 注册了 -k/-r/-f... 全家桶）
      扩展占坑（stub：只有名字）
      别名防撞名注册
  → 产出：self.west_parser（一棵完整的树）            ★ 柜子填上
  → 即将进入：run_command()                          # ← 第 9 讲：用这棵树解析、分发
```
#### 8. run_command()


```
app.run()
  → （第 1-8 讲：情报 + 树）
  → run_command(argv, early_args)        # 本讲：
      ① 别名展开（argv 层面，树不知情）
      ② 未知名拦截（人话报错，带 workspace 语境）
      ③ parse_known_args（一个 Namespace 装下全部；unknown 分离待透传）
      ④ 遗留日志净额对齐
      ⑤ help 路由（-h 的标记在此决策）
      ⑥ 分发：'update' ∈ builtins → run_builtin   ★ 点名！
  → 即将进入：run_builtin()              # ← 第 10 讲：点名的善后与三件套注入
```
#### 9. run_builtin()


```
run_command → 'update' ∈ builtins → run_builtin(args, unknown)   # 本讲：
    ① 排队 args dump（-vvv 可见）
    ② self.cmd = Update 实例
    ③ 音量：INF(3) + v数 - q数，夹在 [0,6]
    ④ mle 雷裁决：update ∈ 白名单 → 放行（或对非白名单命令排队 die）
    ⑤ queued_io 全部挂成 pre-run hook
    ⑥ self.cmd.run(args, unknown, topdir, manifest, config)      # → 第 11 讲
```
#### 10. WestCommand.run()



#### 11. Update.do_run()




#### 12. init→fetch→update-ref manifest-rev→清 refs/west→策略判定→submodules





#### 13. 失败聚合 → CommandError → sys.exit


