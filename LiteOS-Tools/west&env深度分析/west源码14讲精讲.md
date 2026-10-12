# west 源码 14 讲精讲——以 west update 为例的完整执行链路

> 撰写日期：2026-10-12 ｜ 代码基线：west v1.4.0（commit `746e1b19`，`~/workspace/repo/west`）
> 本文来源：对话式逐讲教学的完整记录（14 讲，每讲按【回顾定位 → 代码走读 → 实验证据 → 设计观察 → 时间线 → 三件事 → 自测】的固定格式）。
> 所有实验均在 Ubuntu 22.04 / git 2.34.1 / west 1.4.0（pip 安装）+ 玩具工作区（3 个 bare 仓 + 本地清单仓）上实测，输出原样收录。
> 与系列文档的关系：
> | 你的位置 | 用哪份 |
> |---|---|
> | 入门：实验场 + 六站路线 | 《west源码阅读指南》 |
> | **逐讲精讲执行链路（本文）** | 本文 |
> | 全局地图 / 快速回忆 | 《west实现机制图解》 |
> | 查证细节 / 行号证据 | 《west实现机制深度分析》 |
>
> 编号对照：本文 14 讲 ↔ 《west命令执行全流程精讲》的 ⓪–⑬ 步（第 1 讲 = ⓪，第 14 讲 = ⑬）。

---

## 总览：14 讲流水线

```
west update
 ⓵ pip 胶水 → main() → WestApp()：13 个命令对象就位                    （第 1 讲）
 ⓶ parse_early_args：命令名+净 verbosity；日志级别先于清单生效          （第 2 讲）
 ⓷ west_topdir：向上找 .west 路标 → topdir（找不到先不死）             （第 3 讲）
 ⓸ Configuration：三级配置一次读入（构造即快照）                        （第 4 讲）
 ⓹ load_manifest：五道关卡+import 递归 → Project 图（坏则存 mle）       （第 5 讲）
 ⓺ load_extension_specs：扫 west-commands.yml，只造欠条，零 import      （第 6 讲）
 ⓻ load_aliases：[alias] 节 → 别名对象表（可劫持内置命令）              （第 7 讲）
 ⓼ setup_parsers：树干+内置真注册+扩展占坑+别名防撞                     （第 8 讲）
 ⓽ run_command：别名展开→未知名拦截→parse→help 路由→查表分发            （第 9 讲）
 ⓾ run_builtin：调音量→mle 裁决（白名单6命令）→排队消息挂 hook          （第 10 讲）
 ⑪ WestCommand.run：闸门×2→三件套注入→hooks 清账→do_run               （第 11 讲）
 ⑫ update_all：清单二次解析（先 update 再读 import）→遍历三跳过         （第 12 讲）
 ⑬ 每项目 update()：fetch→update-ref manifest-rev→策略三选一→子模块     （第 13 讲）
 ⑭ _handle_failed 结算 → CommandError → 异常阶梯 → sys.exit            （第 14 讲）
```

前 11 讲是**所有命令共用的高速公路**；第 12 讲起进入 `west update` 自己的领地。

---

# 第 1 讲：west 程序是怎么"出生"的

## 1.1 先建立一个总画面：west 像一栋办事大楼

把整条执行链想象成你走进一栋大楼办事：

```
你说："我要办 update 业务"（敲 west update）
  → 门口保安室：看你是谁、要不要讲解耳机（第 2 讲：手搓解析器）
  → 查园区门牌：你属于哪个小区？（第 3 讲：找 .west）
  → 调档案：你的偏好设置（第 4 讲：读配置）
  → 查项目名录：这栋楼里有哪些仓（第 5 讲：解析 west.yml）
  → 查窗口名录：楼里有哪些额外服务（第 6 讲：扫描扩展）
  → 带你去对应窗口（第 9 讲：分发）
  → 窗口办事员领三样资料开工（第 11 讲：三件套注入）
  → 办事员干 update 的活（第 12-14 讲：git 编排）
```

本讲讲的是**你还没进大楼之前的事**：这栋楼是谁盖的、门口那扇门（`west` 命令本身）是什么做的。

## 1.2 你敲的 `west`，其实是一个 9 行的小文件

`which west` → `/home/houcq/.local/bin/west`。**这个文件不是 west 作者写的，是 pip 安装时自动生成的**。它的全部内容：

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

### 逐行白话翻译

| 代码 | 白话 |
|---|---|
| `#!/usr/bin/python3` | 告诉系统："用 python3 来运行我"（不然 bash 会把它当 shell 脚本） |
| `import re, sys` | 拿两件工具：正则表达式（re）、系统功能（sys） |
| `from west.app.main import main` | **本文件的灵魂**：从 west 软件包里，把 `main` 这个函数请出来。从此刻起，west 的源码正式参战 |
| `if __name__ == '__main__':` | "只有当我被**直接执行**时才往下走"。这个文件永远是被直接执行的，所以条件恒真——写它是防御性惯例 |
| `sys.argv[0] = re.sub(...)` | 给自己修剪名字。Windows 上这个文件可能叫 `west.exe` 或 `west-script.pyw`，这行把后缀剪掉，让程序自认为叫 `west`（帮助信息里显示的名字才统一） |
| `sys.exit(main())` | 调用 west 的主函数；它结束时，返回值/异常就成了整个进程的**退出码**（0=成功——这是第 14 讲的出口） |

### 这个文件是谁生成的？

pip 读 west 包的 `pyproject.toml` 里的这两行：

```toml
[project.scripts]
west = "west.app.main:main"
```

意思是："装我的时候，请生成一个叫 `west` 的命令，它执行 `west.app.main` 模块里的 `main` 函数。" pip 照办，写出了上面那个 9 行文件。

**这一环的设计意义**：west 作者只写了"模块路径：函数名"这个**约定**，入口文件交给打包工具生成。所以 `west update` 的第一行代码，其实运行在你家磁盘上 pip 写的文件里，而不是 west 仓库里。

## 1.3 `main()`：短到只有两行

```python
# main.py:1196-1199
def main(argv=None):
    app = WestApp()
    app.run(argv or sys.argv[1:])
```

### 先补一个背景知识：`sys.argv` 是什么

当 Python 程序启动时，命令行的内容会自动装进一个列表 `sys.argv`：

```python
$ python3 argv_demo.py update --narrow
['/tmp/opencode/argv_demo.py', 'update', '--narrow']
 └── argv[0]：程序自己            └── argv[1:]：真正的参数
```

所以 `argv or sys.argv[1:]` 的意思是："如果调用方明确传了参数列表就用它（**测试时**这么干），否则从真实命令行里取**去掉程序名之后**的部分"。对我们这条线，`app.run(['update'])`。

### 两行各自在干什么

| 代码 | 白话 |
|---|---|
| `app = WestApp()` | 造一个"管家"对象，并把楼里的 13 个办事窗口**预先装修好**（下一节展开） |
| `app.run(['update'])` | 把参数交给管家："开始按流程办 update 这件事"——后面 13 讲全是这两字的展开 |

### 为什么不直接写成过程式的几十行？

看作者写在类上方的注释（main.py:199-201），翻译过来：

> "我们可以用全局变量（存这些状态），但那样就很难在同一个 Python 进程里反复测试 `main()`，而这正是我们想要的（issue #149）。"

**用"对象"代替"全局变量"，唯一理由是可测试性**：测试代码可以 `app = WestApp(); app.run(['update'])` 连续跑一百次，每次状态互不污染；全局变量跑第二次就带着上次的残留了。

## 1.4 `WestApp()` 构造：先把 13 个窗口装修好

构造函数（main.py:203-233）干两件事：**立一堆空柜子** + **把 13 个命令对象造出来登记在册**。

### 第一步：立空柜子（`:204-216`）

```python
self.topdir = None          # 柜子1："工作区在哪"——现在空着，第 3 讲往里放
self.config = None          # 柜子2："配置是什么"——第 4 讲放
self.manifest = None        # 柜子3："清单是什么"——第 5 讲放
self.mle = None             # 柜子4："清单加载失败时的异常"——先备着，第 5 讲存，第 10 讲用
self.builtins = {}          # 柜子5：内置命令花名册——★今天马上就有内容
self.extensions = {}        # 柜子6：扩展命令花名册——第 6 讲
self.aliases = {}           # 柜子7：别名录——第 7 讲
...（还有 parser、cmd 等工具柜）
```

**读源码技巧（本讲最值钱的一条）**：看到一大片 `self.xxx = None`，别急着翻页——这是作者在给你画**程序的状态地图**。后面 1000 行代码的本质，就是把这些 `None` 一个一个换成真值。**每读一讲，就问自己"这讲填了哪个柜子"**，主线就永远不会丢。

### 第二步：造出 13 个命令对象（`:218-221`）

```python
for group, classes in BUILTIN_COMMAND_GROUPS.items():
    lst = [cls() for cls in classes]
    self.builtins.update({command.name: command for command in lst})
    self.builtin_groups[group] = lst
```

数据源是文件末尾的一张表（main.py:1204-1225）：

```python
BUILTIN_COMMAND_GROUPS = {
    'built-in commands for managing git repositories': [   # 组1：git 管理组
        Init, Update, List, ManifestCommand,
        Compare, Diff, Status, ForAll, Grep],              # 9 个命令类
    'other built-in commands': [Help, Config, Topdir],     # 组2：杂项
    None: [SelfUpdate],                                    # 组3：None = 隐藏组
}
```

**逐行翻译那个循环**：

| 代码 | 白话 |
|---|---|
| `for group, classes in ...items()` | 把表翻一遍，每次拿一个组名和它的命令类列表 |
| `lst = [cls() for cls in classes]` | `cls` 是**类**（图纸），`cls()` 是**调用类 = 按图纸造实物**——一口气把整组对象全造出来 |
| `self.builtins.update({...})` | 造好的对象按"命令名 → 对象"登记进花名册字典。从此 `self.builtins['update']` 就是那个 Update 实例 |
| `self.builtin_groups[group] = lst` | 同时按组归档一份（`west help` 显示时按组分栏） |

### 关键边界：造出来 ≠ 干活了

此刻 `Update` 实例确实存在，但请务必建立这个认知：

- 它**没有**解析任何参数（argparse 要到第 8 讲才出生）
- 它**没有**读过任何文件（`.west`、`west.yml` 都还不知道在哪）
- 它唯一的"内容"是构造时登记的**静态信息**：名字叫 `'update'`、帮助文本、`requires_workspace=True`

**这一步相当于把各窗口的办事员都请到楼里坐好，但还没开张**。

### 最后一个小动作：给 help 开后门（`:233`）

```python
self.builtins['help'].app = self
```

为什么 help 特殊？因为 `west help 任意命令` 要能翻**任何窗口**的帮助手册，还要能看整栋楼的窗口分布图（主 parser）——而 argparse 没提供从子窗口"爬回"总台的正规通道。于是直接把管家自己的引用塞给 help。

作者在注释里是怎么说的？（main.py:225）——*"A dirty layering violation"*（一个肮脏的分层违规），认账了。**读源码的真实一课**：这不是你看不懂，它确实就是个妥协的伤疤；作者没掩盖，注释本身就是设计文档。

## 1.5 本讲时间线（一图收束）

```
你敲 west update
  ① bash 在 PATH 里找到 /home/houcq/.local/bin/west
  ② 执行这个 pip 生成的 9 行胶水脚本
  ③ 胶水脚本 import 并调用 west.app.main.main()
  ④ main() 两行：造 WestApp（13 个命令对象就位 + 一堆空柜子）
  ⑤ app.run(['update'])                                ← 下一讲从这里开始
```

**今天填了哪个柜子**：只有 `builtins`（内置命令花名册）有了内容；其余柜子全部还是 `None`。

**你只需要记住三件事**：
1. `west` 命令本身是 pip 按 `pyproject.toml` 的约定生成的胶水脚本，它只负责调用 `main()`
2. `main()` 的策略是"先造管家对象再干活"，为的是可测试性
3. 此刻进程里已有的**唯一**实质内容：13 个待命的命令对象；一切与"你的工作区"有关的信息还都没加载

## 自测

1. `pip uninstall west` 之后敲 `west update`，报错的会是谁？（答：bash——PATH 里找不到 west，错误消息和 west 源码毫无关系）
2. `sys.argv[0]` 和 `sys.argv[1:]` 分别装着什么？`main()` 里 `argv or sys.argv[1:]` 是想让谁受益？（答：测试代码——它可以注入自己的参数列表）
3. 把 `Update` 从 `BUILTIN_COMMAND_GROUPS` 删掉，`west update` 会死在哪一讲？（答：第 9 讲分发时查不到花名册，报 unknown command）

