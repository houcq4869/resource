# RT-Thread Env 工具 venv 引导、安装与激活链源码分析报告

**分析版本**：v2.0.2（commit ec2c251）  
**分析对象**：`~/workspace/repo/env` 中 Python 引导脚本、Shell/PowerShell 安装与激活脚本、打包元数据、统计上报及测试用例。  
**方法**：逐行阅读源码，所有行为结论均附 `file:line` 精确引用；未运行任何脚本，未修改仓库。

---

## 1. env_venv.py：venv 创建 / 修复 / 升级判定与 PyPI 镜像选择

### 1.1 核心数据结构

`env_venv.py:40-41` 定义了状态文件：

```python
STATE_FILENAME = '.rt-thread-env-state.json'
STATE_SCHEMA = 1
```

`env_venv.py:43-67` 定义了需要参与指纹计算的运行时文件集合：

- `ROOT_RUNTIME_FILES`：根目录下 `MANIFEST.in`、`env.json`、`env.ps1`、`env.sh`、`pyproject.toml`、`setup.py`。
- `ROOT_RUNTIME_SUFFIXES`：根目录下所有 `.py` 文件。
- `RUNTIME_DIRECTORIES`：`cmds`、`plugins` 两个目录。
- 排除项：`EXCLUDED_DIRECTORY_NAMES`（含 `.git`、`__pycache__`、`build`、`dist`、`node_modules`、`playwright-report`、`test-results`）以及 `EXCLUDED_RUNTIME_PREFIXES`（`plugins/examples`、`plugins/tests`、`plugins/webui/frontend`）和 `.md`/`.rst` 后缀文件。

### 1.2 venv 指纹（fingerprint）算法

`env_venv.py:113-131` 的 `source_fingerprint()`：

1. 调用 `iter_runtime_files(source_root)` 收集文件。
2. 对每个文件，先将其相对路径（UTF-8）加入 SHA-256 digest，再写入 `\0`。
3. 接着读取文件内容（每次 1 MiB）加入 digest，再写入 `\0`。
4. 返回 `digest.hexdigest()`。

也就是说，**指纹 = 运行时源文件集合 × 相对路径 × 文件内容** 的 SHA-256。任何运行时脚本内容变化都会触发升级。

`env_venv.py:380-383` 的 `_state_matches()` 判定状态是否仍然匹配：

```python
def _state_matches(state, source_root, fingerprint):
    if not state or state.get('schema') != STATE_SCHEMA:
        return False
    return state.get('source') == str(_normalized(source_root)) and state.get('fingerprint') == fingerprint
```

### 1.3 判定流程：`ensure_environment()`

`env_venv.py:410-469` 是引导入口。逻辑如下：

1. **首次安装判定**（`env_venv.py:423`）：
   ```python
   initial_install = not venv_is_usable(layout)
   ```
   `venv_is_usable`（`env_venv.py:166-167`）检查 `python` 和 `activate` 文件是否都存在。

2. **首次安装动作**（`env_venv.py:426-432`）：
   ```python
   print('Create Python venv for RT-Thread...')
   host_python = getattr(sys, '_base_executable', sys.executable)
   command_runner([host_python, '-m', 'venv', str(venv_root)])
   ```

3. **源变更检测**（`env_venv.py:434-439`）：
   ```python
   fingerprint = source_fingerprint(source_root)
   state = read_state(venv_root)
   source_changed = not _state_matches(state, source_root, fingerprint)
   activation_changed = not activation_is_current(source_root, activation_target)
   package_missing = not env_is_installed(layout)
   upgrade_required = source_changed or activation_changed
   ```
   - `activation_is_current()`（`env_venv.py:208-218`）比较激活脚本源文件与目标文件是否相同（先 `samefile`，再 `filecmp.cmp`）。
   - `env_is_installed()`（`env_venv.py:170-171`）检查 `rt-env` 可执行文件是否存在。

