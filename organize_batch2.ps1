# PowerShell Classifier Script for 3D Library Files (Pass 2 - Major Studios)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization_batch2.csv"
)

$files = Get-ChildItem -Path $SourcePath -File
Write-Host "Analyzing $($files.Count) remaining root files..."

$results = @()

foreach ($f in $files) {
    $name = $f.Name
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext = $f.Extension.ToLower()

    $cat = "other"
    $creator = "Unknown Creator"
    $release = "General"
    $item = $baseName

    # 1. UNIT9 (Cyberpunk / Sci-Fi)
    if ($name -match '(?i)^UNIT9\s*[-_ ]*(.*)') {
        $cat = "cyberpunk"
        $creator = "UNIT9"
        $item = $Matches[1]
    }
    # 2. TytanTroll / Tytan Troll
    elseif ($name -match '(?i)Tytan\s*Troll\s*(\d{2}\.?\s*[A-Za-z]+\s*\d{4}|\d{6}|[A-Za-z]+\s*\d{4})(.*)') {
        $cat = "fantasy"
        $creator = "TytanTroll Miniatures"
        $release = ($Matches[1] -replace 'By\s*AiR', '').Trim(' .-_')
        $item = ($Matches[2] -replace 'By\s*AiR', '').Trim(' .-_')
        if (-not $item) { $item = "Monthly Release" }
    }
    elseif ($name -match '(?i)Tytan\s*Troll') {
        $cat = "fantasy"
        $creator = "TytanTroll Miniatures"
        $item = $baseName -replace '(?i)Tytan\s*Troll\s*[-_ ]*', ''
    }
    # 3. The Dragon Trappers Lodge
    elseif ($name -match '(?i)The[-_ ]Dragon[-_ ]Trappers[-_ ]Lodge') {
        $cat = "fantasy"
        $creator = "Dragon Trappers Lodge"
        if ($name -match '(?i)(The[-_ ]Gunslinger[-_ ]Lodge)') {
            $release = "The Gunslinger Lodge"
        } elseif ($name -match '(?i)([A-Za-z]+\s*\d{4})') {
            $release = $Matches[1]
        }
        $item = $baseName -replace '(?i)The[-_ ]Dragon[-_ ]Trappers[-_ ]Lodge[-_ ]*|The[-_ ]Gunslinger[-_ ]Lodge[-_ ]*', ''
    }
    # 4. The Makers Cult / The Maker's Cult
    elseif ($name -match '(?i)The\s*Maker''?s\s*Cult\s*[-_ ]*(\d{4}[-_]?\d{2}|[A-Za-z]+\s*\d{4})?\s*[-_ ]*(.*)') {
        $cat = "sci fi"
        $creator = "The Makers Cult"
        if ($Matches[1]) { $release = $Matches[1] }
        $item = if ($Matches[2]) { $Matches[2] } else { $baseName }
    }
    elseif ($name -match '(?i)The\s*Maker''?s\s*Cult') {
        $cat = "sci fi"
        $creator = "The Makers Cult"
        $item = $baseName -replace '(?i)The\s*Maker''?s\s*Cult\s*[-_ ]*', ''
    }
    # 5. STL Miniatures
    elseif ($name -match '(?i)STL\s*Miniatures\s*[-_ ]*(\d{4}[-_]?\d{2}|\d{2}[-_]\d{4})?\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "STL Miniatures"
        if ($Matches[1]) { $release = $Matches[1] }
        $item = if ($Matches[2]) { $Matches[2] } else { $baseName }
    }
    # 6. CobraMode
    elseif ($name -match '(?i)CobraMode\s*(\d+)?\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "CobraMode"
        if ($Matches[1]) { $release = "Collection " + $Matches[1] }
        $item = $Matches[2]
    }
    # 7. White Werewolf Tavern
    elseif ($name -match '(?i)White\s*Werewolf\s*Tavern\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "White Werewolf Tavern"
        $item = $Matches[1]
    }
    # 8. Artisan Guild
    elseif ($name -match '(?i)Artisan\s*Guild') {
        $cat = "fantasy"
        $creator = "Artisan Guild"
        $item = $baseName -replace '(?i)Artisan\s*Guild\s*[-_ ]*', ''
    }
    # 9. Galaad Miniatures
    elseif ($name -match '(?i)Galaad\s*Miniatures') {
        $cat = "fantasy"
        $creator = "Galaad Miniatures"
        $item = $baseName -replace '(?i)Galaad\s*Miniatures\s*[-_ ]*', ''
    }
    # 10. Star Wars Legion / Galaxy proxies
    elseif ($name -match '(?i)Star\s*Wars|Star\s*Destroyer|Pocket\s*Dimension|Scout\s*Troopers|Star\s*Lord|Peter\s*Quill') {
        $cat = "sci fi"
        $creator = "Star Wars Galaxy"
        $item = $baseName
    }
    # 11. Highlands Miniatures
    elseif ($name -match '(?i)highlands\s*miniatures') {
        $cat = "fantasy"
        $creator = "Highlands Miniatures"
        $item = $baseName
    }
    # 12. TXarli Factory
    elseif ($name -match '(?i)TXarli\s*Factory|Txarli') {
        $cat = "terrain"
        $creator = "Txarli Factory"
        $item = $baseName
    }
    # 13. Wightwood Abbey / Terrain
    elseif ($name -match '(?i)Wightwood[-_ ]Abbey|Stalingrad.*Factory|WD2-Barbican|Shadowdale') {
        $cat = "terrain"
        $creator = "Terrain Scenery"
        $item = $baseName
    }
    # 14. Pokemon
    elseif ($name -match '(?i)Umbreon|Pikachu|Charizard|Pokemon') {
        $cat = "pokemon"
        $creator = "Pokemon Models"
        $item = $baseName
    }
    # 15. Warhammer Skaven / Ratkin / Warhammer 40k Tau / Voluptuaris
    elseif ($name -match '(?i)Ratas\s*Ogro|Skaven|Ratkin|Veer-Myn') {
        $cat = "fantasy"
        $creator = "Skaven Ratkin"
        $item = $baseName
    }
    elseif ($name -match '(?i)WH40K|Tau_Cadre|Voluptuaris') {
        $cat = "sci fi"
        $creator = "Warhammer 40k Proxies"
        $item = $baseName
    }
    # 16. Marvel / DC / Superheroes
    elseif ($name -match '(?i)marvel\s*dc|Spider\s*Gwen') {
        $cat = "superheros"
        $creator = "Marvel & DC"
        $item = $baseName
    }
    # 17. The Lazy Forger
    elseif ($name -match '(?i)The\s*Lazy\s*Forger') {
        $cat = "smaller scale"
        $creator = "The Lazy Forger"
        $item = $baseName -replace '(?i)The\s*Lazy\s*Forger\s*[-_ ]*', ''
    }

    # Clean up item naming
    $item = ($item -replace '(?i)\.(zip|rar|7z|stl|jpg|png|obj)$', '' -replace '@[a-zA-Z0-9_]+', '' -replace '\(\d+\)', '' -replace '_', ' ' -replace '\s+', ' ').Trim(' -_')
    if (-not $item) { $item = $baseName }

    # Proposed file and folder paths
    $newFileName = ""
    if ($creator -ne "Unknown Creator" -and $release -ne "General") {
        $newFileName = "$creator - $release - $item$ext"
    } elseif ($creator -ne "Unknown Creator") {
        $newFileName = "$creator - $item$ext"
    } else {
        $newFileName = "$item$ext"
    }

    $destFolder = ""
    if ($release -ne "General") {
        $destFolder = Join-Path (Join-Path (Join-Path $SourcePath $cat) $creator) $release
    } else {
        $destFolder = Join-Path (Join-Path $SourcePath $cat) $creator
    }

    $results += [PSCustomObject]@{
        OriginalFile = $name
        Extension    = $ext
        Category     = $cat
        Creator      = $creator
        Release      = $release
        CleanItem    = $item
        NewFileName  = $newFileName
        DestFolder   = $destFolder
    }
}

$results | Export-Csv -Path $OutputCsv -NoTypeInformation
Write-Host "Exported proposed organization mapping to $OutputCsv"

$matchedCount = ($results | Where-Object { $_.Creator -ne "Unknown Creator" }).Count
Write-Host "Matched with identified creators in Batch 2: $matchedCount of $($results.Count)"
