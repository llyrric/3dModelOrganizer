# Terrain Category Organizer Script
param(
    [string]$CategoryPath = "X:\3d files\3d files\terrain",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_terrain_move.csv"
)

$files = Get-ChildItem -Path $CategoryPath -File
Write-Host "Analyzing $($files.Count) loose files in terrain..."

$results = @()

foreach ($f in $files) {
    $name = $f.Name
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext = $f.Extension.ToLower()

    $creator = "Terrain Scenery"
    $release = "General"
    $item = $baseName

    # 1. Cast N Play (Terrain Essentials)
    if ($name -match '(?i)Cast\s*N\s*Play|Terrain\s*Essentials') {
        $creator = "Cast N Play"
        $release = "Terrain Essentials"
        $item = $baseName -replace '(?i)\[?Cast\s*N\s*Play\]?[-_ ]*|Terrain\s*Essentials[-_ ]*', ''
    }
    # 2. Corvus Games
    elseif ($name -match '(?i)\[Corvus\]|Corvus\s*Games') {
        $creator = "corvus games"
        $item = $baseName -replace '(?i)\[Corvus\][-_ ]*', ''
    }
    # 3. Last Sword Miniatures ([LS] Undercaves)
    elseif ($name -match '(?i)\[LS\]|Last\s*Sword') {
        $creator = "Last Sword Miniatures"
        $item = $baseName -replace '(?i)\[LS\][-_ ]*', ''
    }
    # 4. War Scenery
    elseif ($name -match '(?i)War\s*Scenery') {
        $creator = "war scenery"
        $item = $baseName
    }
    # 5. Fat Dragon Games
    elseif ($name -match '(?i)Fat\s*Dragon') {
        $creator = "fat dragon games"
        $item = $baseName
    }
    # 6. Terrainify
    elseif ($name -match '(?i)Terrainify') {
        $creator = "terrainify"
        $item = $baseName
    }
    # 7. Txarli Factory
    elseif ($name -match '(?i)Txarli\s*Factory|Txarli') {
        $creator = "txarli factory"
        $item = $baseName
    }
    # 8. Dungeon Forge / Dungeon Blocks
    elseif ($name -match '(?i)Dungeon\s*Forge|Dungeon\s*Blocks') {
        $creator = "dungeon forge"
        $item = $baseName
    }
    # 9. Dragon's Rest
    elseif ($name -match '(?i)Dragon''?s\s*Rest') {
        $creator = "dragon's rest"
        $item = $baseName
    }
    # 10. Makers Anvil / Hexengarde
    elseif ($name -match '(?i)Makers\s*Anvil|Hexengarde') {
        $creator = "Makers Anvil"
        $item = $baseName
    }
    # 11. Dark Realms
    elseif ($name -match '(?i)Dark\s*Realms') {
        $creator = "Dark realms"
        $item = $baseName
    }
    # 12. Modular Buildings & Taverns (Alchemists House, Abbot's House, Adventurer Camp)
    elseif ($name -match '(?i)House|Tavern|Camp|Alchemists|Abbot|Church|Temple') {
        $creator = "Modular Buildings & Interiors"
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
        Category     = "terrain"
        Creator      = $creator
        Release      = $release
        CleanItem    = $item
        NewFileName  = $newFileName
        DestFolder   = $destFolder
    }
}

$results | Export-Csv -Path $OutputCsv -NoTypeInformation
Write-Host "Exported proposed terrain moves to $OutputCsv"
$results | Group-Object Creator | Select-Object Count, Name | Sort-Object Count -Descending | Format-Table -AutoSize