4. **交互式确认**（`env_venv.py:441-444`）：
   若非首次安装、包存在且需要升级，且未设置 `--yes`/环境变量 `ENV_VENV_AUTO_UPGRADE`，则调用 `confirm_upgrade()` 询问用户。

5. **早退条件**（`env_venv.py:446-447`）：
   ```python
   if not initial_install and not package_missing and not upgrade_required:
       return 'current'
   ```

6. **执行安装/升级/修复**（`env_venv.py:449-469`）：
   - 选择 PyPI 镜像。
   - 调用 `install_env()`。
   - 同步激活脚本并写入状态文件。
   - 返回 `'created'`、`'repaired'` 或 `'upgraded'`。

### 1.4 状态文件内容

`env_venv.py:454-463`：

```python
{
    'schema': 1,
    'source': str(source_root),
    'fingerprint': fingerprint,
    'version': read_env_version(source_root),
    'index': _index_label(index_url),
}
```

### 1.5 pip 命令与包列表

`env_venv.py:347-377` 的 `install_env()`：

1. 升级 `ensurepip`：
   ```python
   [python, '-m', 'ensurepip', '--upgrade']
   ```

2. 首次安装时升级 pip：
   ```python
   [python, '-m', 'pip', 'install', '--disable-pip-version-check', '--upgrade']
   + _pip_network_arguments(index_url, env_root)
   + ['pip']
   ```

3. 安装本地源目录（即 `source_root`，也就是 `~/.env/tools/scripts`）：
   ```python
   [python, '-m', 'pip', 'install', '--disable-pip-version-check', '--upgrade',
    '--upgrade-strategy', 'only-if-needed']
   + _pip_network_arguments(index_url, env_root)
   + [str(_normalized(source_root))]
   ```

**没有固定的 `requirements.txt` 或显式包列表**；依赖由 `pyproject.toml` 的 `dependencies` 决定，pip 会解析 `setup.py`/`pyproject.toml` 并安装。因此，所有版本约束都集中在 `pyproject.toml:13-21`。

### 1.6 PyPI 镜像选择

`env_venv.py:265-284` 的 `select_index_url()`：

1. **环境变量最高优先级**：若 `ENV_PYPI_INDEX_URL` 非空，直接返回（`env_venv.py:267-270`）。
2. **持久化配置**：若 `network` 模块可用，调用 `network.pypi_index_url(env_root=env_root, environ=environ)`（`env_venv.py:272-273`）。
   - 如果 `pypi_mode == 'default'`，返回 `None`（使用 PyPI 默认）（`env_venv.py:277-278`）。
3. **中国 IP 检测**：调用 `country_detector`（默认是 `detect_country()`）。
   - `detect_country()`（`env_venv.py:256-262`）使用 `https://ipinfo.io/country`，User-Agent 为 `RT-Thread-Env/2`，**强制绕过代理**（`_open_without_proxy`），超时 3 秒。
   - 若返回 `'CN'`，使用阿里云镜像 `https://mirrors.aliyun.com/pypi/simple/`（`env_venv.py:281-283`）。

`env_venv.py:28`：

```python
ALIYUN_INDEX_URL = 'https://mirrors.aliyun.com/pypi/simple/'
```

`_pip_network_arguments()`（`env_venv.py:326-336`）处理 pip 代理：

- 若 `network` 模块缺失，添加 `--proxy ''`。
- 若未配置网络或 `proxy_mode == 'direct'`，添加 `--proxy ''`。
- 若 `proxy_mode == 'custom'`，添加 `--proxy <proxy_url>`。

### 1.7 失败处理

`env_venv.py:515-517` 的 `main()`：

```python
except (BootstrapError, OSError, ValueError, subprocess.CalledProcessError) as exc:
    print('Failed to prepare the Env Python venv: %s' % exc, file=sys.stderr)
    return 1
```

中间步骤中，`BootstrapError` 会抛出清晰的错误消息，例如：