---

# 第 2 讲：门口的保安室——手搓迷你解析器

## 2.1 先看要解决的问题：一条"鸡生蛋"死锁链

正常的想法是：CLI 工具嘛，`argparse` 一把梭。但 west 建不起完整的 argparse 树，推演一下就明白：

```
想建完整的命令树
  → 树上必须包含"扩展命令"（west build/flash 是谁挂的？）
    → 扩展命令从哪来？读 west.yml 里各项目的 west-commands.yml
      → west.yml 在哪？读 .west/config 的 manifest.path
        → .west 在哪？要先找到工作区根 topdir
          → 可是！用户可能敲的是 west -V（只是看版本号）
             根本不该去找工作区——甚至可能就不在工作区里！
```

链条断在两头：**建树需要的信息在最深处，而有些用户根本不需要树**。

west 的解法是：**先用 80 行手搓代码扫一遍 argv，只提取"在任何情况下都需要尽早知道"的信息**，其余全部留给后面的 argparse。这就是 `parse_early_args`（main.py:94-172）。

**为什么 verbosity 必须早知道**——这是最容易被忽略的一点：`-v` 要控制的日志里，**包括清单解析过程本身的日志**。而清单解析发生在第 5 讲。所以日志级别的设定必须发生在第 5 讲之前，也就是现在。

官方理由（`EarlyArgs` 注释，main.py:70-92）：
1. 命令是扩展命令、但人不在工作区时，能给出**更友好的报错**；
2. **用 verbosity 提前设定日志级别**。

## 2.2 它长什么样：一个装 6 个格子的收纳盒

`parse_early_args` 的返回值是个 `EarlyArgs`——一种**不可变的"收纳盒"**（Python 叫 NamedTuple，可以理解为"带字段名的元组"）：

| 格子 | 装什么 | 白话 |
|---|---|---|
| `help` | True/False | 用户敲了 `-h` 吗 |
| `version` | True/False | 用户敲了 `-V` 吗 |
| `zephyr_base` | 路径或 None | `-z` 带的路径 |
| `verbosity` | 整数 | 啰嗦程度：`-v` 每次加 1，`-q` 每次减 1 |
| `command_name` | 字符串或 None | ★**第一个不以 `-` 开头的词 = 命令名** |
| `unexpected_arguments` | 字符串列表 | 其他不认识的 `-` 开头的词，**先记账不报错** |

## 2.3 主循环走读：一台 if-elif 分类机

```python
for arg in argv:
    if expecting_zephyr_base:          # 上一个词是孤零零的 -z，那这个词就是它的值
        zephyr_base = arg
    elif arg.startswith('-h'):  help = True; consume_more_args(arg[2:])
    elif arg.startswith('-V'):  version = True; consume_more_args(arg[2:])
    elif arg.startswith('-v'):  verbosity += 1; consume_more_args(arg[2:])
    elif arg.startswith('-q'):  verbosity -= 1; consume_more_args(arg[2:])
    elif arg.startswith('-z'):  # 三种形态：-z PATH / -z=PATH / -zPATH
        ...
    elif arg.startswith('-'):   unexpected_arguments.append(arg)   # ★ 只记账
    else:
        command_name = arg             # ★★ 第一个非选项 token = 命令名
        break                          # ★★ 后面的词是命令自己的参数，与我无关
```

### 实测：直接调用 parse_early_args 看七种输入的输出

```
['-v', 'update']        => verbosity=1, command_name='update'
['-v', '-v', '-q', 'update'] => verbosity=1              ← 净计数（+1+1-1）
['-hVv', 'list']        => help=True, version=True, verbosity=1, command_name='list'
['-z=/path/to/z', 'update'] => zephyr_base='/path/to/z', command_name='update'
['-z', 'update']        => zephyr_base='update', command_name=None    ← ★陷阱！
['--foo', 'update']     => command_name='update', unexpected_arguments=['--foo']
['update', '-v']        => command_name='update', verbosity=0         ← 命令名后的 -v 不归它管
```

三个关键行为：

**① 命令名 = 第一个不以 `-` 开头的词，拿到就 `break`。** `['update']` → `'update'`，没有更玄的机制。

**② 不认识的选项只记账。** `--foo` 被记进"待处理清单"，**此刻不报错**——它很可能是某个命令自己的参数（比如 `west init -o=--depth=1` 里的 `-o=...`）。**保安室管不了的，留给懂行的窗口（argparse）去裁决**。这个"克制"是手搓解析器不出错的根本原因。

**③ 命令名后面的 `-v`，保安室看不见**（break 了）。所以**全局选项必须写在命令名之前**——`west -v list` 合法，`west list -v` 会在第 11 讲的闸门被拒（实测：`west list: error: unexpected arguments: ['-v']`）。

### `-z` 的陷阱

`west -z update` 的本意可能是"设 ZEPHYR_BASE 再跑 update"，但规则是"`-z` 后面紧跟的词就是它的值"——**`update` 被当成路径吃掉了，命令名变成 None**（最后落到 help 路由）。想表达原意要写 `west -z=/path update`。这种"吃词"行为是所有"选项后跟值"解析器的共性（`git -C` 同款）。

## 2.4 `consume_more_args`：处理 Unix 风格的"合并短选项"

Unix 传统允许把短选项**粘在一起**：`-hVv` = `-h` + `-V` + `-v`。argparse 天生支持，手搓就得自己处理——west 的办法是**递归**：

```
词是 '-hVv'
  → startswith('-h') 命中：help=True，把剩下的 'Vv' 递归处理
      → 'V' 命中：version=True，递归 'v'
          → 'v' 命中：verbosity=1，剩下 '' → return
```

## 2.5 verbosity 净计数

`-v` 加 1、`-q` 减 1，是一个**净额**。为什么这么设计（三句话版）：①日志"要多啰嗦"是**一根数轴上的一个点**，不是两个独立维度——净计数把"-v 和 -q 同时出现谁赢"的问题变成算术；②`ssh -vvv`、`git -q` 的 Unix 惯例；③**west 里有两个人数参数**——保安室（手搓）和窗口（argparse 的 `action='count'`），两套数法必须算出同一个数才不打架：

```python
# 保安室（手搓）：直接加减
elif rest.startswith('v'):  verbosity += 1

# 窗口（argparse 侧，main.py:567）：-v/-q 分开计数后相减
log.set_verbosity(args.verbose - args.quiet)
```

作者甚至专门留了注释（main.py:507）：*"如果你改了这些全局选项，记得同步更新 parse_early_args()"*——**两份解析器的对齐契约**。

## 2.6 保安室下班后：`run()` 的三个后续动作

```python
# main.py:238-250
early_args = parse_early_args(argv)
logging.getLogger('pykwalify').setLevel(logging.CRITICAL)   # ①
self.setup_west_logging(early_args.verbosity)               # ②
colorama.init()                                            # ③
```

**① 给 pykwalify 消音**：pykwalify 是第 5 讲要登场的清单校验库，它校验失败时喜欢往 ERROR 日志里喷一大段自己的格式。west 想自己控制报错文案，先把它的嘴堵上。

**② 按 verbosity 设定日志级别**（:669-683）：`>=2 → DEBUG, 1 → INFO, 0 → WARNING, -1 → ERROR, 更低 → CRITICAL`，挂到 `west.manifest` logger。**时序是关键**：这行在第 5 讲"解析清单"**之前**执行。证据（实测）：

```
$ west -vv list
west.manifest: DEBUG: loading /tmp/west-lab/manifest/west.yml     ← 清单解析的日志
west.manifest: DEBUG: resolving self import extra.yml             ← 能看到，说明级别
west.manifest: DEBUG: added project dup path dup revision main       早已设好！
```

**③ colorama.init()**：让 ANSI 颜色码在 Windows 终端也能生效；输出不是终端时自动剥色。

`-V` 在更早的地方直接打印并退出——在 `/tmp`（非工作区）实测 `west -V` 秒出 `West version: v1.4.0`，证明它不需要工作区、不需要命令树——死锁推理里"有些用户不需要树"的活证据。

## 2.7 一个重要伏笔：`command_name` 现在生产，后面消费

`run()` 在这一步**并没有使用** `early_args.command_name`。它被原样传给 `run_command(argv, early_args)`（main.py:278），要等到：**第 9 讲**（命令名不在花名册 → "unknown command" 友好报错）和**第 10 讲**（清单加载失败时查白名单）。**现在生产、后面消费**——west 里到处是这种"先把信息拿到手，决策权留给掌握全部上下文的层"的写法。

## 2.8 设计观察：这不是 west 的怪癖

"**迷你预解析器 + 主解析器**"是 CLI 工具的经典两层结构：`git` 自己就这么干；任何"子命令来自外部插件"的工具（pip、poetry…）都逃不开这条死锁链。判断标准一句话：**如果你需要的某个信息，在主解析器可用之前就得用（日志级别、命令名、`--version` 短路）——就必须提前手搓解析**。

## 本讲时间线

```
app.run(['update'])
  → parse_early_args(['update'])          # 80 行 if-elif 分类机
  → EarlyArgs(help=F, version=F, zephyr_base=None,
              verbosity=0, command_name='update',   # ★本讲最重要产物
              unexpected_arguments=[])
  → 堵 pykwalify 的嘴 / 设 west.manifest 日志级别 / colorama 初始化
  → 即将进入：west_topdir()                # ← 第 3 讲
```

**今天填了哪个柜子**：一个都没填（EarlyArgs 是局部变量）——但 `command_name` 和日志级别是**后续多讲要用的弹药**，此刻已经上膛。

**记住三件事**：
1. 手搓解析器存在的原因是死锁链：建 argparse 树需要扩展命令 → 需要清单 → 需要工作区，而 `-V` 什么都不需要；且 `-v` 要控制**清单解析本身**的日志
2. 命令名 = 第一个不以 `-` 开头的词，拿到就 break；全局选项必须写在命令名之前
3. 不认识的选项只记账不报错——"克制"是保安室不出错的原因

## 自测

1. `west -qV` 会打印什么？verbosity 最终是几？
2. `west -z update` 实际效果是什么？怎么写才能"设 ZEPHYR_BASE 且跑 update"？
3. 如果把 `-v` 的处理挪到 argparse 建树之后，`west -vv list` 会少看到什么？

---

# 第 3 讲：查园区门牌——`west_topdir()` 与 `.west` 路标

## 3.1 回顾与定位

保安室查完"你是谁"，接下来要办正事就得知道：**你是哪个园区的**。因为接下来的两个房间——档案室（配置，第 4 讲）和项目名录室（清单，第 5 讲）——都**位于园区里面**。

```python
# main.py:252-258
try:
    self.topdir = west_topdir()      # ← 本讲：找园区根目录
except WestNotFound:
    pass                             # ← 找不到？先不慌，见 3.6
```

## 3.2 要解决的问题：凭什么"在任意子目录敲 west 都能用"？

- 一个工作区 = **一个根目录** + 里面十几个仓库
- 用户可以在**任何深度**的任何子目录里敲 `west update`
- 没有任何环境变量、注册表、守护进程告诉 west"根在哪"

唯一可靠的线索是**文件系统本身**。git 面对同样的问题（找 `.git`），west 照抄了答案：**在根目录放一个特殊标记，程序从当前目录往上爬，看到标记就停**。

## 3.3 `.west` 是什么：一块只贴一张藏宝图的路标

```
west-lab/                  ← 园区根（topdir）
├── .west/                 ← ★ 路标：它存在 = "根在这里"
│   └── config             ← 藏宝图（就 3 行，实测）：
│       [manifest]
│       path = manifest    # 清单仓在根下的位置
│       file = west.yml    # 清单文件名
├── manifest/              ← 清单仓（west.yml 住这里）
├── lib/  app/             ← 项目仓
```

三个设计问答：

**问 1：为什么路标是"目录"而不是一个空文件？** ① 藏宝图 `config` 总得有地方住；② 判断时用 `is_dir()`，能**顺带排除"恰好叫 .west 的普通文件"的误判**——实测证据：`/tmp/opencode/fake/x/` 里放一个 `.west` **文件**，west_topdir 拒绝认账，照样抛 `WestNotFound`。

