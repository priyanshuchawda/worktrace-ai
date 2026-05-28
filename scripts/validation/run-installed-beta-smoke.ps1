param(
  [switch]$Build,
  [switch]$SkipUninstall,
  [int]$SidecarPort = 18765,
  [int]$DesktopLaunchSeconds = 8,
  [string]$RunId = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$artifactRoot = Join-Path $repoRoot "artifacts\validation\$RunId"
$logPath = Join-Path $artifactRoot "installed-beta-smoke.log"
$evidencePath = Join-Path $artifactRoot "installed-beta-smoke.json"
$installDir = Join-Path $artifactRoot "WorkTraceAI"
$dbDir = Join-Path $artifactRoot "db"
$desktopProcess = $null
$sidecarProcess = $null
$steps = New-Object System.Collections.Generic.List[object]
$startedAt = Get-Date

New-Item -ItemType Directory -Force -Path $artifactRoot, $installDir, $dbDir | Out-Null

function Convert-ToRelativePath([string]$Path) {
  $resolved = [System.IO.Path]::GetFullPath($Path)
  $root = [System.IO.Path]::GetFullPath($repoRoot)
  if ($resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $resolved.Substring($root.Length).TrimStart("\", "/")
  }
  return "[outside-repo]"
}

function Add-Step([string]$Name, [string]$Status, [string]$Detail) {
  $steps.Add([ordered]@{
    name = $Name
    status = $Status
    detail = $Detail
  }) | Out-Null
}

function Invoke-LoggedCommand([string]$Name, [string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory) {
  $stepStarted = Get-Date
  Add-Content -Path $logPath -Value "### $Name"
  Add-Content -Path $logPath -Value "Command: $FilePath $($Arguments -join ' ')"
  $outputPath = Join-Path $artifactRoot "$($Name -replace '[^A-Za-z0-9_-]', '-').log"
  Push-Location $WorkingDirectory
  try {
    & $FilePath @Arguments *> $outputPath
    $exitCode = $LASTEXITCODE
  } finally {
    Pop-Location
  }
  $duration = [math]::Round(((Get-Date) - $stepStarted).TotalSeconds, 1)
  if ($exitCode -ne 0) {
    Add-Step $Name "failed" "exit=$exitCode; duration=${duration}s; log=$(Convert-ToRelativePath $outputPath)"
    throw "$Name failed with exit code $exitCode"
  }
  Add-Step $Name "passed" "duration=${duration}s; log=$(Convert-ToRelativePath $outputPath)"
}

function Stop-ProcessTree($Process) {
  if ($null -eq $Process -or $Process.HasExited) {
    return
  }
  & taskkill.exe /PID $Process.Id /T /F *> $null
  try {
    $Process.WaitForExit(5000) | Out-Null
  } catch {
    # Process already exited.
  }
}

function Write-Evidence([string]$Result, [string]$Reason) {
  $finishedAt = Get-Date
  $evidence = [ordered]@{
    run_id = $RunId
    result = $Result
    reason = $Reason
    started_at = $startedAt.ToString("o")
    finished_at = $finishedAt.ToString("o")
    duration_seconds = [math]::Round(($finishedAt - $startedAt).TotalSeconds, 1)
    no_paid_actions = $true
    live_gemini_called = $false
    model_downloads_started = $false
    installer_signed = $false
    sidecar_port = $SidecarPort
    install_dir = Convert-ToRelativePath $installDir
    steps = $steps
  }
  $evidence | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $evidencePath
}

try {
  Add-Content -Path $logPath -Value "WorkTrace installed-app private beta smoke $RunId"
  if ($Build) {
    Invoke-LoggedCommand "package-sidecar" "pnpm.cmd" @("--dir", "apps/desktop", "package:sidecar") $repoRoot
    Invoke-LoggedCommand "package-windows" "pnpm.cmd" @("--dir", "apps/desktop", "package:windows") $repoRoot
  } else {
    Add-Step "package-build" "skipped" "Run with -Build to rebuild sidecar and NSIS installer."
  }

  $installer = Get-ChildItem -Path (Join-Path $repoRoot "apps\desktop\src-tauri\target\release\bundle\nsis") -Filter "*setup.exe" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $installer) {
    throw "No NSIS setup executable found. Run with -Build after packaging tools are installed."
  }
  Add-Step "installer-found" "passed" (Convert-ToRelativePath $installer.FullName)

  $installProcess = Start-Process -FilePath $installer.FullName -ArgumentList @("/S", "/D=$installDir") -WindowStyle Hidden -Wait -PassThru
  if ($installProcess.ExitCode -ne 0) {
    Add-Step "silent-install" "failed" "exit=$($installProcess.ExitCode)"
    throw "Silent installer failed."
  }
  Add-Step "silent-install" "passed" "exit=0"

  $desktopExe = Join-Path $installDir "worktrace-desktop.exe"
  $sidecarExe = Join-Path $installDir "worktrace-local-agent.exe"
  $uninstallerExe = Join-Path $installDir "uninstall.exe"
  foreach ($expectedFile in @($desktopExe, $sidecarExe, $uninstallerExe)) {
    if (!(Test-Path $expectedFile)) {
      throw "Missing installed file: $(Split-Path $expectedFile -Leaf)"
    }
  }
  Add-Step "installed-files" "passed" "desktop, sidecar, uninstaller present"

  $desktopProcess = Start-Process -FilePath $desktopExe -WorkingDirectory $installDir -PassThru
  Start-Sleep -Seconds $DesktopLaunchSeconds
  if ($desktopProcess.HasExited) {
    Add-Step "desktop-launch" "failed" "desktop exited during ${DesktopLaunchSeconds}s smoke window"
    throw "Installed desktop launch smoke failed."
  }
  Add-Step "desktop-launch" "passed" "running_after_${DesktopLaunchSeconds}s=true"
  Stop-ProcessTree $desktopProcess
  $desktopProcess = $null

  $env:WORKTRACE_SIDECAR_HOST = "127.0.0.1"
  $env:WORKTRACE_SIDECAR_PORT = "$SidecarPort"
  $env:WORKTRACE_DB_PATH = Join-Path $dbDir "worktrace.sqlite"
  $env:WORKTRACE_PRIVACY_POLICY_CONFIG_PATH = Join-Path $artifactRoot "privacy-policy.json"
  $env:WORKTRACE_AI_PROVIDER = "local_ollama"
  $env:WORKTRACE_ENABLE_DEV_CLOUD_AI = "false"
  $env:WORKTRACE_LOCAL_OLLAMA_BASE_URL = "http://127.0.0.1:9"
  $sidecarLog = Join-Path $artifactRoot "installed-sidecar.log"
  $sidecarErrorLog = Join-Path $artifactRoot "installed-sidecar-error.log"
  $sidecarProcess = Start-Process -FilePath $sidecarExe -WorkingDirectory $installDir -WindowStyle Hidden -PassThru -RedirectStandardOutput $sidecarLog -RedirectStandardError $sidecarErrorLog
  $healthUri = "http://127.0.0.1:$SidecarPort/health"
  $health = $null
  for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
      $health = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2
      break
    } catch {
      Start-Sleep -Seconds 1
    }
  }
  if ($null -eq $health -or $health.status -ne "ok") {
    Add-Step "sidecar-health" "failed" "health endpoint did not return ok; log=$(Convert-ToRelativePath $sidecarLog)"
    throw "Installed sidecar health smoke failed."
  }
  Add-Step "sidecar-health" "passed" "status=ok; schema=$($health.schema_version)"
  Stop-ProcessTree $sidecarProcess
  $sidecarProcess = $null

  if ($SkipUninstall) {
    Add-Step "silent-uninstall" "skipped" "SkipUninstall requested."
  } else {
    $uninstallProcess = Start-Process -FilePath $uninstallerExe -ArgumentList @("/S") -WindowStyle Hidden -Wait -PassThru
    Add-Step "silent-uninstall" ($(if ($uninstallProcess.ExitCode -eq 0) { "passed" } else { "failed" })) "exit=$($uninstallProcess.ExitCode)"
    if ($uninstallProcess.ExitCode -ne 0) {
      throw "Silent uninstall failed."
    }
  }

  Write-Evidence "passed" "Installed desktop and sidecar smoke completed with safe aggregate evidence only."
  $duration = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1)
  Write-Output "PASS | pwsh -File scripts/validation/run-installed-beta-smoke.ps1$(if ($Build) { ' -Build' } else { '' }) | ${duration}s | log=$(Convert-ToRelativePath $logPath)"
  Write-Output "RUN_ID=$RunId"
  Write-Output "RESULT=PASS"
} catch {
  Stop-ProcessTree $desktopProcess
  Stop-ProcessTree $sidecarProcess
  Add-Step "failure" "failed" ($_.Exception.Message -replace "AIza[0-9A-Za-z_-]{20,}", "[REDACTED]")
  Write-Evidence "failed" ($_.Exception.Message -replace "AIza[0-9A-Za-z_-]{20,}", "[REDACTED]")
  $duration = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1)
  Write-Output "FAIL | pwsh -File scripts/validation/run-installed-beta-smoke.ps1$(if ($Build) { ' -Build' } else { '' }) | ${duration}s | log=$(Convert-ToRelativePath $logPath)"
  Write-Output "Relevant final lines:"
  Write-Output ($_.Exception.Message -replace "AIza[0-9A-Za-z_-]{20,}", "[REDACTED]")
  Write-Output "RUN_ID=$RunId"
  Write-Output "RESULT=FAIL"
  exit 1
}
