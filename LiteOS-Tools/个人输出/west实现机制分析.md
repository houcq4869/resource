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

### 命令跟踪——west topdir
#### main.py

`BUILTIN_COMMAND_GROUPS`（:1204-1225，全部命令的注册表）

~~~python
BUILTIN_COMMAND_GROUPS = {
    'built-in commands for managing git repositories': [
        Init,
        Update,
        List,
        ManifestCommand,
        Compare,
        Diff,
        Status,
        ForAll,
        Grep,
    ],

    'other built-in commands': [
        Help,
        Config,
        Topdir,
    ],

    # None is for hidden commands we don't want to show to the user.
    None: [SelfUpdate]
}
~~~


`WestApp.run`（:235-278，主流程）

```python
	def run(self, argv):
        # Run the command-line application with argument list 'argv'.

        early_args = parse_early_args(argv)

        # Silence validation errors from pykwalify, which are logged at
        # logging.ERROR level. We want to handle those ourselves as
        # needed.
        logging.getLogger('pykwalify').setLevel(logging.CRITICAL)

        # Use verbosity to determine west API log levels
        self.setup_west_logging(early_args.verbosity)

        # Makes ANSI color escapes work on Windows, and strips them when
        # stdout/stderr isn't a terminal
        colorama.init()

        # See if we're in a workspace. It's fine if we're not.
        # Note that this falls back on searching from ZEPHYR_BASE
        # if the current directory isn't inside a west workspace.
        try:
            self.topdir = west_topdir()
        except WestNotFound:
            pass

        # Read the configuration files. We need this to get
        # manifest.path to parse the manifest, etc.
        self.config = west.configuration.Configuration(topdir=self.topdir)

        # Also set up the global configuration object to match, for
        # backwards compatibility.
        self.config._copy_to_configparser(west.configuration.config)

        # Set self.manifest and self.extensions.
        self.load_manifest()
        self.load_extension_specs()
        self.load_aliases()

        # Set up initial argument parsers. This requires knowing
        # self.extensions, so it can't happen before now.
        self.setup_parsers()

        # OK, we are all set. Run the command.
        self.run_command(argv, early_args)
```

`run_command`（:534-641）

```python
    def run_command(self, argv, early_args):
        # Parse command line arguments and run the WestCommand.
        # If we're running an extension, instantiate it from its
        # spec and re-parse arguments before running.

        if not early_args.help and early_args.command_name != "help":
            # Recursively replace alias command(s) if set
            aliases = self.aliases.copy()
            while early_args.command_name in aliases:
                # Make sure we don't end up in an infinite loop
                alias = aliases.pop(early_args.command_name)

                self.queued_io.append(lambda cmd, alias=alias: cmd.dbg(
                    f'Replacing alias {alias.name} with {alias.args}'
                ))

                if len(alias.args) == 0:
                    # This loses the cmd.dbg() above - too bad, don't use empty aliases
                    self.print_usage_and_exit(f'west: empty alias "{alias.name}"')

                # Find and replace the command name. Must skip any other early args like -v
                for i, arg in enumerate(argv):
                    if arg == early_args.command_name:
                        argv = argv[:i] + alias.args + argv[i + 1:]
                        break
                early_args = early_args._replace(command_name=alias.args[0])

        self.handle_early_arg_errors(early_args)
        args, unknown = self.west_parser.parse_known_args(args=argv)

        # Set up logging verbosity before running the command, for
        # backwards compatibility. Remove this when we can part ways
        # with the log module.
        log.set_verbosity(args.verbose - args.quiet)

        # If we were run as 'west -h ...' or 'west --help ...',
        # monkeypatch the args namespace so we end up running Help.  The
        # user might have also provided a command. If so, print help about
        # that command.
        if args.help or args.command is None:
            args.command_name = args.command
            args.command = 'help'

        # Finally, run the command.
        try:
            # Both run_builtin() and run_extension() set self.cmd so
            # we can use it in the exception handling blocks below.
            if args.command in self.builtins:
                self.run_builtin(args, unknown)
            else:
                self.run_extension(args.command, argv)
        except KeyboardInterrupt:
            # Catching this avoids dumping stack.
            #
            # Here we replicate CPython's behavior in exit_sigint() in
            # Modules/main.c (as of
            # 2f62a5da949cd368a9498e6a03e700f4629fa97f), but in pure
            # Python since it's not clear how or if we can call that
            # directly from here.
            #
            # For more discussion on this behavior, see:
            #
            # https://bugs.python.org/issue1054041
            if platform.system() == 'Windows':
                # The hex number is a standard value (STATUS_CONTROL_C_EXIT):
                # https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55
                #
                # Subtracting 2**32 seems to be the convention for
                # making it fit in an int32_t.
                CONTROL_C_EXIT_CODE = 0xC000013A - 2**32
                sys.exit(CONTROL_C_EXIT_CODE)
            else:
                # On Unix, just reinstate the default SIGINT handler
                # and send the signal again, overriding the CPython
                # KeyboardInterrupt stack dump.
                #
                # In addition to exiting with the correct "dying due
                # to SIGINT" status code (usually 130), this signals
                # to the calling environment that we were interrupted,
                # so that e.g. "while true; do west ... ; done" will
                # exit out of the entire while loop and not just
                # the west command.
                signal.signal(signal.SIGINT, signal.SIG_DFL)
                os.kill(os.getpid(), signal.SIGINT)
        except BrokenPipeError:
            sys.exit(0)
        except CalledProcessError as cpe:
            self.cmd.err(f'command exited with status {cpe.returncode}: '
                         f'{quote_sh_list(cpe.cmd)}', fatal=True)
            if self.cmd.verbosity >= Verbosity.DBG_EXTREME:
                self.cmd.banner('Traceback (enabled by -vvv):')
                traceback.print_exc()
            sys.exit(cpe.returncode)
        except ExtensionCommandError as ece:
            self.handle_extension_command_error(ece)
        except CommandError as ce:
            # No need to dump_traceback() here. The command is responsible
            # for logging its own errors.
            sys.exit(ce.returncode)
        except MalformedManifest as mm:
            # We can get here because 'west update' is allowed to run
            # even when an invalid manifest was detected, as a way to
            # try to fix a previous update that left 'manifest-rev'
            # branches pointing at revisions with invalid manifest
            # data in projects that get imported.
            self.cmd.die('\n  '.join(str(arg) for arg in mm.args))
        except WestNotFound as wnf:
            self.cmd.die(str(wnf))
```