**问 2：为什么配置放 `.west/config`，不放进 west.yml？** 职责分离：`west.yml` 是"这个工作区由哪些仓组成"——**公共声明**，会被 git 跟踪、推给所有同事；`.west/config` 是"我这台机器上的事实和偏好"——**本地私事**。混在一起，你个人的偏好会污染所有协作者。

**问 3：`west_topdir` 返回的是哪个路径？** **命名陷阱**：返回 `.west` 的**父目录**（园区根）。想要 `.west` 本身用兄弟函数 `west_dir()`（util.py:54-63，就一行拼接）。

## 3.4 代码全文与逐行翻译（util.py:65-86，总共 22 行）

```python
def west_topdir(start=None, fall_back=True):
    cur_dir = pathlib.Path(start or os.getcwd())     # ①
    while True:                                       # ②
        if (cur_dir / WEST_DIR).is_dir():             # ③
            return os.fspath(cur_dir)                 # ④
        parent_dir = cur_dir.parent                   # ⑤
        if cur_dir == parent_dir:                     # ⑥
            if fall_back and os.environ.get('ZEPHYR_BASE'):
                return west_topdir(os.environ['ZEPHYR_BASE'],
                                   fall_back=False)   # ⑦⑧
            else:
                raise WestNotFound('Could not find a west workspace '
                                   'in this or any parent directory')
        cur_dir = parent_dir                          # ⑩
```

| # | 白话 |
|---|---|
| ① | 起点：调用方给了 start 就用它的，否则当前目录 |
| ② | "一直爬，直到命中或到顶" |
| ③ | 探测：当前目录下有没有一个**目录**叫 `.west`（`/` 是 pathlib 的拼接运算符，不是除法） |
| ④ | 命中！返回当前目录（根） |
| ⑤⑥ | 准备上移；**到根了吗**——判断技巧见下 |
| ⑦⑧ | 兜底：允许且用户设了 `ZEPHYR_BASE`，就**换个起点重新爬一次**，但 `fall_back=False` |
| ⑨ | 真找不到了，抛异常——**只是"报告事实"，不当场处死** |
| ⑩ | 上移一级 |

## 3.5 四个值得单独展开的机制

### 机制一：到根检测靠一个 pathlib 冷知识（⑥）

**根目录 `/` 的父目录还是它自己**（实测：`pathlib.Path('/').parent == Path('/')` → `True`）。所以"当前目录 == 它的父目录"就等价于"我已经站在 `/` 上了"。不需要 `os.path.ismount()` 之类的重型检测——代价是**跨挂载点也会一路爬到根**（git 默认不跨 mount，west 没这个概念）。

### 机制二：就近原则（嵌套工作区）

循环从起点**向上**爬，**遇到的第一个 `.west` 就认**。实测：从 `west-lab/lib` 出发 → 找到 `west-lab`；从 `inner-ws`（自带 `.west`）出发 → 找到 `inner-ws`。两个工作区嵌套时，**你在谁的地盘上就归谁管**——和 git 嵌套仓库行为一致。

### 机制三：`ZEPHYR_BASE` 兜底为什么必须 `fall_back=False`（⑧）

设想用户手滑设了 `ZEPHYR_BASE=/`：从 `/` 出发找不到 → 兜底又从 `/` 出发 → 又找不到 → 又兜底……**死循环**。传 `False` 保证兜底路线**只走一次**。实测：从 `/var`（非工作区）出发，设 `ZEPHYR_BASE` 就能找到 west-lab。这个兜底是为**老的、没有 `.west` 的 Zephyr 检出**保留的兼容通道。

### 机制四：`start` 参数为什么存在

算法本体**不依赖"当前目录"**——起点可以注入。本讲所有实验都是 `west_topdir('/某/路径')` 带参调用的，**一次 cd 都没做**。`start` 参数的意义：**可测试性**（测试代码不必 chdir 来 chdir 去污染环境）。

## 3.6 `run()` 怎么消费结果：发现在底层，决策在上层

关键问题：**找不到园区，是不是该立刻报错退出？** 不一定！`west help/init/config` 在园区外**必须能跑**。而"这个命令要不要园区"，要到**解析完命令行、选定命令之后**才知道。

```
第 3 讲（本层）：west_topdir 只负责报告事实
   → 找到：self.topdir = 路径（第一个柜子填上了！）
   → 没找到：异常被接住，self.topdir 保持 None，流程继续
   ……穿过第 4~10 讲，topdir=None 一路传递……
第 11 讲（上层）：WestCommand.run() 里有一道闸门
   → "topdir 是 None 且这个命令 requires_workspace=True"
   → 此刻才 die，报出你看到的 FATAL ERROR
```

实测证据（在工作区外跑 `west topdir`）：

```
FATAL ERROR: no west workspace found from "/tmp"; "west topdir" requires one.
Things to try:
  - Change directory to somewhere inside a west workspace and retry.
  - Set ZEPHYR_BASE to a zephyr repository path in a west workspace.
  ...
```

注意两个细节：① 这条消息**不是** `WestNotFound` 那句——它来自第 11 讲闸门用的另一个函数 `_no_topdir_msg`；② 消息里还**贴心地教用户用 ZEPHYR_BASE 兜底**。

**这是 west 错误处理的中心思想，第二次出现**：**底层只报告事实，决策权留给掌握全部上下文的上层**。

## 3.7 设计观察

| | git | west |
|---|---|---|
| 向上爬找标记 / 就近优先 | ✅ `.git` | ✅ `.west` |
| 环境变量 | `GIT_DIR` **直接指定**（优先于爬） | `ZEPHYR_BASE` 只是**爬失败后的备选起点**（语义不同） |
| 跨挂载点 | 默认不跨（可配） | 无概念，爬到根为止 |
| 找不到时 | 报错 | 抛异常但上层容错（白名单命令可继续） |

**为什么不缓存结果**？——保持**纯函数**性质：每次都如实反映当前文件系统状态。代价是重复爬几层目录（微秒级），换来"行为永远可从磁盘状态推导"。`west init` 刚创建 `.west` 之后立刻能被同一进程里的下一次调用找到，靠的就是不缓存。

## 本讲时间线

```
app.run()
  → parse_early_args(...)                  # 第 2 讲：你是谁
  → west_topdir()                          # 本讲：你是哪个园区的
  → 找到：self.topdir = '/home/you/west-lab'   ★ 第一个柜子填上真值！
  → 即将进入：Configuration(topdir)         # ← 第 4 讲
```

**今天填了哪个柜子**：`self.topdir`——三件套（topdir/config/manifest）的第一件。

**记住三件事**：
1. `.west` 是**目录**路标（文件版不认账），里面住着 3 行藏宝图 `config`
2. 算法 = 22 行向上爬循环；根检测靠 `Path('/').parent == Path('/')`；嵌套时就近者赢；`ZEPHYR_BASE` 是爬失败后只走一次的备选起点
3. 找不到不立刻死——**发现在底层、决策在上层**，`requires_workspace` 的闸门在第 11 讲

## 自测

1. 在 `west-lab/lib/` 下建一个**空的** `.west` **目录**：`west topdir` 返回什么？`west list` 呢？（路标有了，藏宝图没了）
2. `ZEPHYR_BASE` 和 `GIT_DIR` 的语义差在哪？为什么 west 的兜底调用必须传 `fall_back=False`？
3. `west_topdir` 和 `west_dir` 各返回什么？

---

# 第 4 讲：进园区档案室——`Configuration` 三级配置

## 4.1 回顾与定位

```python
# main.py:260-266
self.config = west.configuration.Configuration(topdir=self.topdir)   # ① 本讲主角
self.config._copy_to_configparser(west.configuration.config)          # ② 遗留兼容，见 4.9
```

## 4.2 要解决的问题：为什么要"三级"？

不同配置的"归属范围"不一样：公司想在所有机器上统一 → **机器级**；你个人对所有工作区的偏好 → **用户级**；某个园区特有的设置 → **园区级**。这个"三级 + 就近覆盖"的需求模型不是 west 发明的，是**从 git config 抄来的**。连文件名都刻意模仿。

| 级别 | 默认路径 | 环境变量覆盖 |
|---|---|---|
| SYSTEM | `/etc/westconfig` | `WEST_CONFIG_SYSTEM` |
| GLOBAL | `~/.westconfig`（XDG 时 `$XDG_CONFIG_HOME/west/config`） | `WEST_CONFIG_GLOBAL` |
| LOCAL | `<topdir>/.west/config` | `WEST_CONFIG_LOCAL` |

## 4.3 构造函数逐行翻译（configuration.py:163-179）

```python
def __init__(self, topdir=None):
    local_path = _location(ConfigFile.LOCAL, topdir=topdir,
                           find_local=False) or None       # ①
    self._system_path = Path(_location(ConfigFile.SYSTEM))  # ②
    self._global_path = Path(_location(ConfigFile.GLOBAL))
    self._local_path  = Path(local_path) if local_path else None
    self._system = _InternalCF.from_path(self._system_path) # ③
    self._global = _InternalCF.from_path(self._global_path)
    self._local  = _InternalCF.from_path(self._local_path)
```

两个细节：① **`from_path` 对不存在的文件返回 `None` 而非报错**——三级都是可选的，`/etc/westconfig` 在多数机器上根本没有；② **`find_local=False`**：找 LOCAL 时**不要**自己去文件系统搜索工作区（那是第 3 讲的职责），只信构造参数 `topdir` 拼路径。**发现工作区归 util，读文件归 Configuration**。

## 4.4 `_InternalCF`：每个文件一个卡片盒

它是对标准库 `configparser` 的薄包装。两个必须知道的点：

**① `section.key` 怎么对应到 INI**——在**第一个** `.` 处切一刀：`'demo.color'` → `[demo]` 节的 `color` 键。

**② 写入 = 立即全量重写，没有锁**。类的文档字符串（:150-152）**主动承认**：*"设置立即影响文件，且不受并发读保护。调用者自行负责互斥。"*

## 4.5 读路径：一条 10 行的瀑布

四个读取方法（`get/getboolean/getint/getfloat`）全部汇入 `_get`：

```python
def _get(self, getter, default, configfile):
    for cf in self._whence(configfile):     # [local, global, system]
        if cf is None:
            continue                        # 这一级文件不存在 → 跳过
        try:
            return getter(cf)               # 这一级里有 → 直接返回
        except KeyError:
            pass                            # 这一级没有 → 落到下一级
    return default                          # 三级都没有 → 默认值
```

**用"三张透写纸"想象**：local、global、system 三张叠起来的透写纸（local 最上）。**读 = 从上往下看，看到第一个写这个字的地方**。

### 实测：优先级与"删一层露一层"

```
$ west config demo.color blue            # 无作用域 → 落在 .west/config（local）
$ WEST_CONFIG_GLOBAL=/tmp/fake.cfg west config --global demo.color red
$ west config demo.color
blue                                     # ★ local 赢（就近优先）
$ west config -d demo.color              # 删的是 local 那份
$ west config demo.color
red                                      # ★ 删一层露一层
```

**欣赏一个小技巧**：`_get` 收到的 `getter` 是个 **lambda**。getboolean 的 lambda 里调 `cf.getboolean`、getint 的调 `cf.getint`……于是 `_get` 这 10 行完全不用关心类型转换，**一份循环逻辑服务四个 API**。

## 4.6 写路径：为什么读和写"不公平"

```python
def set(self, option, value, configfile=ConfigFile.LOCAL):   # ★ 默认 LOCAL
```

**读默认 ALL，写默认 LOCAL**。为什么？读的语义是"现在生效的值是什么"（三层综合）；写的语义是"把我的偏好记在哪"（默认记在**最私有**的 local，不会惊吓式改 `/etc/westconfig`）。

第二个不对称：**`set` 禁止传 ALL，`delete` 却允许 ALL**：

| 操作 | 不带作用域 | 传 ALL |
|---|---|---|
| `set` | 写 local | ❌ 直接拒绝 |
| `delete` | 删**最高优先级**那份 | ✅ 三层全删 |

一句话：**"三层全删"有明确含义，"三层全写"没有任何合理语义**。写不存在的文件会**懒创建**（连父目录一起建）。

## 4.7 `west config` 命令：这套 API 的遥控器

`Config` 命令**没有任何自己的存储逻辑**，只是把命令行翻译成 `Configuration` 的方法调用：`west config k` → get(ALL)；`west config k v` → set(LOCAL)；`-d` → delete；`--list` → items(ALL) 三层合并。

