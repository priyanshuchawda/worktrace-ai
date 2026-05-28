param(
  [Parameter(Mandatory = $true)]
  [string]$ArtifactPath,

  [ValidateSet("dev", "alpha", "store-beta", "store-stable")]
  [string]$Channel = "alpha",

  [switch]$AllowInstallableBinaries
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$resolvedPath = Resolve-Path -LiteralPath $ArtifactPath -ErrorAction Stop
$root = $resolvedPath.Path

$installableExtensions = @(
  ".exe",
  ".msi",
  ".msix",
  ".msixbundle",
  ".appx",
  ".appxbundle",
  ".zip"
)

$files = Get-ChildItem -LiteralPath $root -File -Recurse -Force
$blocked = @(
  $files | Where-Object {
    $installableExtensions -contains $_.Extension.ToLowerInvariant()
  }
)

if ($blocked.Count -eq 0) {
  Write-Output "PASS | release artifact policy | channel=$Channel | path=$root"
  exit 0
}

$approval = [Environment]::GetEnvironmentVariable("WORKTRACE_APPROVE_INSTALLER_RELEASE")
$approvalAccepted = $approval -eq "I_UNDERSTAND_STORE_OR_SIGNED_CHANNEL"
$storeChannel = $Channel -in @("store-beta", "store-stable")

if ($AllowInstallableBinaries -and $storeChannel -and $approvalAccepted) {
  Write-Output "PASS | release artifact policy | channel=$Channel | installable artifacts explicitly approved"
  exit 0
}

Write-Output "FAIL | release artifact policy | channel=$Channel | path=$root"
Write-Output "Installable/update-like artifacts are blocked by default:"
foreach ($file in $blocked | Select-Object -First 20) {
  $relative = [System.IO.Path]::GetRelativePath($root, $file.FullName)
  Write-Output "- $relative"
}
if ($blocked.Count -gt 20) {
  Write-Output "- ... $($blocked.Count - 20) more"
}
Write-Output "Do not attach unsigned installer/update artifacts to public GitHub Releases."
Write-Output "Use source-only alpha releases until Store/MSIX distribution is approved and validated."
exit 1
