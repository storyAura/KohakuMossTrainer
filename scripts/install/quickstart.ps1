# Quick start menu (Chinese), launched by start.bat: install, doctor, config wizard, weights, data caches, training, sampling, shell, web UI.
# Usage: double-click start.bat, or powershell -ExecutionPolicy Bypass -File scripts\install\quickstart.ps1
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Venv = Join-Path $Root ".venv"
$Weights = "models\MOSS-Image-Base"
$UserConfigs = "configs/user"
$DataScripts = @(
    @("检查数据", "scripts/data/inspect_data.py"),
    @("缓存文字描述", "scripts/data/cache_text.py"),
    @("缓存图片", "scripts/data/cache_latents.py")
)
$LowRamSets = @("--set", "BASE_PRECISION=int8", "--set", "SAMPLE_EVERY=0")
Set-Location $Root

# Waits for Enter so the window does not close before the message is read.
function Wait-Enter { Read-Host "按回车键继续" | Out-Null }

function Write-Note([string]$Text) { Write-Host "[启动] $Text" -ForegroundColor Yellow }

# Runs a native command on this console (output not captured); callers read $LASTEXITCODE.
function Invoke-Native([string]$What, [string]$Exe, [string[]]$Arguments) {
    Write-Host ">> $Exe $($Arguments -join ' ')" -ForegroundColor DarkGray
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[启动] $What 失败 (退出码 $LASTEXITCODE)，请看上面的报错信息。" -ForegroundColor Red
    }
}

# Train configs written by the wizard: configs\user\<name>.py with a <name>_data.py beside it.
function Get-TrainNames {
    if (-not (Test-Path $UserConfigs)) { return @() }
    Get-ChildItem $UserConfigs -Filter "*_data.py" |
        ForEach-Object { $_.Name -replace "_data\.py$", "" } |
        Where-Object { Test-Path (Join-Path $UserConfigs "$_.py") }
}

# Asks which train config to use; returns its name, or $null when there is none.
function Select-TrainName {
    $names = @(Get-TrainNames)
    if ($names.Count -eq 0) {
        Write-Note "还没有训练配置，请先选 2 生成训练配置。"
        return $null
    }
    if ($names.Count -eq 1) {
        Write-Note "使用配置: $($names[0])"
        return $names[0]
    }
    for ($i = 0; $i -lt $names.Count; $i++) { Write-Host "  $($i + 1). $($names[$i])" }
    $pick = Read-Host "选择配置 (输入编号后按回车)"
    $index = 0
    if ([int]::TryParse($pick, [ref]$index) -and $index -ge 1 -and $index -le $names.Count) {
        return $names[$index - 1]
    }
    Write-Note "没有这个编号。"
    return $null
}

function Invoke-PrepareData {
    $name = Select-TrainName
    if (-not $name) { return }
    $config = "$UserConfigs/${name}_data.py"
    foreach ($step in $DataScripts) {
        Write-Host "---- $($step[0]) ----" -ForegroundColor Cyan
        Invoke-Native $step[0] "kogine" @("run", $step[1], "--config", $config)
        if ($LASTEXITCODE -ne 0) { return }
    }
    Write-Note "数据准备好了，可以选 5 开始训练。"
}

function Invoke-Train {
    $name = Select-TrainName
    if (-not $name) { return }
    $trainArgs = @("run", "scripts/train/moss.py", "--config", "$UserConfigs/$name.py")
    $lowRam = Read-Host "使用省内存模式? 内存小于 32 GB 建议用 (Y/n)"
    if ($lowRam.Trim() -notmatch "^[nN]") { $trainArgs += $LowRamSets }
    Invoke-Native "训练" "kogine" $trainArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Note "训练完成，成果在 runs\moss\$name\export\，可以选 6 出图。"
    }
}

function Invoke-Sample {
    $name = Select-TrainName
    if (-not $name) { return }
    $adapter = Get-ChildItem "runs\moss\$name\export" -Filter "*-comfy.safetensors" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $adapter) {
        Write-Note "还没找到训练成果 (runs\moss\$name\export\*-comfy.safetensors)，请先选 5 训练。"
        return
    }
    $sampleName = "$name-sample"
    $sampleConfig = "$UserConfigs/$sampleName.py"
    if (-not (Test-Path $sampleConfig)) {
        $relAdapter = Resolve-Path $adapter.FullName -Relative
        $newArgs = @("new", "sample", "--weights", $Weights, "--adapter", $relAdapter, "--name", $sampleName)
        Invoke-Native "生成出图配置" "kohakumoss-config" $newArgs
        if ($LASTEXITCODE -ne 0) { return }
    }
    $prompt = Read-Host "描述想要的画面 (英文效果更稳)"
    if (-not $prompt.Trim()) {
        Write-Note "没有输入画面描述。"
        return
    }
    $runArgs = @("run", "scripts/sample/sample.py", "--config", $sampleConfig, "--set", "PROMPT=$prompt")
    Invoke-Native "出图" "kogine" $runArgs
    if ($LASTEXITCODE -eq 0) { Write-Note "出图完成，图片保存位置见上面的输出。" }
}

# First run: no venv yet, so run the install helper.
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
    Write-Note "没找到 .venv 工具箱，正在运行安装脚本 scripts\install\install.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "install.ps1")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[启动] 安装失败，请看上面的报错信息。" -ForegroundColor Red
        Wait-Enter
        exit 1
    }
}

# Activate the venv for this window and every program it starts.
$env:VIRTUAL_ENV = $Venv
$env:PATH = "$Venv\Scripts;$env:PATH"
$env:PROMPT = '(KohakuMoss) $P$G'

while ($true) {
    Write-Host ""
    Write-Host "===== KohakuMoss 快速启动 =====" -ForegroundColor Cyan
    Write-Host "  1. 环境体检        (kohakumoss-doctor)"
    Write-Host "  2. 生成训练配置    (kohakumoss-config wizard)"
    Write-Host "  3. 下载模型        (约 26 GB，存到 $Weights)"
    Write-Host "  4. 准备数据        (检查数据 + 缓存文字和图片，每份数据做一次)"
    Write-Host "  5. 开始训练"
    Write-Host "  6. 用训练成果出图"
    Write-Host "  7. 打开命令行窗口  (工具箱已激活)"
    Write-Host "  8. 网页界面        (kohakumoss-webui，浏览器里完成以上全部)"
    Write-Host "  9. 退出"
    $pick = Read-Host "请输入 1-9 后按回车"
    switch ($pick.Trim()) {
        "1" { kohakumoss-doctor }
        "2" { kohakumoss-config wizard }
        "3" { hf download OpenMOSS-Team/MOSS-Image-Base --local-dir $Weights }
        "4" { Invoke-PrepareData }
        "5" { Invoke-Train }
        "6" { Invoke-Sample }
        "7" {
            Write-Note "工具箱已激活。输入 exit 回车可以回到菜单。"
            cmd /k
        }
        "8" {
            Write-Note "网页界面启动中，关闭本窗口或按 Ctrl+C 停止。"
            kohakumoss-webui
        }
        "9" { exit 0 }
        default { Write-Note "没看懂 `"$pick`"，请输入 1 到 9 之间的数字。" }
    }
}