- `env_venv.py:432`："Python venv was created without a usable interpreter or activation script"
- `env_venv.py:394`："cannot mark the Python venv as current before Env is installed"
- `env_venv.py:452`："local Env package installation did not create the rt-env command"

---

## 2. 激活链：`env.sh` 的执行步骤

`env.sh` 共 63 行，流程如下：

### 2.1 变量初始化（`env.sh:1-9`）

```sh
ENV_ROOT="${ENV_ROOT:-$HOME/.env}"
VENV_ROOT="$ENV_ROOT/.venv"
ENV_SCRIPTS_ROOT="$ENV_ROOT/tools/scripts"
ENV_BOOTSTRAP="$ENV_SCRIPTS_ROOT/env_venv.py"
ENV_ACTIVATE="$VENV_ROOT/bin/activate"
```

### 2.2 导出环境变量（`env.sh:11-17`）

```sh
export ENV_ROOT
if [ "${ENV_VENV_AUTO_UPGRADE+x}" = "x" ]; then export ENV_VENV_AUTO_UPGRADE; fi
if [ "${ENV_PYPI_INDEX_URL+x}" = "x" ]; then export ENV_PYPI_INDEX_URL; fi
```

### 2.3 选择引导 Python（`env.sh:19-25`）

优先级：

1. 系统 `python3`；
2. 已存在 venv 中的 `$VENV_ROOT/bin/python`；
3. 否则为空，报错。

### 2.4 运行 `env_venv.py` 引导（`env.sh:34-38`）

```sh
"$BOOTSTRAP_PYTHON" "$ENV_BOOTSTRAP" \
    --venv "$VENV_ROOT" \
    --source "$ENV_SCRIPTS_ROOT" \
    --activation-script "$ENV_ROOT/env.sh"
```

### 2.5 激活 venv（`env.sh:40-53`）

```sh
if [ -f "$ENV_ACTIVATE" ]; then
    if ! . "$ENV_ACTIVATE"; then ... fi
    if command -v rt-env >/dev/null 2>&1; then
        rt-env --info
    fi
else
    echo "Cannot activate the RT-Thread Env Python venv: $ENV_ACTIVATE was not found." >&2
    activate_status=1
fi
```

### 2.6 注入 PATH 与默认值（`env.sh:55-56`）

```sh
export PATH="$ENV_SCRIPTS_ROOT:$PATH"
export RTT_EXEC_PATH=/usr/bin
```

### 2.7 是否仅当前会话有效？

是的。`env.sh` 通过 `source env.sh` 执行，所有 `export` 仅影响当前 shell 进程；它没有写入 `~/.bashrc` 等文件，也没有创建持久 alias。`env.sh:58-63` 根据激活/引导状态 `return` 或 `exit`。

### 2.8 `env.ps1` 的差异

`env.ps1:1-5` 支持从 `$PSScriptRoot` 推断 `ENV_ROOT`；`env.ps1:55` 修改 `PATHEXT`：

```powershell
$env:PATHEXT = ".PS1;$env:PATHEXT"
```

注意这里使用大写 `.PS1`，可能导致 Windows 上 PowerShell 脚本扩展名大小写不敏感但实际仍可运行。`env.ps1:57-62` 在引导失败时仅发出 `Write-Warning`，**不会终止会话**，这与 `env.sh` 的 `exit/return` 行为不同。

---

## 3. `touch_env.sh` / `touch_env.py` / `touch_env.ps1`：克隆仓库与镜像切换

### 3.1 `touch_env.sh`

`touch_env.sh:3-5` 硬编码三个仓库的 GitHub URL：

```sh
DEFAULT_RTT_PACKAGE_URL=https://github.com/RT-Thread/packages.git
ENV_URL=https://github.com/RT-Thread/env.git
SDK_URL="https://github.com/RT-Thread/sdk.git"
```

`touch_env.sh:7-11` 根据中国 IP 切换到 Gitee：

