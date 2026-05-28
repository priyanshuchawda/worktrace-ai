param(
  [ValidateSet("Shared", "Desktop", "Python", "Rust", "Packaging", "GeminiSmoke", "All")]
  [string]$Scope = "All",
  [string]$RunId,
  [int]$FailureTailLines = 12
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if ([string]::IsNullOrWhiteSpace($RunId)) {
  $RunId = Get-Date -Format "yyyyMMdd-HHmmss"
}

$artifactRoot = Join-Path $repoRoot "artifacts\validation\$RunId"
New-Item -ItemType Directory -Force $artifactRoot | Out-Null

function Redact-Line {
  param([string]$Line)

  $redacted = $Line
  $redacted = $redacted -replace "AIza[0-9A-Za-z_-]{20,}", "[REDACTED]"
  $redacted = $redacted -replace "github_pat_[0-9A-Za-z_]+", "[REDACTED]"
  $redacted = $redacted -replace "ghp_[0-9A-Za-z_]+", "[REDACTED]"
  $redacted = $redacted -replace "sk-[0-9A-Za-z_-]{16,}", "[REDACTED]"
  $redacted = $redacted -replace "(?i)(authorization:\s*bearer\s+)[^\s]+", "`$1[REDACTED]"
  $redacted = $redacted -replace "(?i)\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|PASS|KEY)[A-Z0-9_]*=)([^\s;&|]+)", "`$1[REDACTED]"
  return $redacted
}

function Format-Duration {
  param([TimeSpan]$Duration)
  return "{0:n1}s" -f $Duration.TotalSeconds
}

function Get-Tool {
  param([string[]]$Candidates)

  foreach ($candidate in $Candidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -ne $command) {
      return $candidate
    }
  }
  return $Candidates[0]
}

$pnpm = Get-Tool @("pnpm.cmd", "pnpm")
$uv = Get-Tool @("uv.exe", "uv")
$cargo = Get-Tool @("cargo.exe", "cargo")

$gates = @(
  [pscustomobject]@{
    Scope = "Shared"
    Id = "shared-typecheck"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "packages/shared", "typecheck")
  },
  [pscustomobject]@{
    Scope = "Shared"
    Id = "shared-test"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "packages/shared", "test")
  },
  [pscustomobject]@{
    Scope = "Desktop"
    Id = "desktop-typecheck"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "apps/desktop", "typecheck")
  },
  [pscustomobject]@{
    Scope = "Desktop"
    Id = "desktop-lint"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "apps/desktop", "lint")
  },
  [pscustomobject]@{
    Scope = "Desktop"
    Id = "desktop-test"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "apps/desktop", "test")
  },
  [pscustomobject]@{
    Scope = "Desktop"
    Id = "desktop-build"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "apps/desktop", "build")
  },
  [pscustomobject]@{
    Scope = "Python"
    Id = "python-ruff-format-check"
    WorkDir = Join-Path $repoRoot "services/local-agent"
    Exe = $uv
    Args = @("run", "--python", "3.13", "ruff", "format", "--check", ".")
  },
  [pscustomobject]@{
    Scope = "Python"
    Id = "python-ruff-check"
    WorkDir = Join-Path $repoRoot "services/local-agent"
    Exe = $uv
    Args = @("run", "--python", "3.13", "ruff", "check", ".")
  },
  [pscustomobject]@{
    Scope = "Python"
    Id = "python-pyright"
    WorkDir = Join-Path $repoRoot "services/local-agent"
    Exe = $uv
    Args = @("run", "--python", "3.13", "pyright")
  },
  [pscustomobject]@{
    Scope = "Python"
    Id = "python-pytest"
    WorkDir = Join-Path $repoRoot "services/local-agent"
    Exe = $uv
    Args = @("run", "--python", "3.13", "pytest")
  },
  [pscustomobject]@{
    Scope = "Rust"
    Id = "rust-fmt"
    WorkDir = Join-Path $repoRoot "apps/desktop/src-tauri"
    Exe = $cargo
    Args = @("fmt", "--all", "--", "--check")
  },
  [pscustomobject]@{
    Scope = "Rust"
    Id = "rust-clippy"
    WorkDir = Join-Path $repoRoot "apps/desktop/src-tauri"
    Exe = $cargo
    Args = @("clippy", "--workspace", "--all-targets", "--", "-D", "warnings")
  },
  [pscustomobject]@{
    Scope = "Rust"
    Id = "rust-test"
    WorkDir = Join-Path $repoRoot "apps/desktop/src-tauri"
    Exe = $cargo
    Args = @("test", "--workspace")
  },
  [pscustomobject]@{
    Scope = "Packaging"
    Id = "package-sidecar"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "apps/desktop", "package:sidecar")
  },
  [pscustomobject]@{
    Scope = "Packaging"
    Id = "package-windows"
    WorkDir = $repoRoot
    Exe = $pnpm
    Args = @("--dir", "apps/desktop", "package:windows")
  },
  [pscustomobject]@{
    Scope = "GeminiSmoke"
    Id = "gemini-dev-smoke"
    WorkDir = Join-Path $repoRoot "services/local-agent"
    Exe = $uv
    Args = @("run", "--python", "3.13", "python", "-m", "worktrace_agent.scripts.smoke_gemini_gemma_dev_report")
  }
)

if ($Scope -eq "All") {
  $selectedScopes = @("Shared", "Desktop", "Python")
} else {
  $selectedScopes = @($Scope)
}

$selectedGates = $gates | Where-Object { $selectedScopes -contains $_.Scope }
$failed = $false

foreach ($gate in $selectedGates) {
  $displayCommand = "$($gate.Exe) $($gate.Args -join ' ')"
  $logPath = Join-Path $artifactRoot "$($gate.Id).log"
  $relativeLogPath = $logPath.Replace($repoRoot, "").TrimStart("\").TrimStart("/")
  $start = Get-Date

  Push-Location $gate.WorkDir
  try {
    $tool = Get-Command $gate.Exe -ErrorAction SilentlyContinue
    if ($null -eq $tool) {
      "Tool not found: $($gate.Exe)" | Set-Content -Path $logPath -Encoding UTF8
      $exitCode = 127
    } else {
      $oldPreference = $ErrorActionPreference
      $ErrorActionPreference = "Continue"
      & $gate.Exe @($gate.Args) *> $logPath
      $exitCode = $LASTEXITCODE
      $ErrorActionPreference = $oldPreference
      if ($null -eq $exitCode) {
        $exitCode = 0
      }
    }
  } catch {
    $_ | Out-String | Set-Content -Path $logPath -Encoding UTF8
    $exitCode = 1
  } finally {
    Pop-Location
  }

  $duration = Format-Duration ((Get-Date) - $start)
  if ($exitCode -eq 0) {
    Write-Output "PASS | $displayCommand | $duration | log=$relativeLogPath"
  } else {
    $failed = $true
    Write-Output "FAIL | $displayCommand | $duration | log=$relativeLogPath"
    Write-Output "Relevant final lines:"
    if (Test-Path $logPath) {
      Get-Content -Path $logPath -Tail $FailureTailLines | ForEach-Object {
        Write-Output (Redact-Line $_)
      }
    }
  }
}

Write-Output "RUN_ID=$RunId"
if ($failed) {
  Write-Output "RESULT=FAIL"
  exit 1
}

Write-Output "RESULT=PASS"
