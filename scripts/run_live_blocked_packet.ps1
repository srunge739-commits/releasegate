param(
    [ValidateSet("structure", "understand", "agentic")]
    [string]$Mode = "structure"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$parentVenvPython = Join-Path (Split-Path $projectRoot -Parent) ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $parentVenvPython) {
    $parentVenvPython
} else {
    (Get-Command python -ErrorAction Stop).Source
}

Write-Host "ReleaseGate five-document live Nutrient proof" -ForegroundColor Cyan
Write-Host "Packet: PKT-1001-BLOCKED (synthetic documents)"
Write-Host "Mode: $Mode"
Write-Host "Run this only after the one-invoice credential check succeeds."

$secureKey = Read-Host "Paste the Nutrient Data Extraction API key" -AsSecureString
$keyPointer = [IntPtr]::Zero
$plainKey = $null
$previousKey = $env:NUTRIENT_EXTRACTION_API_KEY
$hadPreviousKey = $null -ne (Get-Item Env:NUTRIENT_EXTRACTION_API_KEY -ErrorAction SilentlyContinue)
$pushedLocation = $false

try {
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw "No API key was entered."
    }
    $env:NUTRIENT_EXTRACTION_API_KEY = $plainKey

    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmssZ")
    $output = "artifacts\live\northstar-packet-$timestamp.json"

    Push-Location $projectRoot
    $pushedLocation = $true
    & $python "scripts\run_cli.py" "evaluate-live-packet" "PKT-1001-BLOCKED" `
        "--mode" $Mode `
        "--output" $output
    if ($LASTEXITCODE -ne 0) {
        throw "The live packet command failed with exit code $LASTEXITCODE."
    }

    Write-Host ""
    Write-Host "Success. The sanitized five-document proof is saved at:" -ForegroundColor Green
    Write-Host (Join-Path $projectRoot $output)
    Write-Host "The saved proof contains request IDs and citations, not the API key."
}
finally {
    if ($pushedLocation) {
        Pop-Location
    }
    if ($hadPreviousKey) {
        $env:NUTRIENT_EXTRACTION_API_KEY = $previousKey
    } else {
        Remove-Item Env:NUTRIENT_EXTRACTION_API_KEY -ErrorAction SilentlyContinue
    }
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $plainKey = $null
    $secureKey = $null
}