```sh
if [ "$(wget -qO- --timeout=3 https://ipinfo.io/country 2>/dev/null)" = "CN" ]; then
    DEFAULT_RTT_PACKAGE_URL=https://gitee.com/RT-Thread-Mirror/packages.git
    ENV_URL=https://gitee.com/RT-Thread-Mirror/env.git
    SDK_URL="https://gitee.com/RT-Thread-Mirror/sdk.git"
fi
```

`touch_env.sh:13-19` 处理 `.env` 目录已存在的情况：提示是否删除并重建。正则 `[[ "$option" =~ [Yy*] ]]` 中的 `*` 在字符类内是字面量，实际只匹配 `Y`、`y`、`*`；可能原意是 `[Yy]`。

`touch_env.sh:21-40` 实际创建目录并克隆：

```sh
mkdir $env_dir
mkdir $env_dir/local_pkgs
mkdir $env_dir/packages
mkdir $env_dir/tools

git clone $package_url $env_dir/packages/packages --depth=1
echo 'source "$PKGS_DIR/packages/Kconfig"' >$env_dir/packages/Kconfig
git clone $SDK_URL $env_dir/packages/sdk --depth=1
git clone $ENV_URL $env_dir/tools/scripts --depth=1
```

然后 **把 remote origin 改回 GitHub**：

```sh
git -C $env_dir/packages/packages remote set-url origin https://github.com/RT-Thread/packages.git
git -C $env_dir/packages/sdk remote set-url origin https://github.com/RT-Thread/sdk.git
git -C $env_dir/tools/scripts remote set-url origin https://github.com/RT-Thread/env.git
```

最后把 `env.sh` 复制到 `$env_dir/env.sh`。

### 3.2 `touch_env.ps1`

逻辑与 shell 版一致。`touch_env.ps1:5-9` 使用 `Invoke-RestMethod -Uri "https://ipinfo.io/json"` 检测国家；`touch_env.ps1:34-37` 同样 `--depth=1` 克隆；`touch_env.ps1:40-42` 同样把 origin 改回 GitHub。

### 3.3 `touch_env.py`

`touch_env.py` **为空文件（0 字节）**，目前没有任何作用。这是一个明显的遗留/占位文件。

### 3.4 分支信息来源

`touch_env.sh`/`touch_env.ps1` 都是**硬编码分支为默认**（通过 `--depth=1` 克隆，不指定 `--branch`，因此使用仓库默认分支）。它们**没有读取 `env.json`**。

而 `env.json`（`env.json:5-30`）确实定义了每个仓库的 `branch` 和 `mirror.branch`：

- `env` → `master`
- `sdk` → `main`
- `packages` → `master`

这说明 `touch_env.*` 的镜像切换逻辑与 `env.json` 的配置是**两套独立来源**：脚本硬编码了 URL，而 `env.json` 被 `info.py` 等运行时模块使用。

---

## 4. `install_*.sh` / `install_windows.ps1`：宿主包安装

### 4.1 共同行为

所有 Linux 安装脚本都通过 `wget`/`curl` 下载 `touch_env.sh`/`touch_env.ps1`，设置可执行权限后运行，然后删除临时脚本。**它们不安装 Python 依赖到宿主 Python，也不调用 host pip**。这一点在 `tests/test_installers.py` 中有显式校验。

### 4.2 `install_ubuntu.sh`（`install_ubuntu.sh:14-16`）

```sh
sudo apt-get update
sudo apt-get -qq install python3 python3-venv gcc git libncurses5-dev -y
```

宿主包：`python3`、`python3-venv`、`gcc`、`git`、`libncurses5-dev`。

### 4.3 `install_arch.sh`（`install_arch.sh:15-17`）

```sh
sudo pacman -Syu python gcc git ncurses \
    arm-none-eabi-gcc arm-none-eabi-gdb \
    qemu-desktop qemu-system-arm-firmware
```

