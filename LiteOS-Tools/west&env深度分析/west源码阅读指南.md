# west 源码阅读指南：写给"会 Python 但看不懂 west"的你

> 撰写日期：2026-10-09 ｜ 代码基线：west v1.4.0
> 定位：本文是《west实现机制深度分析.md》（架构总结）和《west实现机制图解.md》（图解速查）的**前置读物**。
> 三份文档的关系：**先读本文入门 → 用图解版建立全局 → 深度分析版当字典查**。
> 本文所有实验命令均已在 west 1.4.0 + git 2.34 上亲手验证。

---

## 0. 先说结论：你看不懂，不是你的问题

"我了解 Python 语法，但看 west 源码很混乱"——这句话里藏着三个真实原因，**没有一个是 Python 语法**：

| # | 真实原因 | 占比感受 | 解药 |
|---|---|---|---|
| 1 | **缺领域知识**：west 的代码是对"git 多仓协作"的编码。不知道 refs、update-ref、refspec，看 `project.py` 就像看天书 | ★★★★★ | §1 先当用户 + §2 git 速成 |
| 2 | **不知道代码在优化什么**：不理解"west 为什么存在"，就看不懂它为什么把简单的事（拉代码）写得这么绕 | ★★★ | §1 的实验 D 会让你顿悟 |
| 3 | **代码模式非常规**：递归构造 + 共享上下文、`NamedTuple._replace`、惰性工厂、延迟错误——语法书里不讲这些"打法" | ★★★ | §5 拦路虎拆解（每个配可运行玩具代码） |

另外还有一个纯技术性的原因：**阅读顺序错了**。`manifest.py` 有 2784 行，不能从第一行顺读到最后一行；主流程还藏在 `main.py` 的中段（前 200 行都是边角处理）。§4 给出经过设计的 6 站阅读路线。

---

## 1. 第一步：先当 30 分钟 west 用户（一行源码都不读）

读代码前必须先建立"这个工具到底在干什么"的肌肉记忆。下面这套玩具实验**全部可复制粘贴运行**（已验证）。

### 1.1 搭建玩具工作区（5 分钟）

设计：3 个本地目录模拟真实世界的多仓协作——`remote/` 是"服务器"上的裸仓，`manifest/` 是清单仓，`work-lib/` 是同事的开发机。

```bash
LAB=~/west-lab   # 实验场，随便放哪
rm -rf $LAB && mkdir -p $LAB/remote $LAB/manifest $LAB/work-lib $LAB/work-app

# 1. 造两个"远端服务器"上的裸仓
git init -q --bare -b main $LAB/remote/lib.git
git init -q --bare -b main $LAB/remote/app.git

# 2. 造内容并推上去（模拟"同事已经推送了代码"）
cd $LAB/work-lib && git init -q -b main
echo "lib v1" > lib.txt && git add . && git commit -qm "lib v1"
git remote add origin $LAB/remote/lib.git && git push -q origin main

cd $LAB/work-app && git init -q -b main
echo "app v1" > app.txt && git add . && git commit -qm "app v1"
git remote add origin $LAB/remote/app.git && git push -q origin main

# 3. 写清单：声明这个工作区由哪几个仓组成
cd $LAB/manifest && git init -q -b main
cat > west.yml <<EOF
manifest:
  version: "1.2"
  projects:
  - name: lib
    url: $LAB/remote/lib.git
    revision: main
  - name: app
    url: $LAB/remote/app.git
    revision: main
EOF
git add . && git commit -qm "manifest v1"
```

### 1.2 初始化 + 更新

```bash
cd $LAB
west init -l manifest     # -l：围绕本地已有的清单仓建工作区（.west 建在 manifest 旁边）
west update               # 克隆/更新清单里声明的所有项目
west list                 # 列出工作区里的项目
```

实际输出（`west list`）：

```
manifest     manifest                     HEAD                                     N/A
lib          lib                          main                                     /home/you/west-lab/remote/lib.git
app          app                          main                                     /home/you/west-lab/remote/app.git
```

