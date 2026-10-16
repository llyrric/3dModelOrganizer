# 3D Library Organizer: Batch Move Execution Script
param(
    [string]$MappingCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization.csv",
    [switch]$Execute = $false
)

$mapping = Import-Csv $MappingCsv
$matched = $mapping | Where-Object { $_.Creator -ne "Unknown Creator" }

Write-Host "Total files to organize in this batch: $($matched.Count)"
if (-not $Execute) {
    Write-Host "[DRY RUN MODE] No files will be moved. Pass -Execute to run live migration." -ForegroundColor Yellow
}

$movedCount = 0
$errorCount = 0

foreach ($row in $matched) {
    $sourceFile = Join-Path "X:\3d files\3d files" $row.OriginalFile
    $destFolder = $row.DestFolder
    $destFile = Join-Path $destFolder $row.NewFileName

    if (-not (Test-Path -LiteralPath $sourceFile)) {
        Write-Warning "Source file not found: $sourceFile"
        continue
    }

    if ($Execute) {
        try {
            if (-not (Test-Path -LiteralPath $destFolder)) {
                New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
            }
            Move-Item -LiteralPath $sourceFile -Destination $destFile -Force
            $movedCount++
            Write-Host "MOVED: $($row.OriginalFile) -> $destFile" -ForegroundColor Green
        } catch {
            Write-Error "Failed to move $($row.OriginalFile): $_"
            $errorCount++
        }
    } else {
        Write-Host "WOULD MOVE: $($row.OriginalFile) -> $destFile"
    }
}

Write-Host "`nSummary:"
Write-Host "Processed: $($matched.Count)"
if ($Execute) {
    Write-Host "Successfully Moved: $movedCount" -ForegroundColor Green
    Write-Host "Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })
}