宿主包：`python`、`gcc`、`git`、`ncurses`、`arm-none-eabi-gcc`、`arm-none-eabi-gdb`、`qemu-desktop`、`qemu-system-arm-firmware`。

### 4.4 `install_suse.sh`（`install_suse.sh:14-17`）

```sh
sudo zypper update -y
sudo zypper install python3 python3-venv gcc git ncurses-devel cross-arm-none-gcc11-bootstrap cross-arm-binutils qemu qemu-arm qemu-extra -y
```

宿主包：`python3`、`python3-venv`、`gcc`、`git`、`ncurses-devel`、`cross-arm-none-gcc11-bootstrap`、`cross-arm-binutils`、`qemu`、`qemu-arm`、`qemu-extra`。

### 4.5 `install_macos.sh`

与 Linux 脚本不同，`install_macos.sh:39` 直接使用 GitHub URL 下载 `touch_env.sh`，**没有使用 ipinfo.io 检测中国 IP**，也没有 Gitee 镜像切换。

其他宿主包通过 Homebrew 安装：`git`、`ncurses`、`gnu-arm-embedded`。

### 4.6 `install_windows.ps1`

`install_windows.ps1:8-13` 查找 `python3`、`python`、`py`；若未找到则下载 Python 3.11.2 并安装。`install_windows.ps1:32-36` 通过 `ipinfo.io/json` 检测国家并切换 Gitee。`install_windows.ps1:43-57` 使用 `winget` 安装 Git，失败则回退到手动下载安装包。

`install_windows.ps1:68-72` 的自动模式判断：

```powershell
if ($args.Count -ge 2 -and $args[1] -eq "-y") {
    ...
}
```

这里检查 `$args[1]`，而 `$args[0]` 在 PowerShell 中才是第一个位置参数，脚本自身路径由 `$PSCommandPath` 提供。因此该判断实际上要求**第二个位置参数为 `-y`**，而不是通常理解的“第一个参数 -y”。

---

## 5. `statistics.py`：统计上报

### 5.1 触发条件与数据

`statistics.py:42-67` 的 `Information_statistics()`：

1. 构造 `.config` 路径：
   ```python
   env_kconfig_path = os.path.join(os.getcwd(), 'tools', 'scripts', 'cmds')
   env_config_file = os.path.join(env_kconfig_path, '.config')
   ```

2. 获取 MAC 地址：
   ```python
   mac_addr = get_mac_address()
   ```

3. 如果 `env_config_file` 不存在，发送 GET 请求：
   ```python
   requests.get(
       get_api_url('statistics')
       + '?userid=' + str(mac_addr)
       + '&username=' + str(mac_addr)
       + '&envversion=1.0&studioversion=2.0&ip=127.0.0.1'
   )
   ```

   上报数据包括：
   - `userid`：MAC 地址
   - `username`：MAC 地址
   - `envversion`：硬编码 `1.0`
   - `studioversion`：硬编码 `2.0`
   - `ip`：硬编码 `127.0.0.1`

### 5.2 退出机制

`statistics.py:62-63`：

```python
except Exception as e:
    exit(0)
```

这里捕获异常后直接 `exit(0)`，会**终止整个进程**，而不仅仅是返回。如果该模块在 import 时触发，可能导致脚本意外退出。

### 5.3 禁用机制

`statistics.py:64-67`：

```python
elif os.path.isfile(env_config_file) and cmd_package.find_bool_macro_in_config(
    env_config_file, 'SYS_PKGS_NOT_USING_STATISTICS'
):
    return True
```

如果 `.config` 文件存在且包含 `CONFIG_SYS_PKGS_NOT_USING_STATISTICS=y`，则跳过上报。

### 5.4 明显缺陷

- `statistics.py:31`：`from vars import Import` 导入了未使用的 `Import`。
- `statistics.py:44` 和 `statistics.py:48` 重复赋值 `env_config_file`。
- 文件头部注释写成了 `File      : vars.py`（`statistics.py:3`），明显是从 `vars.py` 复制后未修改。
- `statistics.py:62`：`except Exception as e` 中的 `e` 未被使用。

