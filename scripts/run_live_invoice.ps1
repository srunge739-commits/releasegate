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

Write-Host "ReleaseGate genuine Nutrient extraction" -ForegroundColor Cyan
Write-Host "Document: synthetic Northstar invoice"
Write-Host "Mode: $Mode"
Write-Host "The key will be hidden and removed from this PowerShell process after the request."

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
    $output = "artifacts\live\northstar-invoice-$timestamp.json"

    Push-Location $projectRoot
    $pushedLocation = $true
    & $python "scripts\run_cli.py" "extract-live" `
        "assets\demo-documents\PKT-1001-BLOCKED\northstar-invoice-1048.pdf" `
        "--schema" "assets\schemas\invoice.json" `
        "--mode" $Mode `
        "--output" $output
    if ($LASTEXITCODE -ne 0) {
        throw "The extraction command failed with exit code $LASTEXITCODE."
    }

    Write-Host "" 
    Write-Host "Success. The sanitized proof is saved at:" -ForegroundColor Green
    Write-Host (Join-Path $projectRoot $output)
    Write-Host "Do not share the API key. The saved proof does not contain it."
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