注意 `manifest` 这一行：清单仓自己也是工作区的一个"项目"（这就是源码里 `ManifestProject` 的由来）。

### 1.3 实验A：west 克隆的仓库和普通 clone 有什么不一样？★

这是理解 west 全部设计的钥匙：

```bash
cd $LAB/lib
git show-ref                          # 这个仓库有哪些 ref？
git status -sb | head -1              # HEAD 在哪？
```

实际输出：

```
cc4b2623... refs/heads/manifest-rev   ← 只有这一个 ref！
## HEAD (no branch)                   ← detached HEAD
```

对比你自己 `git clone` 的仓库：会有一堆 `refs/remotes/origin/*`、HEAD 挂在 `main` 上。而 west 克隆的仓库：

- **只有一个本地分支 `manifest-rev`**，指向"清单说我该在的提交"
- **没有任何 remote-tracking 分支**（west 用显式 refspec fetch，不建 origin/*）
- HEAD 是 **detached** 的，停在 manifest-rev 上

**为什么这么设计？** 想象你正在改 lib 仓库的代码，改到一半，同事说"清单更新了，大家升到 lib v2"。如果 west 像普通人那样 `git checkout main && git pull`，你的本地修改可能被冲掉。west 的答案是把三个东西彻底分开：

```
 refs/heads/manifest-rev ──► ● v2     「清单的意图」（west update 唯一有权移动）
 refs/west/*              ──► (临时)  「fetch 的中间态」（用完就删）
 HEAD / 你的分支           ──► ● 你的工作（west 绝不强行覆盖）
```

记住这个图，`project.py` 里那 80 行 `update()` 就是它的逐行翻译。

### 1.4 实验B：再次 update，看 ref 怎么动

```bash
# 模拟"同事推送了新版本"
cd $LAB/work-lib && echo "lib v2" >> lib.txt && git commit -qam "lib v2" && git push -q origin main

cd $LAB && west update
cd lib && git reflog show refs/heads/manifest-rev    # manifest-rev 自己的日志
```

实际输出：

```
f963504 refs/heads/manifest-rev@{0}: west update: moving to f963504...   ← west 移的，还留了言
cc4b262 refs/heads/manifest-rev@{1}: west update: moving to cc4b262...
```

源码 `project.py:2136` 那行 `git update-ref -m 'west update: moving to ...'` 里的 `-m` 就是这个留言。**用实验对照源码**，是读 west 最有效的方法。

### 1.5 实验C：import 的优先级（反直觉，必做）

```bash
cd $LAB/manifest
# 改 west.yml：本文件定义 dup=lib.git，同时 self: import: 一个也定义 dup=app.git 的文件
cat > west.yml <<EOF
manifest:
  version: "1.2"
  projects:
  - name: lib
    url: $LAB/remote/lib.git
    revision: main
  - name: dup
    url: $LAB/remote/lib.git
    revision: main
  self:
    import: extra.yml
EOF
cat > extra.yml <<EOF
manifest:
  version: "1.2"
  projects:
  - name: dup
    url: $LAB/remote/app.git
    revision: main
  - name: extra
    url: $LAB/remote/app.git
    revision: main
EOF

cd $LAB && west list -f "{name:8} {url}"
```

实际输出：

```
dup      .../remote/app.git    ← 被导入文件（extra.yml）的 dup 赢了！
extra    .../remote/app.git    ← 导入的项目也进来了
lib      .../remote/lib.git
```

**本文件的 `dup` 被 `extra.yml` 的 `dup` 覆盖了**。规则是"先解析者胜"（first-writer-wins），而解析顺序是：**self 导入 → 本文件 projects → 项目导入**。所以 self 导入反而优先级最高——这正是 `manifest.py:1992-1999` 文档字符串写的东西，现在你有实验证据了。

### 1.6 实验D：west 如何保护你的本地工作 ★★

```bash
cd $LAB/lib
git checkout -q -b my-work && echo "my local work" > mine.txt && git add . && git commit -qm "my work"

# 同事又推了 v3
cd $LAB/work-lib && echo "lib v3" >> lib.txt && git commit -qam "lib v3" && git push -q origin main

cd $LAB && west update lib
```

实际输出（关键部分）：

```
HEAD is now at 0601993 lib v3
WARNING: left behind lib branch "my-work"; to rebase onto the new HEAD:
  git -C lib rebase 0601993e... my-work
```

检查现场：

```bash
cd $LAB/lib && git branch
# * (HEAD detached at 0601993)   ← west 把 HEAD 挪到新版本
#   manifest-rev
#   my-work                       ← 你的分支完好无损地躺在那！
```

**west 把 HEAD 挪走了，但你的分支一根汗毛没动**，还告诉你怎么 rebase 回来。再试 `--keep-descendants`（分支领先于新版本时保留分支不挪 HEAD）：

```bash
cd $LAB/lib && git checkout -q my-work && git rebase -q manifest-rev
echo "work v3" > mine.txt && git commit -qam "my work on v3"
cd $LAB && west update lib --keep-descendants
# west update: left descendant branch "my-work" checked out; current status:
cd $LAB/lib && git status -sb | head -1
# ## my-work    ← 这次 HEAD 没被挪走
```

做完这 4 个实验，你已经**用行为理解了 west 存在的意义和最核心的机制**。现在可以去看源码了。

---

## 2. 第二步：git refs 速成（读 west 的词汇表）

读 west 源码前，把下面 6 个概念过一遍。"你已经会的"那列是你日常 git 的认知，"需要补的"是 west 源码里到处都是的用法。每个都配了 3 行验证命令，任何 git 仓库里都能跑：

| 你已经会的 | 读 west 需要会的 | 验证命令 |
|---|---|---|
| `git checkout main` | **分支只是 ref 的别名**：`main` = `refs/heads/main` | `git rev-parse main`<br>`git rev-parse refs/heads/main`（输出相同） |
| `git pull` | **`git update-ref`**：程序化把某个 ref 指到某个 commit（west 移动 manifest-rev 的唯一手段） | `git update-ref refs/heads/test HEAD`<br>`git log test -1` |
| （没接触过） | **detached HEAD**：HEAD 直接指 commit 而非分支名 | `git checkout --detach HEAD`<br>`git status`（提示 "HEAD detached"） |
| `git fetch origin` | **refspec** `src:dst`：把远端的 src 存成本地 dst。west 用 `refs/heads/*:refs/west/*` 把分支暂存到自己的命名空间 | `git fetch origin 'refs/heads/main:refs/west/main'`<br>`git show-ref` |
| （没接触过） | **FETCH_HEAD**：上次 fetch 结果的"书签"文件 | `cat .git/FETCH_HEAD` |
| `git log` | **祖先判断**：A 是否是 B 的祖先（west 判断"你的分支是否包含新版本"） | `git merge-base --is-ancestor HEAD main`<br>`echo $?`（0=是） |

另外两个源码里高频出现的 git 调用：`git rev-parse --show-cdup`（判断是不是仓库根，`Project.is_cloned` 用它）、`git ls-tree <rev> <path>`（读某个提交里的文件内容，manifest 的 import 从这里读子清单）。

---

## 3. 第三步：50 行伪代码 = 整个 west

在跳进 8300 行源码之前，先看这个"心脏"。**west 全部源码就是下面这段伪代码的展开**：

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

对照文件行数：`manifest.py` 2784 行里有约 2000 行在处理"解析 west.yml"这 10 行伪代码的**报错和边角**；`project.py` 2331 行里约 1800 行是 `west_update` 那 6 行的**每个 git 调用的参数细节和失败处理**。**先抓住心脏，边角是读第二遍时才需要的。**

---

## 4. 第四步：六站阅读路线（每站 30–60 分钟）

> 方法论：**带着问题读，读完做自测**。每一站都标了精确到行的入口，跳着读，不要顺读。

### 第 0 站：把工具玩熟（§1 的实验）✅ 你已完成

### 第 1 站：`util.py` 全文——86 行，热身

**读**：全文。重点是 `west_topdir()`（:65-86）。

**带着问题**：为什么找到根后还要检查 `ZEPHYR_BASE`？为什么 `fall_back=False` 传进去？

**自测**：`WEST_DIR` 是什么？为什么 `.west` 必须是**目录**而不是文件（提示：`.is_dir()`）？

### 第 2 站：跟踪一条最简单的命令——`west topdir`

**读**：`main.py` 只读 5 段：`BUILTIN_COMMAND_GROUPS`（:1204-1225，全部命令的注册表）→ `WestApp.run`（:235-278，主流程）→ `run_command`（:534-641）→ `commands.py` 的 `WestCommand.run`（:171-200）→ `project.py` 的 `Topdir.do_run`（:2102-2103，就 2 行）。

**带着问题**：从敲下 `west topdir` 到打印路径，经过几个函数？`self.topdir` 这个值是谁、在哪一行注入的？

**自测**：`accepts_unknown_args` 和 `requires_workspace` 分别挡住了什么？（提示：`west topdir --foo` 会怎样？在 workspace 外跑 `west list` 会怎样？）动手试。

**调试技巧**：`python3 -m pdb $(which west) topdir`，`b west/commands.py:198`（hooks 之后、do_run 之前），看注入现场。

### 第 3 站：Manifest 主干（跳过一切 import 相关）

**读**：`manifest.py` 三段：`Manifest.__init__`（:1328-1533，只看参数校验和调用顺序）→ `_load_validated`（:1992 起，加载顺序的"目录"）→ `_load_project`（:2337-2459，单项目怎么变成 `Project` 对象）。**遇到 `import` 字样一律跳过**，第二遍再来。

**带着问题**：`url`、`remote+repo-path`、`defaults.remote` 三者的优先级怎么实现的（:2351-2377）？`path` 是怎么拼出来的（:2399）？

**REPL 玩法**（比读更有效）：

```python
$ python3
>>> from west.manifest import Manifest
>>> m = Manifest.from_file("~/west-lab/manifest/west.yml")   # 用你 §1 建的玩具
>>> [p.name for p in m.projects]
>>> m.projects[1].url, m.projects[1].path, m.projects[1].revision
```

**自测**：手写一个 3 项目的 west.yml（一个用 `remote`、一个用 `url`、一个用 defaults），先在纸上写出每个的 url 和 path，再用 REPL 验证。

### 第 4 站：import 递归——最烧脑的一站（配玩具代码）

**先跑** §5.2 的 20 行玩具代码，**再读**：`_import_ctx`（:355-426，就这一个结构体，读懂它的 10 个字段各管什么）→ `_add_project`（:2690-2704，先到先得的全部实现，14 行）→ `_import_from_self`（:2152-2200）。

**带着问题**：`ctx._replace(...)` 换掉了哪些字段、留下了哪些字段？（这是本站的全部考点）

**自测**：用 §1.5 实验C 的结果回答——为什么 self 导入会赢过本文件？

### 第 5 站：`west update` 的 git 序列

**读**：`project.py` 的 `Update.update`（:1376-1457，主序列）→ `fetch`（:1602-1666）→ `decide_update_strategy`（:1732-1761）。**每读到一个 git 命令，就回 §1 的实验场跑一遍，对照 reflog**。

**带着问题**：为什么 SHA revision 要用 `refs/heads/*:refs/west/*` 全量拉分支（提示：`is_ancestor_of` 判断需要）？为什么默认策略宁可 `checkout --detach` 也不动你的分支（实验D）？

**自测**：不看文档，说出 `west update` 从 fetch 到 submodules 的 8 步序列。

### 第 6 站：扩展命令机制

**读**：`commands.py` 的 `_ExtFactory`（:549-582）+ `main.py` 的 `run_extension`（:700-740）。

**带着问题**：为什么 `setup_parsers` 只给扩展建 stub（占位）parser？（提示：加载 zephyr 全部扩展要 import 多少模块？）为什么 `run_extension` 要**重建**一套 parser？

**自测**：写一个 5 行的 `west-commands.yml` + 10 行命令类，挂到玩具工作区里跑通（照抄 `tests/conftest.py:133-145` 的模板）。

---

## 5. 三大拦路虎拆解（每个配可运行玩具代码）

### 5.1 拦路虎一：`NamedTuple` + `_replace` 是什么打法？

west 满屏 `xxx = self._ctx._replace(a=1, b=2)`。这不是什么高深设计，就是 **"不可变结构体 + 改一个字段返回新副本"**：

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: int
    y: int

p1 = Point(1, 2)
p2 = p1._replace(x=99)     # 新对象！p1 不受影响
print(p1, p2)              # Point(x=1, y=2) Point(x=99, y=2)
```

**west 用它做什么**：把"解析配置"沿着 import 递归链传递并逐层修改（`path_prefix` 每层拼接），同时保证父层的配置不被子层污染。为什么不直接改？因为可能一个清单被导入多次、每次前缀不同——副本语义天然安全。

**为什么不用 dataclass**：历史选择（west 1.x 早期支持 Python 3.6，NamedTuple 更轻）。看到满屏 NamedTuple 不用慌，就当"带字段名的 tuple"。

### 5.2 拦路虎二：递归构造 Manifest + "共享上下文" ★★★（全文档最重要的一节）

`manifest.py` 最让人懵的代码：

```python
child_ctx = self._ctx._replace(path_prefix=..., current_data=...)
Manifest(topdir=self.topdir, internal_import_ctx=child_ctx)   # 递归构造新清单！
```

三个连环疑问：①为什么要递归构造自己？②为什么不会无限递归？③说好的 NamedTuple 不可变，怎么 projects 就"共享"了？

**20 行玩具复现**（复制即可运行，输出已验证）：

```python
from typing import NamedTuple

class Ctx(NamedTuple):
    projects: dict        # ★ 可变：所有递归层级共享同一个 dict 对象
    path_prefix: str      # 不可变：每层用自己的一份

def parse_manifest(content: str, ctx: Ctx) -> None:
    # 模拟解析：content 形如 "A,B,import"（项目名逗号分隔）
    for name in [t for t in content.split(',') if t != 'import']:
        if name not in ctx.projects:              # ★ 先到先得
            ctx.projects[name] = ctx.path_prefix + name

    if 'import' in content.split(','):            # 模拟 import: 指令
        child = ctx._replace(path_prefix=ctx.path_prefix + '子/')  # 换掉标量
        parse_manifest('dup,C', child)            # 递归：新 Ctx，旧 dict

ctx = Ctx(projects={}, path_prefix='')
parse_manifest('A,dup,import', ctx)
print(ctx.projects)
# {'A': 'A', 'dup': 'dup', 'C': '子/C'}
```

逐条解惑：

1. **为什么递归构造自己**：一份子清单 = 又一个完整的 west.yml，解析逻辑 100% 相同。与其写"解析顶层"和"解析子层"两套，不如一个函数递归用。
2. **为什么不会无限递归**：import 是有向的（A import B，B 不会再 import A），正常情况链条有限。**真有环怎么办？** west 没做检测，靠 Python 的 `RecursionError` 兜底转成报错（`manifest.py:686`，作者注释自嘲是 hack）。
3. **不可变的 NamedTuple 怎么共享**：**值不可变 ≠ 引用不共享**。`ctx._replace()` 换的是 `path_prefix` 这类标量字段（换新值），而 `projects` 字段装的是 dict 的**引用**——child 拿到的还是同一个 dict。所以"先到先得"才能跨层级生效。

理解了这 20 行，`manifest.py` 2000 行的 import 部分你就有了地图。

### 5.3 拦路虎三：`Project.git()` 的参数看不懂

`manifest.py:910-974`，所有 git 操作的总入口。参数表：

| 参数 | 作用 | 典型调用 |
|---|---|---|
| `cmd` | str 或 list。str 会被 `shlex.split` 拆（所以源码里能写 `project.git('rebase ' + ref)` 这种字符串拼接） | `'status'` 或 `['fetch', url, refspec]` |
| `cwd` | 在哪个目录跑，默认项目自己 | update 里传 `self.topdir` |
| `capture_stdout/stderr` | 要不要把输出抓回来（否则直接打到终端） | diff 要分析输出 → True |
| `check` | 返回非 0 时抛不抛 `CalledProcessError`，**默认抛** | diff 要拿 returncode 判断 → False |
| `extra_args` | 用户命令行透传（`accepts_unknown_args` 的出口） | `west diff --stat` 的 `--stat` |

**为什么没有 `shell=True`**：args 永远是列表，直接 exec，Windows/POSIX 都不需要引号转义。源码里的 `shlex.quote` 只用于**日志显示**。全库唯一 `shell=True` 是 `forall`（它本来就是让用户跑任意 shell 命令的）。

---

## 6. 懵点 FAQ

**Q1：为什么 `projects[0]` 永远是 `ManifestProject`？**
清单仓自己也是工作区一员（`west list` 里那个 `manifest N/A` 行）。west 把它硬插在索引 0，各命令遍历时用 `isinstance` 或索引判断跳过它。源码 `manifest.py:1106` 有 FIXME："这个类应该消失"（issue #327）——连作者都觉得这是个历史包袱。

**Q2：`log.py` 文档字符串说自己 deprecated，为什么还在？**
west 有**两套日志**：新的 `WestCommand.dbg/inf/wrn/err`（挂在命令实例上，随 verbosity）和旧的全局 `west.log`（模块级函数 + 全局 `VERBOSE` 变量）。旧的是给 v1.0 之前的扩展命令续命的，west 2.0 才移除（issue #149）。读码时无视旧的那套即可。

**Q3：`main.py` 里一堆 `queued_io` 是什么？**
"延迟吐话"机制。清单加载失败的诊断信息，如果在加载时立刻打印，verbosity 还没从命令行解析出来，可能打不出来或者打错地方。所以先包成闭包排队，等命令真正开跑前（pre-run hook）再吐。这叫**延迟错误**：清单坏了，`west help/config/update` 这几个白名单命令照样能跑（`main.py:316`）。

**Q4：为什么 west 克隆的仓库里 `git branch -a` 看不到 `origin/main`？**
west fetch 用显式 refspec（`fetch <url> main`），不建 remote-tracking 分支。它眼里"远端什么样"不重要，只有 manifest-rev（清单的意图）重要。见实验A。

**Q5：`ImportFlag.IGNORE / FORCE_PROJECTS` 是什么？**
控制 import 行为的开关：`IGNORE`＝根本不处理 import（`west init` 只想读 `self: path:` 时用）；`FORCE_PROJECTS`＝强制所有 import 走 importer 回调（`west update` 要"先更新再读内容"时用）。`_flags_ok`（:728）校验组合合法性。

**Q6（自测彩蛋）：源码里藏着一个真 bug，你能找到吗？**
提示：`project.py:1422`。`west update --stats --keep-descendants` 组合会崩溃。为什么这行平时不炸？（答案：`perf_counter - start` 少写了一对括号——函数对象减浮点数必然 TypeError，但只有 `--stats` 且走到"保留后代分支"分支才会执行到这行。这也是读源码的一课：**参数检查型 bug 藏在配置组合的角落里**。）

---

## 7. 三份文档怎么配合用

```
你的位置                    用哪份
─────────────────────────────────────────────────────
"看不懂源码"（现在的你）  →  本指南：§1 实验 + §4 六站路线
读完一遍，要全局地图      →  《west实现机制图解.md》：16 张图速查
写报告/做设计、要行号证据 →  《west实现机制深度分析.md》：当字典查
```

最后一条心法：**west 源码里 80% 的行数是报错处理和边角情况**。任何时候觉得乱，就回到 §3 那 50 行伪代码——找不到主线的时候，主线一定在那里。

---

*实验环境：Ubuntu 22.04 / git 2.34 / west 1.4.0（pip 安装）。§1 全部命令与输出于 2026-10-09 实测；行号引证与另两份文档一致，基于 commit `746e1b19`。*