---

## 6. `file_context_menu.py`：Windows 资源管理器右键菜单

### 6.1 功能概述

`file_context_menu.py` 提供**仅在 Windows 上安装/卸载资源管理器右键菜单**的能力。菜单文字为 `在RT-Thread Env终端中打开`（`file_context_menu.py:27`）。

### 6.2 注册表位置

`file_context_menu.py:50-52`：

```python
locations = [
    r"HKCU\Software\Classes\Directory\shell\EnvTerminal",
    r"HKCU\Software\Classes\Directory\Background\shell\EnvTerminal",
]
```

即 **HKEY_CURRENT_USER** 下的两个位置：

- 目录右键：`Directory\shell\EnvTerminal`
- 目录背景右键：`Directory\Background\shell\EnvTerminal`

### 6.3 注册表写入内容

`_install_windows()`（`file_context_menu.py:112-136`）：

1. 在 `~/.env/tools/scripts/.env-terminal.ps1` 写入 PowerShell 辅助脚本，内容调用 `env.ps1`。
2. 创建注册表键，设置：
   - `MUIVerb`：菜单显示文字
   - `Icon`：`powershell.exe`
   - `command` 默认值：
     ```powershell
     powershell.exe -NoLogo -NoExit -ExecutionPolicy Bypass -File "%s" "%%V\\."
     ```

### 6.4 卸载

`_remove_windows()`（`file_context_menu.py:138-150`）递归删除注册表树并删除辅助脚本。

### 6.5 Linux 支持声明

`file_context_menu.py:36-38`：

```python
if self.hostos not in ("Linux", "Windows"):
    raise ContextMenuError("文件资源管理器菜单仅支持 Linux 和 Windows")
```

但实际 `snapshot()`、`install()`、`remove()` 中只有 Windows 逻辑；Linux 仅返回 `supported=False`。

---

## 7. 打包与入口点：`pyproject.toml` + `setup.py` + `MANIFEST.in`

### 7.1 Python 版本要求

`pyproject.toml:8`：

```toml
requires-python = ">=3.7"
```

### 7.2 依赖列表

`pyproject.toml:13-21`：

```toml
dependencies = [
    "SCons>=4.0.0",
    "requests",
    "psutil",
    "tqdm",
    "kconfiglib",
    "pyyaml",
    "windows-curses; sys_platform=='win32'",
]
```

### 7.3 控制台脚本入口点

`pyproject.toml:23-30`：

```toml
rt-env = "env.env:main"
menuconfig = "env.env:menuconfig"
pkgs = "env.env:pkgs"
sdk = "env.env:sdk"
system = "env.env:system"
webui = "env.env:webui"
```

- `rt-env` 对应 `env.env:main`
- `menuconfig` 对应 `env.env:menuconfig`
- `pkgs` 对应 `env.env:pkgs`
- `sdk` 对应 `env.env:sdk`
- `system` 对应 `env.env:system`
- `webui` 对应 `env.env:webui`

### 7.4 `setup.py`

`setup.py:10-12`：

```python
setup(
    version=get_version(),
    description=get_description(),
)
```

它从 `info.py` 动态读取版本和描述。

### 7.5 `MANIFEST.in`

`MANIFEST.in` 用于 sdist 时包含额外文件：文档、前端静态资源、`plugins/bundled`、`plugins/examples`、`assets/env.png` 等，并排除 `*.py[cod]`。

### 7.6 包布局映射

`pyproject.toml:32-44` 使用 `package-dir` 把根目录映射为 `env` 包，子目录映射为 `env.cmds`、`env.plugins` 等。

---

## 8. 小怪癖、Bug 与死代码