## 4.8 遗留兼容那行

`west.configuration.config` 是模块级**全局** configparser（:419）。往里抄一份是因为 west 1.0 前的扩展用模块级 API。**双轨制**：老轨道全标 DeprecationWarning，west 2.0 移除——与 `log.py` 同一个故事（issue #149）。

## 4.9 设计观察：构造即快照

文档字符串（:154-156）：*"WEST_CONFIG_* 环境变量在且仅在 Configuration 对象创建时生效。"* 实测铁证：

```
c  = Configuration(topdir=...)     →  c.get('demo.shape') = None
（偷偷往 global 文件追加 shape = round）
c  还是老对象                       →  c.get('demo.shape') = None   ← 看不到！
c2 = Configuration(topdir=...)     →  c2.get('demo.shape') = round  ← 新对象才看得到
```

**为什么**：一次性读入 = 对象生命周期内行为**可预测**；同时测试可以把每个用例指向独立的临时文件（本讲所有实验的隔离手法），互不污染。另外全库**没有一处** `git config` 子进程调用——**模仿接口语义，不复用实现**。

## 本讲时间线

```
app.run()
  → Configuration(topdir)                   # 本讲：三个文件一次性读入内存
  → 产出：self.config                        ★ 三件套第二件到位！
  → 即将进入：load_manifest()                # ← 第 5 讲
```

**记住三件事**：
1. 读默认 ALL（透写纸全叠、从上往下看第一眼），**写默认 LOCAL**——不对称是刻意的
2. 文件不存在 → 盒子是 None；构造即快照（建成后文件再变，对象看不到）
3. 和 git config 是"模仿语义、零复用实现"的关系

## 自测

1. `west config --global demo.x 1` 后再 `west config --local demo.x 2`，`west config --list` 里 `demo.x` 出现几次？值是什么？
2. 为什么 `set` 禁止 ALL 而 `delete` 允许？
3. 进程建好 `Configuration` 后，别人在另一终端改了 `~/.westconfig`——这个进程后续 `get` 能看到新值吗？

---

# 第 5 讲：项目名录室——`load_manifest` 把 west.yml 变成一张项目图

## 5.1 回顾与定位

```python
# main.py:280-303
def load_manifest(self):
    if not self.topdir:                     # ① 连园区都没有
        return
    try:                                    # ②
        self.manifest = Manifest.from_topdir(topdir=self.topdir,
                                             config=self.config)
    except (ManifestVersionError, MalformedManifest, MalformedConfig,
            ManifestImportFailed, FileNotFoundError, PermissionError) as e:
        self.mle = e                        # ③
```

**③ 是全讲最反直觉的一行**：解析失败不报错不退出，把异常**暂存**进 `self.mle` 柜子。作者注释（:292-302）翻译：*"也许这样是 OK 的——比如用户正在跑 `west config manifest.path foo` 来修复配置错误。但现在没法判断，得等命令行解析完才知道。"*——**发现在底层、决策在上层**的第三次登场。白名单裁决在第 10 讲。

## 5.2 大件一：west.yml 是什么，变成什么

**输入**（玩具清单实测）：

```yaml
manifest:
  version: "1.2"
  projects:
  - name: lib
    url: /tmp/west-lab/remote/lib.git
    revision: main
  - name: dup
    url: /tmp/west-lab/remote/lib.git
    revision: main
  self:
    import: extra.yml        # ★ 把 extra.yml 也拉进来合并
```

**输出**（实测，一张对象图）：

```
m.projects = [
  ManifestProject(name='manifest', path='manifest'),   # 索引 0 固定：清单仓自己
  Project(name='dup',    url=...app.git),   # ← 注意！url 是 extra.yml 里那个
  Project(name='extra',  url=...app.git),
  Project(name='lib',    url=...lib.git),
]
```

**两个容易被旧文档带偏的真相**：
- **没有 `Remote` 类**——`remotes:` 解析后只是 `{名字: url前缀}` 的普通字典（`url_bases`）。同理 `Defaults`/`Import` 也不是类，是 NamedTuple。west 的数据模型大量用 NamedTuple——当"装好就不能改的收纳盒"即可。
- **`ManifestProject`（清单仓自己）也是项目之一**，硬插在 `projects[0]`。源码里作者留了 FIXME："这整个类应该消失"（issue #327）。

## 5.3 大件二：五道关卡的解析流水线

```
west.yml 文件
  ↓ 关卡①  yaml.load(SafeLoader)          纯语法解析
  ↓ 关卡②  顶层必须有 'manifest' 键
  ↓ 关卡③  version 预检查                 对照白名单（实测：塞 "9.9" → ManifestVersionError）
  ↓ 关卡④  pykwalify 校验                 对照外部 schema 文件逐条检查字段
  ↓ 关卡⑤  _load_validated 语义解析       self → defaults/remotes → projects
                                          → import 递归 → 路径唯一性 → 插 ManifestProject
```

**关卡④ 的实测证据**（故意少写 name）：`"Cannot find required key 'name'. Path: '/projects/0'"`——错误信息**精确到 YAML 路径**。另外直接在 Python 里调 `Manifest.from_data` 时会看到 pykwalify **自己**喷的原始日志（`validation.invalid --- All found errors ---`）——west 真正的入口用 `logging.getLogger('pykwalify').setLevel(CRITICAL)` 专门堵它（第 2 讲"堵嘴"伏笔的兑现）。

三个"刻意的洞"：schema 里 `import`/`submodules` 类型是 `any`（形态多样，运行时细查）；`west-commands` 只许 `str`（list 只在 import 合并的内部过程中产生）。

**关卡⑤ 的 URL 三级优先**（`_load_project` :2337-2459）：

```
显式写了 url        → 直接用（再写 remote/repo-path 会报错）
否则写了 remote     → url = url_bases[remote] + '/' + (repo-path 或 name)
否则                → 继承 defaults.remote（三级都没有 → 报错）
```

`path` 计算：`path_prefix / 显式path 或 name`；算出来还要做**逃逸校验**（绝对路径、`..` 爬出、钻进 `.west`——三种都拒绝）。

## 5.4 大件三：import 递归——最难的一块

### 先看现象，再问问题

`dup` 被定义了**两次**：west.yml 里指向 lib.git，extra.yml 里指向 app.git。最终结果是 **extra.yml 的定义赢了**——**被导入的文件赢了导入它的文件**。

### 机制核心一句话：**递归造新实例，共享同一个登记簿**

```python
child_ctx = self._ctx._replace(
    path_prefix=self._ctx.path_prefix / '子前缀',   # 换掉标量字段
    current_data=子清单的内容)
Manifest(topdir=self.topdir, internal_import_ctx=child_ctx)   # 递归构造新清单！
```

三个连环疑问，逐个拆：

**疑问 1：为什么要递归构造自己？** 一份子清单 = 又一个完整的 west.yml，解析它需要的逻辑和解析顶层**一模一样**。

**疑问 2：说好的 NamedTuple 不可变，怎么"共享"？** **"值不可变"≠"引用不共享"**。`_replace()` 换掉的是 `path_prefix` 这类**标量**字段（父层不受影响）；但 `projects` 字段装的是一个 **dict 的引用**——child 拿到的还是**同一个 dict 对象**。父子都往这里写 → "先到先得"才能跨层生效。

**疑问 3：会不会无限递归？** 正常不会（import 是单向的）。**真有环**？west 没做检测——靠 Python 的 `RecursionError` 兜底，作者在注释里自嘲这是个 hack。

### "先到先得"的全部实现：14 行

```python
# _add_project（manifest.py:2690-2704）
def _add_project(self, project):
    if project.name not in self._ctx.projects:      # ★ 登记簿里还没有这个名字
        self._check_project_name(project)
        self._ctx.projects[project.name] = project  #   登记进去
        return True
    else:
        return False                                 # ★ 已经有人注册了 → 直接忽略
```

**没有优先级字段、没有覆盖规则——只有"谁先来谁注册，后来的忽略"**。

### 那"谁先来"由什么决定？——解析顺序

`_load_validated` 的文档字符串（:1992-1999）白纸黑字：

```
① self: import: 导入的项目      ← 最先解析
② 本文件 projects: 声明的项目
③ 项目 import: 导入的项目        ← 最后解析
```

谜底揭晓：**extra.yml 是 `self: import:`，排队第一**，它先注册了 `dup`；轮到本文件自己的 `projects:` 时，`dup` 已被占——**被忽略**。"外人盖过自己"不是因为外人有特权，是因为**队伍排在前面**。

### `-vv` 日志逐行对照（实测）

```
loading west.yml                       ← 开始解析主清单
resolving self import extra.yml        ← 关卡⑤顺序①：先处理 self import！
loading extra.yml                      ← 递归：新实例，同一登记簿
added project dup path dup revision main   ← extra.yml 的 dup 先注册 ★
added project extra path extra revision main
loaded extra.yml
resolved self import
（接下来才是本文件 projects: 的 lib —— dup 已被占，忽略）
```

### 两条读取路径 + 一个鸡生蛋伏笔

`self: import:` 从**文件系统**读；**项目**的 `import:` 从**该仓库 git 里的 manifest-rev 提交**读（`git ls-tree`）——因为"项目 A 该用哪个版本的子清单"由清单指定的 revision 决定。**鸡生蛋**：项目 A 还没克隆时它的 import 读不到！此刻读不到的部分——**第 12 讲带着"先 update 再读"的回调重新解析**。

## 5.5 REPL 玩法

```python
>>> from west.manifest import Manifest
>>> m = Manifest.from_file('~/west-lab/manifest/west.yml')
>>> [p.name for p in m.projects]
>>> m.projects[2].url, m.projects[2].revision
```

把 2784 行的 manifest.py 当成可交互的玩具——半小时的直觉胜过顺读三遍源码。

## 本讲时间线

```
→ load_manifest()：from_topdir → 五道关卡 → Project 对象图
→ 成功：self.manifest = 一张项目图      ★ 三件套最后一件到位！
  失败：self.mle = 异常（第 10 讲裁决）
```

**记住三件事**：
1. 流水线五道关卡；语义解析**顺序即规则**（self 导入 → 本文件 → 项目导入）
2. import 合并的机制是"**新实例、旧登记簿**"：`_replace` 换标量、留 dict 引用，先到先得
3. 解析失败只暂存（`self.mle`）不处死——是否致命取决于**接下来跑什么命令**

## 自测

1. 手写 3 项目 west.yml（一个 url、一个 remote+repo-path、一个 defaults），纸上算 url/path 再用 REPL 验证
2. 换成**项目** import，dup 谁赢？（项目 import 排队第几？）
3. 清单坏了，`west help` 还能跑吗？`west list` 呢？（动手试）

---

# 第 6 讲：扫描楼内服务窗口——`load_extension_specs`

## 6.1 要解决的问题：一个看似悖论的需求

west 的定位是"通用壳"：它**不懂**构建、烧录——这些领域知识住在 Zephyr 仓里。但用户敲 `west build` 时必须能找到命令：

- **`west help` 必须能列出全部扩展命令** → 必须**扫描**
- 但启动不能慢 → **不能随手 import 任何扩展代码**（Zephyr 的扩展模块全 import 一遍可能要几秒）

解法：**惰性工厂**——扫描时只记"名字 + 一个'以后怎么造它'的承诺"（欠条），真正的 import 推迟到命令被选中的那一刻（第 9 讲）。

## 6.2 扩展命令从哪来：三个文件的三层接力

```
第①层  west.yml（清单）                self: west-commands: ext-commands.yml
第②层  ext-commands.yml（扩展描述）     west-commands:
                                         - file: scripts/hello.py    ← 指向第③层
                                           commands:
                                           - name: hello
                                             class: Hello
                                             help: 玩具扩展命令：打印一句话
第③层  scripts/hello.py（命令本体）     from west.commands import WestCommand
                                       class Hello(WestCommand):
                                           def do_add_parser(...)   ...
                                           def do_run(...)          ...
```

**一个刚从源码确认的细节**：第①层和第②层的文件路径**都相对项目根目录**（`os.path.join(project.abspath, cmd)`，commands.py:640/673）——不是相对 yml 所在目录。写扩展最容易踩的坑。

**两道安全闸**：每层解析前都调 `escapes_directory()` 检查路径没有 `../../` 逃出项目目录（:644/:676）。加上 `commands.allow_extensions=false` 总闸，一共三层防护。

## 6.3 亲手造一个（实测）

