import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { realpath } from "@toonflow/file";

const runFile = promisify(execFile);

export async function selectDirectory() {
  if (!["win32", "darwin"].includes(process.platform)) throw new Error("当前系统请手动填写文件夹的完整路径");
  const windowsScript = `
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
$dialog = [System.Windows.Forms.FolderBrowserDialog]::new()
$dialog.Description = "选择文件夹"
$owner = [System.Windows.Forms.Form]::new()
$owner.ShowInTaskbar = $false
$owner.Opacity = 0
try {
  # ACT: 隐形父窗口先显示，系统目录弹窗才能继承置顶状态。
  $owner.Show()
  $owner.TopMost = $true
  $owner.Activate()
  if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Write($dialog.SelectedPath) }
} finally { $dialog.Dispose(); $owner.Dispose() }
`;
  const macScript = `try
  return POSIX path of (choose folder with prompt "选择文件夹")
on error number -128
  return ""
end try`;
  try {
    const { stdout } = process.platform === "win32"
      ? await runFile("powershell.exe", ["-NoProfile", "-NonInteractive", "-STA", "-Command", windowsScript], { windowsHide: true })
      : await runFile("/usr/bin/osascript", ["-e", macScript]);
    const selected = stdout.replace(/\r?\n$/, "");
    const directory = selected ? await realpath(selected) : null;
    return directory;
  } catch {
    throw Object.assign(new Error("无法打开本机文件夹选择器，请重试"), { status: 500 });
  }
}
