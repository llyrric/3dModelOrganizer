# PowerShell Classifier Script for 3D Library Files (Batch 4)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization_batch4.csv"
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

    # 1. Twin Goddess Miniatures
    if ($name -match '(?i)Twin[-_ ]Goddess') {
        $cat = "fantasy"
        $creator = "Twin Goddess Miniatures"
        if ($name -match '(?i)Fantasy[-_ ]Queens') { $release = "Fantasy Queens" }
        elseif ($name -match '(?i)(April\s*2023|June\s*2023|july\s*23|\d{6})') { $release = $Matches[1] }
        $item = $baseName -replace '(?i)Twin[-_ ]Goddess\s*(Miniatures)?[-_ ]*', '' -replace '(?i)Fantasy[-_ ]Queens[-_ ]*', ''
    }
    # 2. Cast n Play
    elseif ($name -match '(?i)CastnPlay|Cast[-_ ]n[-_ ]Play') {
        $cat = "fantasy"
        $creator = "Cast n Play"
        $item = $baseName -replace '(?i)CastnPlay|Cast[-_ ]n[-_ ]Play', ''
    }
    # 3. Stormlight Archive (Brandon Sanderson)
    elseif ($name -match '(?i)STORMLIGHT') {
        $cat = "fantasy"
        $creator = "Brotherwise Games / Stormlight"
        $release = "Stormlight Archive"
        $item = $baseName -replace '(?i)STORMLIGHT[-_ ]*', ''
    }
    # 4. Fleshcraft Studio
    elseif ($name -match '(?i)FleshcraftStudio') {
        $cat = "fantasy"
        $creator = "Fleshcraft Studio"
        $item = $baseName -replace '(?i)FleshcraftStudio', ''
    }
    # 5. The Darkwoods (TDW)
    elseif ($name -match '(?i)^TDW\s*[-_ ]*(\d{4}[-_]?\d{2})?\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "The Darkwoods"
        if ($Matches[1]) { $release = $Matches[1] }
        $item = $Matches[2]
    }
    # 6. WildMesh
    elseif ($name -match '(?i)WildMesh\s*[-_ ]*(.*)') {
        $cat = "sci fi"
        $creator = "WildMesh"
        $item = $Matches[1]
    }
    # 7. Seb Miniatures / Stormsoldiers
    elseif ($name -match '(?i)Stormsoldiers.*\[Seb\]') {
        $cat = "sci fi"
        $creator = "Seb Miniatures"
        $item = $baseName
    }
    # 8. Modern Military / Tanks (Bolt Action, Su-122, SU-152, Tora Bora, Strv, Sukhoi)
    elseif ($name -match '(?i)Su-122|SU-152|su-76|sukhoi|strv|Tora[-_ ]Bora|Delta[-_ ]Force|Hawkei|Universal[-_ ]Guard|TCB_GA') {
        $cat = "WWII"
        $creator = "Military & Armor"
        $item = $baseName
    }
    # 9. Ships, Naval & Age of Sail
    elseif ($name -match '(?i)Sail\d+|Ship[-_ ]Base|Ships\s*and\s*Boats|shipyard|Sloop.*Gunship') {
        $cat = "fantasy naval game and airships"
        $creator = "Naval & Airships"
        $item = $baseName
    }
    # 10. Tavern & Stores modular sets (Modular Towns / Interiors)
    elseif ($name -match '(?i)^Stores\s+|^Tavern\s+|^Temple\s+|^Stormcrow\s+Mansion') {
        $cat = "terrain"
        $creator = "Modular Buildings & Interiors"
        $item = $baseName
    }
    # 11. Skulls & Bones / Thematic bases
    elseif ($name -match '(?i)Thematic[-_ ]Bases|skulls[-_ ]bones[-_ ]core|Tau_Bases') {
        $cat = "bases"
        $creator = "Bases & Toppers"
        $item = $baseName
    }
    # 12. Werewolves & Bears (Fantasy beasts)
    elseif ($name -match '(?i)Werewolf\d+|WereBear|bear[-_ ]warriors|Wolfriders|wolfs\s*pack') {
        $cat = "fantasy"
        $creator = "Beasts & Monsters"
        $item = $baseName
    }
    # 13. ZBrush Brushes / 3D Sculpting Assets (.ZBP)
    elseif ($ext -eq ".zbp" -or $name -match '(?i)_IMM\.ZBP|_brush\.ZBP|Layered[-_ ]Scales') {
        $cat = "other"
        $creator = "ZBrush Sculpting Brushes"
        $item = $baseName
    }
    # 14. Star Wars (Tulak Hord, Sandi Gold & Jawas)
    elseif ($name -match '(?i)Tulak\s*Hord') {
        $cat = "sci fi"
        $creator = "Star Wars Galaxy"
        $item = $baseName
    }
    # 15. The Proxigenator / Fabrikatum
    elseif ($name -match '(?i)Proxigenator') {
        $cat = "sci fi"
        $creator = "The Proxigenator"
        $item = $baseName
    }
    # 16. TurnBase Miniatures
    elseif ($name -match '(?i)TurnBase[-_ ]Miniatures') {
        $cat = "modern and post apoc"
        $creator = "TurnBase Miniatures"
        $item = $baseName
    }

    # Clean up item text
    $item = ($item -replace '(?i)\.(zip|rar|7z|stl|jpg|png|obj)(\.00\d+)?$', '' -replace '@[a-zA-Z0-9_]+', '' -replace '\?@[a-zA-Z0-9_]+\?', '' -replace '\(\d+\)', '' -replace '_', ' ' -replace '\s+', ' ').Trim(' -_')
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
Write-Host "Matched with identified creators in Batch 4: $matchedCount of $($results.Count)"