三步搭建（改 west.yml 的 self 段挂 west-commands、写 ext-commands.yml、写 hello.py）后：

```
$ west help | tail -5
extension commands from project manifest (path: manifest):
  hello:                玩具扩展命令：打印一句话      ← 出现了！
$ west hello
Hello from extension!                                        ← 真能跑
$ west config commands.allow_extensions false               ← 拉总闸
$ west hello
west: unknown command "hello"; ...                           ← 装作没看见
```

**一个值得驻足的事实**：`hello.py` 里写的正是第 1 讲见过的 `WestCommand` 协议。**扩展命令和内置命令是同一个物种**——所以它们能在同一套帮助系统、verbosity、错误处理下工作。还有一条隐式契约：工厂最后调 `cls()`——**无参构造**，你的扩展类必须支持。

## 6.4 代码现场走读

### `load_extension_specs`（main.py:388-429）

```python
if self.manifest is None:
    self.extensions = None        # ★ None ≠ {}！
```

**三态设计**：`None` = 清单没加载成功（扩展**无法确定**）；`{}` = 清单加载了、确实没有扩展；`dict` = 正常。`west help` 对三者的表现完全不同。

### `extension_commands`（commands.py:604-631）

读 `commands.allow_extensions`（默认 true）→ 遍历 `manifest.projects`，`west_commands` 非空的进 `_ext_specs`。

### `_ext_specs`（:633-670）——对每个 west-commands.yml 做五件事

```
① 拼绝对路径  ② escapes_directory 安全闸  ③ 文件不存在就跳过（项目没克隆，不算错）
④ yaml.load(SafeLoader)  ⑤ pykwalify 校验 west-commands-schema.yml
```

### `_ext_specs_from_desc`（:672-692）——造"登记卡"

`name` 和 `class` 缺省互为默认；`WestExtCommandSpec(name, project, help, factory)`——`factory` 是**欠条**。

### `_ExtFactory.__call__`（:556-582）——兑现欠条的三步

```python
sys.path.append(os.path.dirname(self.py_file))   # ① 让扩展能 import 兄弟模块
mod = _commands_module_from_file(self.py_file)   # ② 真正 import
cls = getattr(mod, self.attr)                    # ③ 捞出命令类
return cls()                                     #    无参实例化
```

每步失败都转成带 `hint` 的 `ExtensionCommandError`。

## 6.5 惰性的铁证与一个隐藏细节

**铁证**（给 hello.py 模块顶层加"写时间戳"副作用）：

```
扫描完成。此刻 hello.py 被 import 过吗？ 【没有！】     ← 第 6 讲的全部工作
工厂调用后呢？ 【import 了】                           ← spec.factory() 那一刻
```

**隐藏细节**：`sys.modules` 里**永远找不到**扩展模块。`_commands_module_from_file`（:694-721）用 `spec_from_file_location` 手工加载（这条路线**不注册**进 `sys.modules`），存进私有缓存 `_EXT_MODULES_CACHE`，起合成名 `west.commands.ext.cmd_N`。目的：①不污染 `sys.modules`；②你的代码没法 import 到扩展；③同一文件被两个命令引用时只 import 一次。

**观察练习**：缓存**查找**用 resolve 后的路径（:711-712），**写入**却用原始字符串（:719）——若传入路径非规范形式，缓存可能永远命不中。能自己发现它，说明你已经开始"审计式阅读"了。

## 6.6 影子与重名

扩展命令名**撞了内置命令** → 丢弃 + 排队警告；两个项目定义**同名扩展** → 先到者留。警告为什么排队（`queued_io`）——verbosity 此刻还没定（第 10 讲挂 hook 后再吐）。

## 本讲时间线

```
→ load_extension_specs()：扫出一张扩展登记表
    路径安全闸 → yaml → pykwalify → WestExtCommandSpec（含欠条 _ExtFactory）
    影子/重名过滤 → self.extensions = {'hello': spec, ...}
    ★ 全程零 import
```

**记住三件事**：
1. 三层接力，两处路径都相对项目根；扩展类必须**无参可构造**，实现同一个 `WestCommand` 协议
2. 惰性 = 扫描只造"欠条"；扩展模块**不进** `sys.modules`
3. 三层安全防护：`escapes_directory` ×2 + `commands.allow_extensions` 总闸

## 自测

1. 把扩展命令改名 `list`（撞内置名），`west list` 执行的是谁？
2. 项目没克隆时它声明的扩展命令去哪了？
3. `self.extensions = None` 和 `{}` 为什么必须是两个状态？

---

# 第 7 讲：别名墙贴——`load_aliases`

## 7.1 用户视角

别名住在配置的 `[alias]` 节：`west config alias.h hello` 之后，`west h` 等价 `west hello`。本质是**命令行层面的"宏替换"**。

## 7.2 代码现场：7 行主逻辑

```python
def load_aliases(self):
    if not self.config:
        return
    self.aliases = {
        k[6:]: Alias(k[6:], v) for k, v in self.config.items()
        if k.startswith('alias.')
    }
```

① 没有配置对象 → 返回；② `items()` 是第 4 讲的三层合并视图；③ 只挑 `alias.` 键；④ `k[6:]` 切掉前 6 个字符；⑤ 每个别名造一个 `Alias` 对象。就是一次带过滤的字典搬运。

## 7.3 `Alias` 类：一个"永远不会亲自执行"的命令（main.py:905-922）

```python
class Alias(WestCommand):
    def __init__(self, cmd, args):
        super().__init__(cmd, args or '<empty>',
                         f'An alias that expands to: {args}')
        self.args = shlex.split(args)                 # ①

    def do_add_parser(self, parser_adder):            # ② 伪 parser，只为 help 列表
        ...
    def do_run(self, args, ignored):                  # ③ 保险丝
        raise AssertionError("Alias command can't run directly")
```

**① `shlex.split`**：值按 shell 规则拆词，引号感知。**② 伪 parser**：永远不会真解析，只让 `west help` 的 `aliases:` 小节有东西可列。**③ 保险丝**：`raise AssertionError` 而非 `pass`——万一有代码错误地"执行"别名，立刻炸出**程序员的错误**（AssertionError 的语义是"这不该发生"）。**用异常类型区分"用户错误"和"程序员错误"**。

## 7.4 别名怎么兑现：第 9 讲展开循环的预告 + 实验证据

```python
while early_args.command_name in aliases:              # ① while → 链式！
    alias = aliases.pop(early_args.command_name)       # ② 拿一个删一个 → 防死循环
    for i, arg in enumerate(argv):                     # ③ 找到命令名 token
        if arg == early_args.command_name:
            argv = argv[:i] + alias.args + argv[i+1:]  #    替换
            break
    early_args = early_args._replace(command_name=alias.args[0])   # ④
```

**实验证据**（别名套别名：`hh = h`、`h = hello`）：

```
$ west -v hh
Replacing alias hh with ['h']        ← 第一轮循环
Replacing alias h with ['hello']     ← 第二轮（所以必须用 while！）
Hello from extension!
```

- **① `while`**：别名可以指向别名，循环展开到头
- **② `pop` 防环**：`a = b`、`b = a` 互相指——第一轮 pop 掉 a，第二轮 pop 掉 b，第三轮查 a 已被删，循环终止
- **④ `_replace`**：NamedTuple 换字段——同一机制第三次登场

**空别名**：`alias.e = ""` → `west e` 报 `west: empty alias "e"`。

## 7.5 影子实验的教训：别名可以劫持内置命令

```
$ west config alias.list hello      ← 危险实验
$ west list
Hello from extension!               ← west list 被劫持了！！
```

而 `west help` 里 `list` 依然在内置命令区，`aliases:` 小节里也列着 `list: hello`。**为什么**：① 展开循环**不检查**命令名是否内置——只要在别名表里一律展开；② `setup_parsers` 跳过与真命令重名的别名 parser——但那**只是为了 argparse 不崩溃**，不影响执行。结论：别名覆盖内置命令是**留给高级用户的口子**（源码注释确认），它既是功能也是坑——`west list` 行为诡异时记得 `west config --list | grep alias` 排查。

## 本讲时间线

```
→ load_aliases()：配置 [alias] 节 → 别名对象表
    7 行字典搬运 + Alias 对象（shlex 拆词、永不亲自执行）
→ 产出：self.aliases                       ★ 柜子填上
```

**记住三件事**：
1. 值用 `shlex.split` 拆词（引号感知）
2. `Alias` 是 WestCommand 的"只挂帮助、永不执行"用法；`do_run` 里 `AssertionError` 是保险丝
3. 展开循环三件套：`while`（链式）+ `pop`（防环）+ `_replace`；**别名可劫持内置命令**

## 自测

1. `alias.a = b` 和 `alias.b = a`，`west a` 会发生什么？
2. `alias.x = hello -v extra` 里的 `-v` 会被谁消费？
3. 为什么 `load_aliases` 用 `items()`（三级合并）而不是只读 local？

---

# 第 8 讲：搭脚手架——`setup_parsers`

## 8.1 背景知识：argparse 是什么（60 秒版）

argparse 是标准库命令行解析器：① 造解析器；② `add_argument` 声明认识什么；③ `add_subparsers(dest='command')` 挂子命令——**解析后 `args.command` 自动等于选中的子命令名**（下一讲分发的命脉）。一棵 argparse 树 = "west 认识哪些命令、每个命令认识哪些参数"的全部知识。

## 8.2 代码现场：一棵树上三种待遇（main.py:457-490）

```python
def setup_parsers(self):
    west_parser, subparser_gen = self.make_parsers()       # ① 树干
    real_command_names = set()                             #    "已被真名占用"清单

    for name, command in self.builtins.items():            # ② 内置：真注册
        real_command_names.add(name)
        command.add_parser(subparser_gen)                  #    → do_add_parser 全套

    if self.extensions:                                    # ③ 扩展：只占坑
        for specs in self.extension_groups.values():
            for spec in specs:
                real_command_names.add(spec.name)
                subparser_gen.add_parser(spec.name, add_help=False)   # ★ stub

    if self.aliases:                                       # ④ 别名：防撞名
        for name, alias in self.aliases.items():
            if name not in real_command_names:             #    重名 → 跳过
                alias.add_parser(subparser_gen)
```

| 待遇 | 在树上得到什么 | 为什么 |
|---|---|---|
| **真注册** | 完整子 parser：参数、帮助 | 模块早已 import，注册零成本 |
| **占坑** | 只有名字的 stub | 真帮助要等扩展模块 import——而 import 被刻意推迟。**树上有名字，parse 就能把 args.command 填对** |
| **防撞名注册** | 伪 parser | argparse 不允许两个同名子命令；跳过保住树，执行层的劫持不受影响 |

`real_command_names` 是排他锁：先到者（内置→扩展）登记，后来的（别名）让路。顺序刻意——内置优先级最高。

## 8.3 `make_parsers`：树干上的五个全局选项（:492-532）

```python
parser = WestArgumentParser(
    prog='west',                    # 帮助里显示 west 而非绝对路径
    add_help=False,                 # 禁用自带 -h，换自定义动作
    west_app=self,                  # 定制类持有管家引用（排版要问它要扩展/别名表）
    allow_abbrev=False)             # 拒绝前缀缩写
```

| 全局选项 | 白话 |
|---|---|
| `-h`（WestHelpAction） | **只做标记**（`namespace.help = True`），真正的帮助打印延后到 help 路由——**"先标记、后决策"** |
| `-z/--zephyr-base` | Zephyr 仓路径（第 2 讲讲过） |
| `-v/-q` | 各自 `action='count'` 分开计数，下一讲相减成净额——**两份解析器的对齐契约**（:507 注释：改了记得同步 `parse_early_args()`，还有 Zephyr 的 bash 补全脚本） |
| `-V` | argparse 内建 version action（实测：非工作区秒出版本号） |
| `dest='command'` | ★ 解析后 `args.command` 自动 = 选中的命令名 |

`allow_abbrev=False` 实测：`west --verb list` 被拒（`--verb` 不被前缀匹配成 `--verbose`）——**歧义是 CLI 之敌**。

`WestArgumentParser` 的类注释很精彩：argparse 对排版 API "*infuriatingly coy*"（令人恼火地遮遮掩掩），west 只好子类化硬改。

## 8.4 树枝：`Update` 的真注册（project.py:1062-1128）

用 `add_argument_group` 把参数**分组**：