#### commands.py

`WestCommand.run`（:171-200）

```python
    def run(self, args: argparse.Namespace, unknown: list[str],
            topdir: PathType,
            manifest: Optional[Manifest] = None,
            config: Optional[Configuration] = None) -> None:
        '''Run the command.

        This raises `west.commands.CommandContextError` if the command
        cannot be run due to a context mismatch. Other exceptions may
        be raised as well.

        :param args: known arguments parsed via `WestCommand.add_parser`
        :param unknown: unknown arguments present on the command line;
            must be empty unless ``accepts_unknown_args`` is true
        :param topdir: west workspace topdir, accessible as a str via
            ``self.topdir`` from `WestCommand.do_run`
        :param manifest: `west.manifest.Manifest` or ``None``,
            accessible as ``self.manifest`` from `WestCommand.do_run`
        :param config: `west.configuration.Configuration` or ``None``,
            accessible as ``self.config`` from `WestCommand.do_run`
        '''
        self.config = config
        if unknown and not self.accepts_unknown_args:
            self.parser.error(f'unexpected arguments: {unknown}')
        if not topdir and self.requires_workspace:
            self.die(_no_topdir_msg(os.getcwd(), self.name))
        self.topdir = os.fspath(topdir) if topdir else None
        self.manifest = manifest
        for hook in self._hooks:
            hook(self)
        self.do_run(args, unknown)
```


#### project.py

`Topdir.do_run`（:2102-2103)

```python
    def do_run(self, args, user_args):
        self.inf(PurePath(self.topdir).as_posix())
```


### 命令跟踪——west update

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

#### 1. parse_early_args

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




#### 2. west_topdir()：向上找 .west 目录 ──► topdir（"路标"就是 .west 本身）




#### 3. Configuration(topdir)：读 .west/config + ~/.westconfig + /etc/westconfig




#### 4. load_manifest()：west.yml →校验→ Project 图（import 递归合并）【失败仅存 self.mle】



#### 5. load_extension_specs()




#### 6. load_aliases()



#### 7. setup_parsers()：内置真注册 + 扩展占坑




#### 8. run_command()：parse_known_args → 查 builtins 字典 → run_builtin



#### 9. run_builtin()：调 verbosity + 兑现延迟错误（update ∈ 白名单）



#### 10. WestCommand.run()：注入 config/topdir/manifest + hooks → do_run



#### 11. Update.do_run()：带 importer 重解析清单（先 update 再读 import）→ 遍历项目




#### 12. 每项目：init→fetch→update-ref manifest-rev→清 refs/west→策略判定→submodules





#### 13. 失败聚合 → CommandError → sys.exit


