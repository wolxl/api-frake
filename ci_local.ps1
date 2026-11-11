# 本地复现 CI：装依赖 → 建库 → 起服务 → 跑用例 → 出报告
# 用法：powershell -ExecutionPolicy Bypass -File ci_local.ps1 -MysqlPassword "你的密码"
# 说明：这是 GitHub Actions 的本地替身，用来在 push 之前先确认流水线能绿。

param(
    [Parameter(Mandatory = $true)][string]$MysqlPassword,
    [string]$MysqlExe = "D:\MySQL\MySQL Server 8.0\bin\mysql.exe",
    [string]$PythonExe = "C:\Users\86189\AppData\Local\Programs\Python\Python314\python.exe",
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

$log = Join-Path $root "app_ci.log"
$err = Join-Path $root "app_ci.log.err"
Remove-Item $log, $err, "allure-results", "reports" -Recurse -Force -ErrorAction SilentlyContinue

try {
    # ---------- 第 3 步：装依赖 ----------
    Write-Host "[1/5] 装依赖 ..." -ForegroundColor Cyan
    & $PythonExe -m pip install -q -r mall_server\requirements.txt -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw "依赖安装失败" }

    # ---------- 第 4 步：初始化数据库 ----------
    Write-Host "[2/5] 初始化数据库 ..." -ForegroundColor Cyan
    $mysqlArgs = @("-h", "127.0.0.1", "-P", "3306", "-u", "root", "-p$MysqlPassword")
    Get-Content mall_server\schema.sql -Raw -Encoding UTF8 | & $MysqlExe @mysqlArgs
    if ($LASTEXITCODE -ne 0) { throw "schema.sql 执行失败" }
    Get-Content mall_server\seed.sql -Raw -Encoding UTF8 | & $MysqlExe @mysqlArgs
    if ($LASTEXITCODE -ne 0) { throw "seed.sql 执行失败" }

    # ---------- 第 5 步：生成 config.py ----------
    Write-Host "[3/5] 生成 config.py ..." -ForegroundColor Cyan
    Copy-Item mall_server\config.example.py mall_server\config.py -Force
    $c = Get-Content mall_server\config.py -Raw -Encoding UTF8
    $c = [regex]::Replace($c, '"password":\s*"[^"]*"', '"password": "' + $MysqlPassword + '"')
    [System.IO.File]::WriteAllText((Join-Path $root "mall_server\config.py"), $c, [System.Text.UTF8Encoding]::new($false))

    # ---------- 第 6 步：起服务 + 健康检查 ----------
    Write-Host "[4/5] 启动服务并等待就绪 ..." -ForegroundColor Cyan
    $srv = Start-Process -FilePath $PythonExe -ArgumentList @("wsgi.py") `
        -WorkingDirectory (Join-Path $root "mall_server") `
        -RedirectStandardOutput $log -RedirectStandardError $err -PassThru -WindowStyle Hidden

    $up = $false
    for ($i = 1; $i -le 30; $i++) {
        $code = (& curl.exe -s -o NUL -w "%{http_code}" --max-time 2 "http://127.0.0.1:$Port/api/health") 2>$null
        if ($code -eq "200") { Write-Host "  服务已就绪，用时 ${i}s"; $up = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $up) {
        Write-Host "  服务 30 秒内没起来，最后的 HTTP code = $code" -ForegroundColor Red
        if (Test-Path $err) { Get-Content $err -Encoding UTF8 | Select-Object -Last 20 }
        throw "服务未就绪"
    }

    # ---------- 第 7 步：跑用例 ----------
    Write-Host "[5/5] 跑接口用例 ..." -ForegroundColor Cyan
    & $PythonExe -m pytest testcases -v --junitxml=reports\junit.xml --alluredir=allure-results
    $testExit = $LASTEXITCODE

    if ($testExit -eq 0) {
        Write-Host "`n✅ 流水线绿：用例全部通过" -ForegroundColor Green
        Write-Host "   JUnit 报告: reports\junit.xml"
        Write-Host "   Allure 原始结果: allure-results\"
        Write-Host "   看 HTML 报告需要 allure 命令行: allure generate allure-results -o allure-report"
    }
    else {
        Write-Host "`n❌ 有用例失败（退出码 $testExit），下面是失败项：" -ForegroundColor Red
        if (Test-Path "reports\junit.xml") {
            Select-String -Path "reports\junit.xml" -Pattern "<failure|<error" | Select-Object -First 20
        }
    }
    exit $testExit
}
finally {
    if ($srv) { Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "服务已停止" -ForegroundColor DarkGray
    Pop-Location
}