| 参数组 | 参数 | 白话 |
|---|---|---|
| local project clone caches | `--name-cache` / `--path-cache` | 从本地缓存克隆（省流量） |
| fetching behavior | `-f/--fetch {always,smart}`、`-o/--fetch-opt`、`-n/--narrow` | fetch 策略 / 透传 git fetch / 窄拉 |
| checked out branch behavior | `-k/--keep-descendants` ★、`-r/--rebase` | 保留后代分支（优先级最高）/ rebase |
| advanced options | `--group-filter/--gf` | 临时启用/禁用项目组 |
| deprecated options | `-x/--exclude-west` | 已废弃 |

对照实测 `west update -h` 的 usage 行（`[-f {always,smart}] [-k] [-r] [PROJECT ...]`）**逐项对应**。这些 flag 现在挂上树，真正被消费在第 13 讲（`-k` 就是保住 my-work 分支的那个开关）。

## 8.5 树的全貌

`west -h` 的一屏输出 = 前八讲的**联合大检阅**：五个全局选项（make_parsers）+ 内置两组（BUILTIN_COMMAND_GROUPS）+ 扩展栏（第 6 讲扫描结果）+ aliases 栏（第 7 讲）。

## 本讲时间线

```
→ setup_parsers()：make_parsers 造树干 → 内置真注册 → 扩展占坑 → 别名防撞
→ 产出：self.west_parser（一棵完整的树）    ★ 柜子填上
```

**记住三件事**：
1. 一棵树三种待遇——差异的根源都是"此刻还缺什么"
2. `dest='command'` 是下一讲分发的命脉
3. 五个全局选项处处呼应前文：`-h` 先标记后决策、`-v/-q` 对齐契约、`allow_abbrev=False` 拒绝歧义

## 自测

1. `west -h` 的分组顺序由什么决定？
2. 扩展的 stub 为什么必须 `add_help=False`？
3. 两个扩展同名，argparse 树会撞名崩溃吗？

---

# 第 9 讲：分发中枢——`run_command`

## 9.1 代码现场全景（主干六步）

```python
def run_command(self, argv, early_args):
    # ① 别名展开（while 循环）
    # ② handle_early_arg_errors：未知名 → 友好报错
    # ③ parse_known_args → args, unknown
    # ④ log.set_verbosity（遗留对齐，一行）
    # ⑤ help 路由
    # ⑥ 分发：builtins or extensions
    #（外面裹着第 14 讲的异常阶梯）
```

## 9.2 第①步：别名展开（简述）

发生在 `parse_known_args` **之前**——所以 argparse 树**从头到尾没见过别名**，它见到的已经是展开后的真名。别名是纯 argv 层面的"预处理"。

## 9.3 第②步：未知名拦截

```python
self.handle_early_arg_errors(early_args)        # :643-663
```

命令名**既不在**内置花名册、**也不在**扩展表 → 立刻拦下用**人话**报错。实测对比：

```
【在工作区内】
west: unknown command "bogus"; workspace /tmp/west-lab does not
define this extension command -- try "west help" and "west -vv status"
【在工作区外】
west: unknown command "bogus"; do you need to run this inside a workspace?
```

**为什么不让 argparse 自己报**？argparse 原生报错是 `invalid choice: 'bogus' (choose from ...)`——技术上正确但对用户**毫无诊断价值**。west 用第 2 讲的 `command_name` + 第 3 讲的 `topdir` 拼出两种带语境的提示。工作区内的提示还呼应第 6 讲：最常见的场景是**项目没克隆**（west-commands.yml 还没被扫到）。

`print_usage_and_exit`：打印 usage 到 stderr，`sys.exit(消息字符串)`——**退出码 1**。

## 9.4 第③步：`parse_known_args`——一次解析，两种产物（本讲核心）

```python
args, unknown = self.west_parser.parse_known_args(args=argv)
```

为什么容忍"不认识"？因为 `west diff --stat` 里的 `--stat` 是 **git 的参数**——要原封不动透传（Diff/Status/Grep 开了 `accepts_unknown_args`）。而 update 没开，多余的 unknown 在第 11 讲闸门被拒。

**`-vvv` 偷看最终 args 对象**（实测，来自第 10 讲排队的调试钩子）：

```
args namespace: Namespace(
    help=None,            ← -h 的"标记"位
    zephyr_base=None,
    verbose=3, quiet=0,   ← argparse 侧分开计数（净额=3）
    command='list',       ← ★ dest='command' 的成果
    all=False, inactive=False,          ← 以下是 list 自己的字段
    manifest_path_from_yaml=False,
    format='{name:12} {path:28} ...',
    projects=[])
```

一个 Namespace 里**全局选项和子命令自己的参数和平共处**——树干字段 + 走过的树枝字段合并。**分发和后续执行所需的全部信息，此刻都装在这一个对象里。**

## 9.5 第④⑤⑥步

**④** `log.set_verbosity(args.verbose - args.quiet)`——净额契约在此兑现（遗留日志模块）。**⑤** help 路由：`args.help or args.command is None` → 改道 help 命令（`-h` 的"先标记后决策"第四次登场；`args.command_name = args.command` 记住用户想问谁）。**⑥** 分发：

```python
try:
    if args.command in self.builtins:        # 查第 1 讲的花名册字典
        self.run_builtin(args, unknown)      # ← west update 走这里！
    else:
        self.run_extension(args.command, argv)
except KeyboardInterrupt: ...                # ← 第 14 讲的异常阶梯
...
```

三个细节：**为什么 `in 字典` 而不是 if-elif 链**（O(1) 查表，第 1 讲的答案兑现）；**`self.cmd` 在两分支都会被赋值**（except 块要用它收拾场面）；**`run_extension` 一瞥**——`factory()` 兑现第 6 讲的欠条、**重建全新 parser 树**（stub 留下的脏状态）、还有源码自认的 HACK `set_zephyr_base`。

## 本讲时间线

```
→ run_command：① 别名展开 ② 未知名拦截 ③ parse_known_args
              ④ 遗留对齐 ⑤ help 路由 ⑥ 'update' ∈ builtins → run_builtin ★点名！
```

**记住三件事**：
1. 别名展开和未知名拦截都在 parse 之前——前者让树不必认识别名，后者让报错带语境
2. `parse_known_args` 劈两半：args（全局+子命令全字段）+ unknown（透传或闸门拒绝）
3. `args.command` 是分发的唯一依据

## 自测

1. 别名展开为什么必须在 parse 之前？（`args.command` 会是 'hh'——查得到吗？）
2. `west -v -q list` 的 verbose/quiet 各是多少？
3. `west bogus` 和 `west list --bogus` 各死在哪道闸？

---

# 第 10 讲：点名的善后——`run_builtin`

## 10.1 代码现场：六行主流程（main.py:685-698）

```python
def run_builtin(self, args, unknown):
    self.queued_io.append(
        lambda cmd: cmd.dbg('args namespace:', args,
                            level=Verbosity.DBG_EXTREME))     # ①
    self.cmd = self.builtins.get(args.command,
                                 self.builtins['help'])       # ②
    adjust_command_verbosity(self.cmd, args)                  # ③
    if self.mle:                                              # ④ ★本讲主体
        self.handle_builtin_manifest_load_err(args)
    for io_hook in self.queued_io:                            # ⑤
        self.cmd.add_pre_run_hook(io_hook)
    self.cmd.run(args, unknown, self.topdir,                  # ⑥ → 第 11 讲
                 manifest=self.manifest, config=self.config)
```

① 排队 args dump（`-vvv` 可见）；② 选定命令（help 兜底是防御性保险）；③ **调音量**：INF(3) + v数 - q数，`max(min(...))` 双向夹紧到 [QUIET=0, DBG_EXTREME=6]；④ mle 雷引爆；⑤ 排队消息挂 hook；⑥ 三件套注入。

## 10.2 大件：坏清单的裁决——`handle_builtin_manifest_load_err`（:305-386）

### 白名单：六个"坏清单也能跑"的命令

```python
no_manifest_ok = ['help', 'config', 'topdir', 'init', 'manifest', 'update']
```

`update` 为什么在内？作者注释（:311-315）翻译：*"update 是修复'某个被 import 项目的 manifest-rev 指向坏清单'的**唯一途径**。"*（场景：项目 A 的旧版 west.yml 是坏的，把 A 升到新版就好——但升级 A 本身需要 `west update A` 先能跑。）

### 完整决策树

```
self.mle 非 None？
 ├─ ManifestVersionError（清单版本比 west 新）？
 │    ├─ help → 警告，照常跑     ├─ config/topdir → 警告，照常跑
 │    ├─ init → 放行             └─ 其他 → die，建议升级 west
 └─ 其他异常，且命令不在白名单 → 按类型生成 die 消息（闭包排队）：
      MalformedManifest/MalformedConfig → "can't load west manifest: ..."
      _ManifestImportDepth → "import 环"（提示 west -v manifest --resolve）
      ManifestImportFailed → die……★除非命令是 update：直接 return！
      FileNotFoundError → "manifest file not found" + 教你查 .west/config
```

### 三个死法的实验对照（核心证据）

把 west.yml 弄坏（TAB 缩进 → ScannerError → MalformedManifest）后：

| 命令 | 白名单 | 实测结果 | 死在哪 |
|---|---|---|---|
| `west list` | ✗ | `FATAL ERROR: can't load west manifest: ...` exit 1 | **mle 闸门**（诊断闭包排队成 hook，do_run **从未执行**） |
| `west topdir` | ✓ | 照常工作 | 不死——根本不碰清单 |
| `west update` | ✓ | `FATAL ERROR: Malformed manifest file: ...`（**没有 "can't load" 前缀**）exit 1 | 过闸门，死于 **update_all 的重解析**，第 14 讲的 `except MalformedManifest` 接住 |

**update 那行的前缀差异是铁证**：它死于另一处 die 点——白名单给了它"先跑起来试试"的机会。

**FileNotFoundError 变体**（manifest.file 指错）的报错是用户教程级的：把藏宝图写的什么、实际找的哪、去哪改一次说清。

## 10.3 意外收获：本系列第 3 处真实缺口

第一组实验里 `west topdir` 炸出**完整 traceback**。排查：未闭合 `[` 产生 `yaml.parser.ParserError`（语法层），而 `manifest.py:211-215` 的 `_load` 只捕获 `yaml.scanner.ScannerError`（词法层）：

```python
except yaml.scanner.ScannerError as se:      # ← 只认这一种
    raise MalformedManifest(se) from se
```

ParserError 逃出六异常元组，一路裸奔到进程顶层。**读源码的一课**：看到 `except (A, B, C...)` 的枚举式捕获，永远问一句"**这个枚举全吗**"。本系列至此发现三处：:1422 少括号、:1212 缺 f 前缀、:213 只捕 ScannerError。

## 10.4 排队消息机制闭环

| 消息 | 排队时间 | 为什么要排队 |
|---|---|---|
| args dump | 本讲 ① | 等命令实例存在后才能用它的 dbg |
| 影子/重名警告 | 第 6 讲 | verbosity 未定 |
| 别名替换 dbg | 第 7/9 讲 | 同上 |
| mle 诊断 | 本讲 ④ | 要在命令自己的 verbosity 上下文里吐 |

统一答案：**verbosity 直到 ③ 才确定，命令实例直到 ② 才存在**。延迟输出 = 延迟决策。

## 本讲时间线

```
run_command → run_builtin：① args dump ② self.cmd=Update ③ 音量夹紧
                          ④ mle 裁决 ⑤ 排队消息挂 hook ⑥ cmd.run → 第 11 讲
```

**记住三件事**：
1. 白名单六命令；update 在内因为它是**修复坏 import 的唯一途径**——死于更深处，消息前缀都不一样
2. 排队消息的存在理由：verbosity 和命令实例**到位太晚**
3. `except` 枚举要审完备性——ScannerError/ParserError 之别让一种坏 YAML 裸奔 traceback

## 自测

1. 清单坏时 `west config manifest.file west.yml` 为什么必须能跑？
2. `west -vv -qq update` 最终 verbosity 是几？
3. ManifestVersionError 为什么单独处理？

---

# 第 11 讲：成人礼——`WestCommand.run` 三件套注入与两道闸门

## 11.1 代码现场逐行（commands.py:171-200）

