# SmartGit 试用期解除工具

适用于 Linux / SmartGit 26.1：为 SmartGit 设置固定的专用机器 ID，以及申请、验证官方试用凭证。

需要 Python 3；专用 ID 功能还需 Bash、`bwrap`、系统允许命名空间，并将 SmartGit 安装在 `/usr/share/smartgit`。

## 专用机器 ID

在本目录执行，无需 `sudo`：

```bash
python3 smartgit_private_id.py install    # 安装，重复执行保留 ID
python3 smartgit_private_id.py check      # 检查映射
python3 smartgit_private_id.py uninstall  # 恢复桌面入口，保留 ID 和启动器
```

安装后退出所有 SmartGit 进程，再从应用菜单启动。直接运行系统 `smartgit` 命令不会使用专用 ID。系统 ID 不变；此功能不是完整的隐私沙箱。

一键修复并启动（在图形会话中运行，无需 `sudo`）：

```bash
./repair-smartgit.sh          # 重装桌面入口，启动并验证实际 JVM 的 ID 映射
./repair-smartgit.sh --check  # 只检查正在运行的 JVM，不修改配置
```

重复执行保留现有 ID。若已有未使用专用 ID 的实例，脚本会提示正常退出后重试，不强制终止进程。启动通过 `gio launch` 使用明确的用户桌面文件；启动输出位于 `~/.config/smartgit-private/startup.log`（或对应 XDG 配置目录），权限为 `0600`。无法读取运行进程时会报错，不会声称验证成功。

原有 `smartgit_private_id.py check` 仅证明新建子进程的映射正常，不能证明现有窗口已生效。新脚本检查 `/proc/<pid>/root` 下实际 JVM 看到的 ID 文件；检查通过也不代表应用授权状态改变，授权资格与期限仍由官方决定。

## 官方试用凭证

使用系统 ID 申请和验证：

```bash
python3 smartgit_evaluation.py request --output /tmp/smartgit.evaluation
python3 smartgit_evaluation.py verify /tmp/smartgit.evaluation
```

使用专用 ID 时，在本目录执行：

```bash
launcher="${XDG_CONFIG_HOME:-$HOME/.config}/smartgit-private/launch"
"$launcher" --exec python3 "$PWD/smartgit_evaluation.py" request --output /tmp/smartgit.evaluation
"$launcher" --exec python3 "$PWD/smartgit_evaluation.py" verify /tmp/smartgit.evaluation
```

申请需联网，验证可离线。输出文件不能已存在；凭证不会自动安装，需按 SmartGit 授权流程启用。申请、验证和启动须使用相同 ID，资格和期限由官方决定。不要提交凭证或机器 ID 到版本库。

更多参数：脚本后加 `--help`。运行测试：`python3 -m unittest discover -v`。