| 位置 | 问题描述 |
|---|---|
| `touch_env.py` | **完全为空（0 字节）**，没有功能。 |
| `statistics.py:3` | 文件头注释写成 `# File      : vars.py`，应为 `statistics.py`。 |
| `statistics.py:31` | `from vars import Import` 导入后未使用。 |
| `statistics.py:44,48` | `env_config_file` 被重复赋值。 |
| `statistics.py:62` | `except Exception as e:` 中 `e` 未使用。 |
| `statistics.py:63` | 在异常分支调用 `exit(0)` 会终止整个进程。 |
| `touch_env.sh:16` | `[[ "$option" =~ [Yy*] ]]` 中 `*` 在字符类内为字面量，可能原意是 `[Yy]`。 |
| `touch_env.sh:28` | 使用 `$PKGS_DIR` 但该变量未在脚本中定义。 |
| `env.sh:55` | `export PATH="$ENV_SCRIPTS_ROOT:$PATH"` 每次 source 都会把脚本目录 prepend，重复 source 会重复添加。 |
| `env.ps1:55` | `$env:PATHEXT = ".PS1;$env:PATHEXT"` 使用大写 `.PS1`。 |
| `env.ps1:57-62` | 引导失败时只警告不退出，与 `env.sh` 行为不一致。 |
| `install_macos.sh:39` | 没有中国 IP 检测，始终使用 GitHub 下载 `touch_env.sh`。 |
| `install_windows.ps1:68` | 检查 `$args[1]` 是否为 `-y`，但 `$args[0]` 才是第一个位置参数，判断逻辑偏移。 |
| `env.py:137` | 函数名 `get_rtt_verion()` 拼写错误，应为 `get_rtt_version()`。 |
| `env.py:67` | `show_version()` 调用 `get_rtt_verion()`，该拼写错误在多处出现。 |
| `file_context_menu.py:36-38` | 声明支持 Linux，但 `install()`/`remove()` 只处理 Windows，Linux 实际不可用。 |
| `env_venv.py:300-303` | `run_command()` 在 `network` 不可用时使用 `_proxy_free_environment()`，但 `run_command()` 本身只在 `install_env()` 中通过 `_invoke_command()` 调用，实际路径中 `network` 通常存在。 |

---

## 9. 机制总结

RT-Thread Env 2.0 的 venv 子系统有以下几个关键设计决策：

1. **自包含的 venv 引导**：`env.sh`/`env.ps1` 通过调用 `env_venv.py` 确保 `~/.env/.venv` 存在、可用且与本地脚本一致；所有 Python 依赖都装在 venv 中，宿主系统只装 `python3-venv` 等基础包。

2. **源指纹驱动升级**：venv 是否升级取决于运行时源文件集合的 SHA-256 指纹，而不是版本号或时间戳。任何脚本改动都会触发重新 `pip install` 本地源码目录。

3. **双层镜像策略**：首次克隆通过 `ipinfo.io` 检测中国大陆 IP，临时使用 Gitee 加速；随后立即把 Git remote 改回 GitHub，保证后续更新元数据一致性。PyPI  similarly 在中国大陆 IP 下默认使用阿里云镜像。

4. **激活脚本状态仅当前会话**：`env.sh` 只修改当前 shell 的 `PATH` 和 `ENV_ROOT` 等变量，不写入启动文件，因此每次新终端都需要重新 `source`。

5. **统计上报默认开启、无显式 opt-in**：`statistics.py` 在没有 `.config` 文件时会自动上报 MAC 地址等信息；只有在 `.config` 中声明 `CONFIG_SYS_PKGS_NOT_USING_STATISTICS=y` 才会跳过。

6. **Windows 资源管理器深度集成**：通过写入 `HKCU\Software\Classes\Directory\shell\EnvTerminal` 实现右键“在 RT-Thread Env 终端中打开”，并生成辅助 PowerShell 脚本。

7. **配置来源存在割裂**：`touch_env.sh`/`touch_env.ps1` 中的仓库 URL 和分支信息是硬编码的，与 `env.json` 中由 `info.py` 读取的规范化配置不同源；`touch_env.py` 更是完全未实现。
