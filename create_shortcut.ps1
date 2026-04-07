# create_shortcut.ps1
# 在桌面建立「Coffee POS 啟動」捷徑
# 執行方式：在 PowerShell 中 cd 到專案根目錄後執行
#   powershell -ExecutionPolicy Bypass -File create_shortcut.ps1

$ProjectRoot = (Get-Location).Path
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Coffee POS 啟動.lnk"
$IconPath = Join-Path $ProjectRoot "assets\pos_icon.ico"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath  = Join-Path $ProjectRoot "start.bat"
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.WindowStyle = 1   # 1=正常視窗
$Shortcut.Description = "啟動 Coffee POS 收銀系統"

# 若有 icon 檔則套用
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}

$Shortcut.Save()

Write-Host ""
Write-Host "  ✅ 桌面捷徑已建立：Coffee POS 啟動.lnk" -ForegroundColor Green
Write-Host "     位置：$ShortcutPath"
Write-Host ""