```python
def run(self, args, unknown, topdir, manifest=None, config=None) -> None:
    self.config = config                                            # ①
    if unknown and not self.accepts_unknown_args:                   # ② 闸门一
        self.parser.error(f'unexpected arguments: {unknown}')
    if not topdir and self.requires_workspace:                      # ③ 闸门二
        self.die(_no_topdir_msg(os.getcwd(), self.name))
    self.topdir = os.fspath(topdir) if topdir else None             # ④
    self.manifest = manifest
    for hook in self._hooks:                                        # ⑤
        hook(self)
    self.do_run(args, unknown)                                      # ⑥
```

| # | 白话 |
|---|---|
| ① | **config 第一个注入**——后面 ③ 的 `die()` 要查 `color.ui`，config 没先到位 die 自己就崩。**顺序即依赖** |
| ② | **闸门一（多余参数）**：`parser.error`——**退出码 2**（argparse 惯例：用法错误=2，区别于运行错误的 1） |
| ③ | **闸门二（工作区）**：第 3 讲悬案的**宣判** |
| ④ | **三件套注入完成** |
| ⑤ | **hooks 环节**：第 10 讲挂上的排队消息按序、以正确 verbosity 吐出 |
| ⑥ | `do_run`——命令自己的逻辑开跑 |

## 11.2 两道闸门的实验矩阵（含一个意外发现）

### 闸门一

```
$ west update --bogus
west update: error: unexpected arguments: ['--bogus']    (exit=2)
```

### 闸门一的设计意图面 + 互操作怪癖

Diff/Status/Grep 开 `accepts_unknown_args=True` 让 `west diff --stat` 的 `--stat` 转交 git。但实测挖出一个**真实的互操作怪癖**：

```
$ west diff --bogus
Empty diff in 4 projects.    (exit=0)     ← 错误被静默吞掉了！
```

`-vv` 追踪真相：`--bogus` 确实传给了 git；**git 2.34 在 `--exit-code` 模式下，遇到非法选项返回 0**、错误只写 stderr（单独验证：不带 `--exit-code` rc=255，带上就是 0）；west 的 diff 逻辑"rc==0 且 stdout 空 → 无差异"，stderr 里那行 git 报错**没人看**。

**两条教训**：`check=False` + 纯返回码判断**依赖子进程退出码语义的可靠性**；`-vv`（回显子进程命令+输出）是排查这类问题的第一工具。本系列第 4 个真实问题。

### 闸门二

```
【/var 下】
$ west update     → FATAL ERROR: no west workspace found from "/var";
                    "west update" requires one.  + 三条自救建议（含 ZEPHYR_BASE）
$ west config --list  → 照常运行（requires_workspace=False）
```

同一目录两种命运——差别只在命令构造时登记的一个布尔值。

## 11.3 三件套注入：一个命令的自给自足

闸门过后，Update 实例身上有了 `self.topdir / self.config / self.manifest / self.args`——**命令对环境的一切需求都在自己身上**。这就是为什么扩展命令只要实现 `do_add_parser`/`do_run` 就能干活：**插件的"平等待遇"是这套注入机制给的**。

## 11.4 hooks 清账与高速公路全景

| 消息 | 产生 | 真正打印 |
|---|---|---|
| "Replacing alias…" | 第 9 讲 | 本讲 ⑤ |
| 影子/重名警告 | 第 6 讲 | 本讲 ⑤ |
| args dump | 第 10 讲 | 本讲 ⑤（`-vvv`） |
| "can't load west manifest" | 第 10 讲 | 本讲 ⑤（die 闭包，do_run 从未执行） |

**所有命令都走同一条 ⓵–⑪ 高速公路**（见文首总览图），只是 ⑪ 之后各奔东西——这就是为什么读 west 源码要先吃透 main.py + commands.py：**一半的"混乱"其实是共享样板**。

## 本讲时间线

```
run_builtin ⑥ → cmd.run：① config 先行 ② 闸门一(exit 2) ③ 闸门二(exit 1)
                        ④ 三件套注入 ⑤ hooks 清账 ⑥ do_run → Update 接管
```

**记住三件事**：
1. 注入顺序即依赖：**config 必须第一个**；三件套齐了之后命令（含扩展）完全自给自足
2. 两道闸门两种退出码：`parser.error`→**2**、`die`→**1**
3. `check=False`+返回码判断依赖子进程语义——git 的 `--exit-code` 怪癖让 `west diff --bogus` 错误被吞

## 自测

1. 为什么 `west diff` 的设计里 `check=False`？（`--exit-code` 下 rc=1 是"有差异"这个正常结果）
2. 扩展命令和内置命令在 ⑪ 这站的待遇差在哪？（没有差）
3. 闸门一走 parser.error（2）、闸门二走 die（1）——为什么不用同一个？

---

# 第 12 讲：进入 update 领地——`do_run` → `init_state` → `update_all`

## 12.1 `do_run` 三行（project.py:1130-1140）

```python
def do_run(self, args, _):
    self.die_if_no_git()          # shutil.which('git')，结果缓存
    self.init_state(args)
    if not self.args.projects:
        self.update_all()         # 无项目名 → 全量
    else:
        self.update_some()        # 指定项目 → 受限模式
```

签名里的 `_` 是 unknown（闸门一保证恒空）——"我发誓不用它"的命名惯例。

## 12.2 `init_state`：把"用户意图"落到实例字段（:1142-1176）

```python
self.narrow = args.narrow or config.getboolean('update.narrow')    # CLI 优先于配置
self.sync_submodules = config.getboolean('update.sync-submodules', default=True)
# --group-filter 逐项校验：必须 +/- 开头且是合法组名，支持逗号分隔
self.fs = self.fetch_strategy()
```

**`args.xxx or config.get(...)` 是"命令行 > 配置文件 > 默认值"的惯用写法**。`fetch_strategy`（:1311-1322）对非法配置的态度是**警告+忽略+回退**（实测：`WARNING: ignoring invalid config update.fetch=bogus; choices: always, smart`）——对"用户偏好类"配置能救则救（对比第 5 讲：**清单**写错必须死——那是声明数据）。

## 12.3 本讲核心：`update_all` 为什么要"清单二次解析"

### 鸡生蛋（第 5 讲的伏笔）

项目的 `import:` 从该仓库 git 的 manifest-rev 读——项目没克隆时读不到。

### 钥匙（:1178-1192）

```python
self.manifest = Manifest.from_file(
    importer=self.update_importer,            # ★ 回调函数
    import_flags=ImportFlag.FORCE_PROJECTS)   # ★ 强制项目 import 走回调
```

`update_importer`（:1209-1244）：

```python
def update_importer(self, project, path):
    ...
    self.update(project)                                  # ★ 先把被导入的项目 update 到位
    self.updated.add(project.name)
    return _manifest_content_at(project, path, ...)       # ★ 再读它的 west.yml
```

完整的动态：解析清单 → 遇到项目 A 的 import → **不读磁盘**，调回调 → update(A) 到清单指定 revision → 读 A 的 manifest-rev 上的 west.yml → 递归解析 A 的清单 → A 里还有 B 的 import？→ 再来一层……**递归发生在"清单解析"层，每层先把项目钉到固定 revision 再读内容**——链无环就走得到头。

**实验铁证**（`west -vv update` 数 `DEBUG: loading`）：

```
loading west.yml        ← 第 5 讲：第一次解析
loading extra.yml
loading west.yml        ← ★ update_all 的第二次解析！
loading extra.yml
```

## 12.4 遍历循环：三行 continue 各跳过谁（:1194-1207）

```python
failed = []
for project in self.manifest.projects:
    if (isinstance(project, ManifestProject) or
            project.name in self.updated):        # 跳过①
        continue
    try:
        if not self.project_is_active(project):   # 跳过②
            self.dbg(f'{project.name}: skipping inactive project')
            continue
        self.update(project)                      # ★ → 第 13 讲
        self.updated.add(project.name)
    except subprocess.CalledProcessError:
        failed.append(project)                    # ★ 失败不中断，只记账
self._handle_failed(self.args, failed)
```

| 跳过 | 谁 | 为什么 |
|---|---|---|
| ①a | ManifestProject | **west update 从不修改清单仓本身**——multirepo 的"宪法" |
| ①b | `name in self.updated` | 已被 importer 提前 update 过的 |
| ② | 未激活 | group-filter 禁用的（只打 dbg，默认静默） |

## 12.5 `update_some` 的限制（:1246-1309）

只允许**清单仓直接定义**的项目，两步验证：`IGNORE_PROJECTS` 解析查名 → 不在则完整解析再查 → 是 import 来的 die："Only plain \"west update\" can currently update them."。实测：`west update lib` ✓（"HEAD is now at lib v3"）；`west update nosuch` → 提示 `west list`。

**为什么拒绝**？作者注释诚实相告：被 import 项目的更新语义（要不要先强推导入者？）**没设计好，先不做**——一个明说"我没设计好"的边界。

## 本讲时间线

```
Update.do_run：die_if_no_git / init_state
  update_all：★ 清单二次解析（先 update 再读）→ 遍历三跳过 → update(project)
              失败聚合不中断
```

**记住三件事**：
1. **清单被解析两次**；importer 的语义是"先 update 项目、再读它的清单"——鸡生蛋的钥匙
2. 遍历三跳过：清单仓自己（宪法）、importer 已处理的、group-filter 禁用的
3. update_some 只认清单仓直系项目——"语义没设计好，先不做"

## 自测

1. 为什么 self import 在两次解析里都从**文件系统**读？
2. "skipping inactive project" 要几个 v 才看得见？
3. import 链上项目 A 新版清单删掉了项目 B——B 还会被 update 吗？已克隆的 B 目录怎么办？

---

# 第 13 讲：west 的灵魂——每项目的 git 八步序列 `update()`

## 13.1 灵魂前置：三空间解耦

```
 项目仓（lib/）的 git ref 空间，三个互不侵犯的领地：

 refs/heads/manifest-rev ──► ● v5      「清单的意图」（west update 唯一有权移动）
 refs/west/*             ──► (临时)    「fetch 的中间态」（用完即删）
 HEAD + 你的分支          ──► ● 你的提交 「用户领地」（west 只挪 HEAD 到 detach，分支不动）
```

**“清单想要什么”记在 manifest-rev 上，“你正在做什么”原地不动**，两者关系（祖先关系）最后才裁决。八步就是这张图的逐行翻译。

## 13.2 八步序列 + `-vv` 实测对照

| 步 | 代码函数 | 干什么 |
|---|---|---|
| 1 | `ensure_cloned`→`init_project` | 没克隆就 `git init` + `remote add` |
| 2 | `set_new_manifest_rev` | smart 策略免 fetch 短路 |
| 3 | `fetch` | 拉取目标 revision |
| 4 | `_update_manifest_rev`(:2136) | **移动 manifest-rev**（原子） |
| 5 | `clean_refs_west` | 清理中间态 ref |
| 6 | `ensure_head_ok` | 修复悬空 HEAD |
| 7 | `decide_update_strategy` + 三选一 | 策略裁决 |
| 8 | `update_submodules` | 子模块递归更新 |

**实测的 10 条命令逐条认领**（`west -vv update lib` 抓取）：

```
'git rev-parse --show-cdup'                    ← 步1：is_cloned 探测
'git cat-file -t main'                         ← 步2：smart 判定（'main' 本地是 tag/commit 吗）
'git fetch -f --tags -- <url> main'            ← 步3：fetch（非SHA路径）
'git rev-parse FETCH_HEAD^{commit}'            ← 步3尾：解析目标 SHA
'git update-ref -m "west update: moving to ..." refs/heads/manifest-rev <sha>'   ← 步4 ★
'git for-each-ref ...'                         ← 步5：枚举 refs/west/*
'git show-ref --quiet --head /'                ← 步6：HEAD 体检
'git rev-parse <manifest-rev>'                 ← 步7前置：意图指针换 SHA
'git rev-parse --abbrev-ref HEAD'              ← 步7：当前在分支上吗
'git checkout --detach <sha>'                  ← 步7收尾：默认策略
```

**步 4 的 reflog 铁证**：

```
4cc60bc refs/heads/manifest-rev@{0}: west update: moving to 4cc60bc...
0601993 refs/heads/manifest-rev@{1}: west update: moving to 0601993...
```

## 13.3 逐步详解

### 步 1：`init_project`——克隆的"白手起家"版

```python
init_cmd = ['init', project.abspath]
if self.git_version_info >= (2, 28, 0):
    init_cmd.insert(1, '--initial-branch=init_placeholder')   # ★
project.git(init_cmd, cwd=self.topdir)
project.git(['remote', 'add', '--', project.remote_name, project.url])
```

