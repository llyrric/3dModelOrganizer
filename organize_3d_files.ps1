# PowerShell Classifier Script for 3D Library Files (Comprehensive Pattern Set)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization.csv"
)

$files = Get-ChildItem -Path $SourcePath -File
Write-Host "Analyzing $($files.Count) root files..."

$results = @()

foreach ($f in $files) {
    $name = $f.Name
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext = $f.Extension.ToLower()

    $cat = "other"
    $creator = "Unknown Creator"
    $release = "General"
    $item = $baseName

    # 1. Skull Forge Studios (SW Legion proxy codes SQ, PD, BR, HU, VT, BH)
    if ($name -match '(?i)(?:^|[-_ ])(SQ\d+|PD\d+|BR\d+|HU\d+|BH\d+|VT\d+)(?:[-_ .]|$)') {
        $code = $Matches[1].ToUpper()
        $cat = "sci fi"
        $creator = "Skull Forge Studios"
        $release = $code
        $item = ($baseName -replace '(?i)Skull\s*Forge\s*[-_ ]*', '' -replace "(?i)[-_ ]*$code[-_ ]*", '').Trim(' -_')
    }
    # 2. Cyber Forge
    elseif ($name -match '(?i)Cyber\s*Forge') {
        $cat = "cyberpunk"
        $creator = "Cyber Forge"
        $item = $baseName -replace '(?i)Cyber\s*Forge\s*[-_ ]*|[-_ ]*Cyber\s*Forge', ''
    }
    # 3. Galaad Miniatures
    elseif ($name -match '(?i)Galaad\s*Miniatures') {
        $cat = "fantasy"
        $creator = "Galaad Miniatures"
        if ($name -match '(?i)([A-Za-z]+_Release|\d{4}[-_]\d{2})') { $release = $Matches[1] }
        $item = $baseName -replace '(?i)Galaad\s*Miniatures\s*[-_ ]*|[-_ ]*Galaad\s*Miniatures', ''
    }
    # 4. Surrogate Miniatures
    elseif ($name -match '(?i)Surrogate\s*Miniatures') {
        $cat = "sci fi"
        $creator = "Surrogate Miniatures"
        $item = $baseName -replace '(?i)Surrogate\s*Miniatures\s*[-_ ]*|[-_ ]*Surrogate\s*Miniatures', ''
    }
    # 5. Sanix
    elseif ($name -match '(?i)^SANIX\s*[-_ ]*(.*)') {
        $cat = "superheros"
        $creator = "Sanix"
        $item = $Matches[1]
    }
    # 6. RKX Miniatures (WWII / Military)
    elseif ($name -match '(?i)RKX\s*MINIATURES') {
        $cat = "WWII"
        $creator = "RKX Miniatures"
        $item = $baseName -replace '(?i)RKX\s*MINIATURES\s*[-_ ]*', ''
    }
    # 7. Red Pilgrim / Red Butchers
    elseif ($name -match '(?i)^RP\s*-\s*(.*)|Red\s*Pilgrim\s*[-_ ]*(.*)') {
        $cat = "sci fi"
        $creator = "Red Pilgrim"
        $item = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
    }
    # 8. Red Makers
    elseif ($name -match '(?i)red\s*makers\s*[-_ ]*(.*)') {
        $cat = "sci fi"
        $creator = "Red Makers"
        $item = $Matches[1]
    }
    # 9. OnePageRules - Reptilian / Saurian Ancients / Grimdark Future
    elseif ($name -match '(?i)^reptilian\s+(.*)') {
        $cat = "fantasy"
        $creator = "OnePageRules"
        $release = "Saurian Ancients"
        $item = $Matches[1]
    }
    elseif ($name -match '(?i)Grimdark\s+Future') {
        $cat = "sci fi"
        $creator = "OnePageRules"
        $release = "Grimdark Future"
        $item = $baseName -replace '(?i)\+?-?\+?Grimdark\+?Future', ''
    }
    # 10. Sacrusmundus
    elseif ($name -match '(?i)Sacrusmundus\s+(\d{2}[-_]?\d{2})\s*(.*)') {
        $cat = "sci fi"
        $creator = "Sacrusmundus"
        $release = $Matches[1] -replace '_', '-'
        $item = $Matches[2].Trim()
    }
    elseif ($name -match '(?i)Sacrusmundus') {
        $cat = "sci fi"
        $creator = "Sacrusmundus"
        $item = $baseName -replace '(?i)by\s*Sacrusmundus|Sacrusmundus', ''
    }
    # 11. Sons of Ymir (Dwarf army)
    elseif ($name -match '(?i)^SoY\s+Dwarf\s+(.*)') {
        $cat = "fantasy"
        $creator = "Sons of Ymir"
        $release = "Dwarfs"
        $item = $Matches[1]
    }
    elseif ($name -match '(?i)Sons\s+of\s+Ymir\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "Sons of Ymir"
        $item = $Matches[1]
    }
    # 12. Raven Twin Miniatures
    elseif ($name -match '(?i)Raven\s*Twin\s+([A-Za-z]+)\s+(\d{4})(.*)') {
        $cat = "fantasy"
        $creator = "Raven Twin Miniatures"
        $release = "$($Matches[1]) $($Matches[2])"
        $item = ($Matches[3] -replace '(?i)^[-_ ]*', '').Trim()
        if (-not $item) { $item = "Release Pack" }
    }
    # 13. Last Sword Miniatures
    elseif ($name -match '(?i)Last\s*Sword\s*Miniatures') {
        $cat = "fantasy"
        $creator = "Last Sword Miniatures"
        $item = $baseName -replace '(?i)\(Last\s*Sword\s*Miniatures\)|Last\s*Sword\s*Miniatures', ''
    }
    # 14. Mezgike
    elseif ($name -match '(?i)by\s*Mezgike|Mezgike') {
        $cat = "sci fi"
        $creator = "Mezgike"
        $item = $baseName -replace '(?i)by\s*Mezgike|Mezgike', ''
    }
    # 15. Dark Fire Designs
    elseif ($name -match '(?i)DarkFire|Dark\s*Fire') {
        $cat = "sci fi"
        $creator = "Dark Fire Designs"
        $item = $baseName -replace '(?i)DarkFire_?|Dark\s*Fire\s*Designs?', ''
    }
    # 16. RN Estudio
    elseif ($name -match '(?i)RN\s*Estudio|RNEstudio') {
        $cat = "fantasy"
        $creator = "RN Estudio"
        $item = $baseName -replace '(?i)RN\s*Estudio\s*[-_ ]*|RNEstudio\s*[-_ ]*', ''
    }
    # 17. Runic Collectibles
    elseif ($name -match '(?i)Runic\s*Collectibles') {
        $cat = "fantasy"
        $creator = "Runic Collectibles"
        $item = $baseName -replace '(?i)Runic\s*Collectibles\s*[-_ ]*', ''
    }
    # 18. Rocket Pig Games
    elseif ($name -match '(?i)Rocket\s*Pig\s*Games') {
        $cat = "fantasy"
        $creator = "Rocket Pig Games"
        $item = $baseName -replace '(?i)Rocket\s*Pig\s*Games\s*[-_ ]*', ''
    }
    # 19. StationForge / Scavenger series
    elseif ($name -match '(?i)^Scavenger\s+(.*)') {
        $cat = "sci fi"
        $creator = "StationForge"
        $release = "Scavengers"
        $item = $Matches[1]
    }
    # 20. Archvillain Games - Voracious Sands
    elseif ($name -match '(?i)Voracious\s*Sands') {
        $cat = "fantasy"
        $creator = "Archvillain Games"
        $release = "Voracious Sands (2023-09)"
        $item = $baseName
    }
    # 21. Terrain & Bases
    elseif ($name -match '(?i)ruined[-_ ]factory.*bases|wargame[-_ ]bases') {
        $cat = "bases"
        $creator = "Bases & Toppers"
        $item = $baseName
    }
    elseif ($name -match '(?i)terrain|ruins|landing\s*pad\s*terrain|bridge\s*terrain') {
        $cat = "terrain"
        $creator = "Terrain Scenery"
        $item = $baseName
    }
    elseif ($name -match '(?i)^Round(_lip)?_(\d+mm)_(.+)') {
        $cat = "bases"
        $creator = "Standard Bases"
        $release = $Matches[2]
        $item = $Matches[3]
    }
    # 22. Historical / Tanks
    elseif ($name -match '(?i)Russian_Tank|T90|SAS|T-34|Tiger|Sherman|Rheinmetall') {
        $cat = "WWII"
        $creator = "Military & Armor"
        $item = $baseName
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
Write-Host "Matched with identified creators: $matchedCount of $($results.Count)"
