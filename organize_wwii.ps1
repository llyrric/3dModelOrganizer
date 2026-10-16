# WWII Category Organizer Script
param(
    [string]$CategoryPath = "X:\3d files\3d files\WWII",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_wwii_move.csv"
)

$files = Get-ChildItem -Path $CategoryPath -File
Write-Host "Analyzing $($files.Count) loose files in WWII..."

$results = @()

foreach ($f in $files) {
    $name = $f.Name
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext = $f.Extension.ToLower()

    $creator = "WWII & Military"
    $release = "General"
    $item = $baseName

    # 1. 3DBreed Miniatures (Join Or Die WW2 series)
    if ($name -match '(?i)3DBreed\s*Miniatures|Join\s*Or\s*Die') {
        $creator = "3DBreed Miniatures"
        $release = "Join Or Die WW2"
        $item = $baseName -replace '(?i)3DBreed\s*Miniatures\s*[-_ ]*Join\s*Or\s*Die\s*WW2\s*[-_ ]*', ''
    }
    # 2. Soviet / Russian Armor Packs (3F-BL series, T-34, KV, IS, Katyusha)
    elseif ($name -match '(?i)^3F-BL-') {
        $creator = "Soviet Armor 3F"
        $release = "Soviet Armor Series"
        $item = $baseName
    }
    # 3. RKX Miniatures
    elseif ($name -match '(?i)RKX\s*Miniatures') {
        $creator = "RKX Miniatures"
        $item = $baseName -replace '(?i)RKX\s*Miniatures\s*[-_ ]*', ''
    }
    # 4. British forces & armor
    elseif ($name -match '(?i)british|churchill|cromwell|crusader|bren|sherman\s*firefly') {
        $creator = "british"
        $item = $baseName
    }
    # 5. German forces & armor
    elseif ($name -match '(?i)german|panzer|tiger|panther|wehrmacht|waffen|stug|sdkfz') {
        $creator = "german"
        $item = $baseName
    }
    # 6. US / Allied Forces (Willys Jeep, US Paratroopers, Destroyed trucks)
    elseif ($name -match '(?i)US\s*Paratroopers|US_WILLYS|DESTROYED\s*TRUCKS|Civils\s*WW2|US\s*Infantry') {
        $creator = "Military & Armor"
        $item = $baseName
    }

    # Clean up item text
    $item = ($item -replace '(?i)\.(zip|rar|7z|stl|jpg|png|obj)(\.00\d+)?$', '' -replace '@[a-zA-Z0-9_]+', '' -replace '\?@[a-zA-Z0-9_]+\?', '' -replace '\(\d+\)', '' -replace '_', ' ' -replace '\s+', ' ').Trim(' -_')
    if (-not $item) { $item = $baseName }

    # Proposed destination folder
    $destFolder = ""
    if ($release -ne "General") {
        $destFolder = Join-Path (Join-Path $CategoryPath $creator) $release
    } else {
        $destFolder = Join-Path $CategoryPath $creator
    }

    $newFileName = ""
    if ($release -ne "General") {
        $newFileName = "$creator - $release - $item$ext"
    } else {
        $newFileName = "$creator - $item$ext"
    }

    $results += [PSCustomObject]@{
        OriginalFile = $name
        Extension    = $ext
        Category     = "WWII"
        Creator      = $creator
        Release      = $release
        CleanItem    = $item
        NewFileName  = $newFileName
        DestFolder   = $destFolder
    }
}

$results | Export-Csv -Path $OutputCsv -NoTypeInformation
Write-Host "Exported proposed WWII moves to $OutputCsv"
$results | Group-Object Creator | Select-Object Count, Name | Sort-Object Count -Descending | Format-Table -AutoSize