west **不用 `git clone`**：`init` + `remote add` + 照常 fetch。`--initial-branch=init_placeholder` 是妙笔：**不让 git 按用户本机配置猜分支名**——west 不用默认分支（detached HEAD + manifest-rev），猜出来的名字只会造成跨机器不一致。占位名就是个"没人会爱它"的名字。

### 步 2：smart 免 fetch 短路

`git cat-file -t main` 问："revision 在**本地**是什么类型？"——是 tag/commit（SHA 写死、或 tag 早拉过）则**跳过 fetch** 直接 update-ref。这就是 `smart` 的"能免则免"。

### 步 3：fetch 的 refspec 分叉（最值得琢磨）

```python
if _maybe_sha(rev) and not self.narrow:
    refspec = f'refs/heads/*:{QUAL_REFS}*'       # 'refs/heads/*:refs/west/*'
else:
    refspec = project.revision                    # 直接 fetch 那个 ref
    next_manifest_rev = 'FETCH_HEAD^{commit}'
```

**非 SHA**：直接 fetch，取 `FETCH_HEAD^{commit}`（保证是提交而非 tag 对象）。**SHA**：git 默认**不许 fetch 裸 SHA**（需服务器开 `uploadpack.allowReachableSHA1InWant`）——west 把远端全部分支拉进 `refs/west/*` 暂存（目标 SHA 一定在历史里），**顺带给步 7 的祖先判断备好完整后代信息**。用完即删（步 5）。

### 步 4：移动意图指针

`git update-ref -m 'west update: ...'` 是**程序化移动 ref 的正规通道**（比"checkout 再记录"原子得多）；`-m` 留言进 reflog——将来排查"manifest-rev 怎么指到这了"一查便知。

### 步 5–6：清理与体检

删 `refs/west/*`（平时 `git show-ref` 看不到它们的原因）；HEAD 悬空则 `checkout --detach refs/heads/manifest-rev` 扶正。

### 步 8：子模块

`git submodule sync --recursive` + `update --init [--rebase] --recursive`（`update.sync-submodules` 默认 true）。

## 13.4 步 7 展开：策略三选一（代码 + 实验对照）

```python
current_branch, is_ancestor, try_rebase = self.decide_update_strategy(project, sha, ...)
#   'git rev-parse --abbrev-ref HEAD' → 在分支上吗
#   在分支上 → is_ancestor_of(sha, current_branch) → 新 sha 是你分支的祖先吗

if self.args.keep_descendants and is_ancestor:        # ①
    # 后代分支被检出且要求保留 → 什么都不做（连 HEAD 都不挪）
elif try_rebase:                                       # ②
    project.git('rebase ' + QUAL_MANIFEST_REV)         # --rebase 且在分支上
else:                                                  # ③ 默认
    project.git(['checkout', '--detach', sha])         # 挪 HEAD，绝不碰分支
    self.post_checkout_help(...)                       # 附精确救援命令
```

**实验对照**：

```
【D1：默认策略】my-work2 基于 v4，远端到 v5
  → 走③：checkout --detach v5 + post_checkout_help
  实测：
    HEAD is now at dfb32fa lib v5
    WARNING: left behind lib branch "my-work2"; to rebase onto the new HEAD:
      git -C lib rebase dfb32fa2... my-work2      ← 救援命令精确到 SHA
  现场：my-work/my-work2 原封不动，只是 HEAD 挪走了

【D2：--keep-descendants】my-work2 rebase 到 v5 之上（分支领先）
  → 走①：什么都不做
  实测：west update: left descendant branch "my-work2" checked out
  现场：## my-work2（HEAD 留在你的分支上）
```

**优先级链**：`--keep-descendants`（且是祖先）> `--rebase` > 默认 detach。共同底线：**你的分支对象永远不被删除、不被改写**。

一个实测细节：HEAD 是 detached 时，`abbrev-ref HEAD` 返回 `'HEAD'`（不在分支上）→ **连祖先判断都不做**，直接走③——策略路径随仓库状态变化，`-vv` 的命令序列就是路径的脚印。

## 13.5 彩蛋：第 1422 行 bug 的家

```python
if take_stats:
    stats['get current status'] = perf_counter - start    # ← 少一对括号！
```

`perf_counter`（函数对象）减 float 必然 TypeError——但只有 `--stats` 且走到"保留后代分支"分支才触发。**本系列第 1 号真 bug**。

## 本讲时间线

```
self.update(project)：
  ① ensure_cloned ② smart 短路 ③ fetch（SHA/非SHA 分叉）
  ④ update-ref -m manifest-rev ⑤ 清 refs/west ⑥ HEAD 体检
  ⑦ 策略三选一 ⑧ 子模块        CalledProcessError → 记账不中断
```

**记住三件事**：
1. **三空间**：manifest-rev（意图）/ refs/west/*（中间态）/ HEAD+分支（领地）
2. SHA revision 走 `refs/heads/*:refs/west/*` 全量暂存：既绕过"git 不许 fetch 裸 SHA"，又备好祖先判断的后代信息
3. 策略优先级 `--keep-descendants > --rebase > detach`；默认只挪 HEAD，附精确到 SHA 的救援命令

## 自测

1. 为什么 `init_project` 不用 `git clone`？
2. revision 写 SHA 时，步 7 的祖先判断为什么**特别依赖**步 3 的全量 refspec？
3. `post_checkout_help` 的救援命令为什么带**完整 SHA** 而非 `manifest-rev`？

---

# 第 14 讲：退场——失败聚合、异常阶梯与退出码

## 14.1 失败结算：`_handle_failed`（project.py:92-106）

```python
def _handle_failed(self, args, failed):
    if not failed:
        self.dbg(f'git {self.name} failed for zero project')   # ① 全部成功
        return
    elif len(failed) < 20:                                     # ② <20：逐个报名
        s = 's:' if len(failed) > 1 else ''
        projects = ', '.join(f'{p.name}' for p in failed)
        self.err(f'{self.name} failed for project{s} {projects}')
    else:                                                      # ③ ≥20：见上方日志
        self.err(f'{self.name} failed for multiple projects; see above')
    raise CommandError(1)                                      # ④ 唯一退出通道
```

**20 是个体贴的阈值**：大工作区里点名五十个没意义。**实验解读**（把 lib 的 URL 指向不存在的仓库）：

```
=== updating dup (dup):        ← 三个项目全部尝试（失败不中断）
=== updating extra (extra):
=== updating lib (lib):
ERROR: update failed for project lib      （exit=1）
还原后全部成功 exit=0
```

**实验里的复习彩蛋**：sed 把 west.yml 里 `lib` 和 `dup` 两行的 URL 都改了，为什么只有 lib 失败？——**dup 的生效定义来自 extra.yml**（self 导入优先级更高），west.yml 里那行是被忽略的影子。结算发生在**全部项目跑完之后**：dup/extra 先成功，lib 失败不影响它们。

## 14.2 异常阶梯合龙（main.py:585-641）

第 9 讲分发时埋的 `try`，此刻逐层接住所有冒泡异常。**顺序本身是设计**（子类必须排在父类前面）：

```python
except KeyboardInterrupt:
    if platform.system() == 'Windows':
        CONTROL_C_EXIT_CODE = 0xC000013A - 2**32        # ①
        sys.exit(CONTROL_C_EXIT_CODE)
    else:
        signal.signal(signal.SIGINT, signal.SIG_DFL)    # ②
        os.kill(os.getpid(), signal.SIGINT)
except BrokenPipeError:
    sys.exit(0)                                          # ③
except CalledProcessError as cpe:                        # ④
    self.cmd.err(f'command exited with status {cpe.returncode}: '
                 f'{quote_sh_list(cpe.cmd)}', fatal=True)
    sys.exit(cpe.returncode)
except ExtensionCommandError as ece:                     # ⑤
    self.handle_extension_command_error(ece)
except CommandError as ce:                               # ⑥
    sys.exit(ce.returncode)
except MalformedManifest as mm:                          # ⑦
    self.cmd.die('\n  '.join(str(arg) for arg in mm.args))
except WestNotFound as wnf:                              # ⑧
    self.cmd.die(str(wnf))
```

**② POSIX 的 Ctrl-C 是本阶梯最讲究的一段**。为什么不直接 `sys.exit(130)`？因为 shell 对**"死于信号"**和**"退出码 130"**区别对待：前者会让 `while true; do west update; done` **整体退出**，后者只结束当次迭代。所以 west：**恢复默认信号处理（SIG_DFL），给自己补一刀 SIGINT**——让进程真正"死于信号"。作者注释连参考都给了：CPython `exit_sigint()` 的纯 Python 复刻，源头 bpo-1054041。

**① Windows 版**：`0xC000013A` = `STATUS_CONTROL_C_EXIT`；减 `2**32` 是塞进 int32 的惯例。

**③ BrokenPipeError → 0**：`west list | head -1` 时 head 关管道——不是错误，礼貌退场。

**④ CalledProcessError**：**git 的退出码原样透传**，报文附完整命令行（`quote_sh_list`——第 1 讲那个"只用于显示"的引号函数）。

**⑤ 扩展失败**：`-vvv` 打栈，**否则 traceback 落盘临时文件**并告知路径——不刷屏又留证据。

**⑥ CommandError 静默退出**：命令自己已经把错误打完（`_handle_failed` 先 err 再 raise），再复述就是复读机。⑤ 必须排在 ⑥ 前（子类先接）。

**⑦ MalformedManifest**：第 10 讲白名单的最终保障——update 带坏清单死于重解析处，被这里接住。

## 14.3 退出码语义总表（实测 + 代码佐证）

| 场景 | 退出码 | 证据 |
|---|---|---|
| 全部成功 | **0** | 实测 |
| 项目失败聚合 | **1** | 实测 |
| 用法错误（闸门一 parser.error） | **2** | 实测（argparse 惯例） |
| 未知名命令 | **1** | 实测 |
| die()（含 WestNotFound/MalformedManifest） | **1** | 第 10/11 讲 |
| git 子进程失败 | **= git 的返回码** | :626 |
| 扩展命令失败 | `ece.returncode` | :455 |
| Ctrl-C（POSIX） | **死于 SIGINT**（显示 130） | :616-617 |
| Ctrl-C（Windows） | `0xC000013A - 2**32` | :603-604 |
| 管道断裂 | **0** | :618-619 |
| die() 且 -vvv | 改抛 RuntimeError | commands.py:511-524 |

**用法错误 2 / 运行错误 1** 的区分是刻意的：脚本作者可以区分"我的调用方式错了"和"环境/数据出了问题"。

## 14.4 出口：回到第 1 讲的那扇门

```
CommandError(1)
  → 冒泡到本阶梯 ⑥ → sys.exit(1)
  → SystemExit 向上穿透 app.run / main
  → 第 1 讲的 pip 胶水脚本 sys.exit(main()) 处——首尾呼应，闭环
  → 操作系统收到退出码，终端回到提示符
```

## 14.5 系列结语：读源码途中发现的 4 处真实问题

| # | 位置 | 问题 |
|---|---|---|
| 1 | project.py:1422 | `perf_counter - start` 少括号（`--stats --keep-descendants` 触发） |
| 2 | project.py:1212 | `die("... {project.abspath} ...")` 缺 f 前缀 |
| 3 | manifest.py:213 | 只捕 `ScannerError`，`ParserError` 型坏 YAML 裸奔 traceback |
| 4 | git 2.34 互操作 | `--exit-code` 模式下非法选项返回 0，`west diff --bogus` 错误被吞 |

读源码的额外奖赏：**bug 是最诚实的文档**——每一处都精确标出了"作者没测到的路径"。

## 最终自测

1. 为什么 `_handle_failed` 抛 `CommandError(1)` 而不是直接 `sys.exit(1)`？（直接 exit 会跳过异常阶梯——它还能打日志/落盘吗？）
2. `west update | head -1` 和 Ctrl-C 中断的退出码各是几？为什么管道断裂"不算错误"？
3. 把 ⑦ MalformedManifest 从阶梯删掉，update 带坏清单跑会发生什么？（它继承自谁？会被 ⑥ 接住吗？退出码变吗？）

---

*实验环境：Ubuntu 22.04 / git 2.34.1 / west 1.4.0（pip 安装）+ 玩具工作区（3 个 bare 仓 + 本地清单仓，路径 `/tmp/opencode/west-lab`）。全部命令与输出为 2026-10-09/12 实测；行号基于 commit `746e1b19`。*
