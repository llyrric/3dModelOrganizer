# PowerShell Classifier Script for 3D Library Files (Batch 5)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization_batch5.csv"
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

    # 1. Titan Forge
    if ($name -match '(?i)Titan\s*Forge') {
        $cat = "fantasy"
        $creator = "Titan Forge"
        if ($name -match '(?i)Arabian\s*Nights') { $release = "Arabian Nights" }
        elseif ($name -match '(?i)Dragon\s*Empire\s*3') { $release = "Dragon Empire 3" }
        elseif ($name -match '(?i)Midnight\s*Goblins') { $release = "Midnight Goblins (2022-06)" }
        $item = $baseName -replace '(?i)Titan\s*Forge[-_ ]*', ''
    }
    # 2. Voxelhouse (A Billion Suns / Spaceships)
    elseif ($name -match '(?i)Voxelhouse') {
        $cat = "spaceships"
        $creator = "Voxelhouse"
        $release = "A Billion Suns"
        $item = $baseName -replace '(?i)Voxelhouse\s*[-_ ]*|\(A\s*Billion\s*Suns\)', ''
    }
    # 3. War Scenery (Kickstarters / Grimdark Terrain)
    elseif ($name -match '(?i)War\s*Scenery') {
        $cat = "terrain"
        $creator = "War Scenery"
        $item = $baseName -replace '(?i)War\s*Scenery\s*[-_ ]*', ''
    }
    # 4. Vouivre Hive / Xenarid (StationForge / Hive Aliens)
    elseif ($name -match '(?i)^Vouivre_') {
        $cat = "sci fi"
        $creator = "StationForge"
        $release = "Vouivre"
        $item = $baseName -replace '(?i)^Vouivre_', ''
    }
    elseif ($name -match '(?i)^Xenarid\s+(.*)') {
        $cat = "sci fi"
        $creator = "StationForge"
        $release = "Xenarid"
        $item = $Matches[1]
    }
    # 5. DM Stash
    elseif ($name -match '(?i)DM\s*Stash') {
        $cat = "fantasy"
        $creator = "DM Stash"
        if ($name -match '(?i)(Jan\s*2023|Hexhunters\s*of\s*Brightstone)') { $release = "2023-01 Hexhunters of Brightstone" }
        $item = $baseName -replace '(?i)SUPPORTED\s*DM\s*Stash\s*[-_ ]*', ''
    }
    # 6. 3DArtDigital (Survivors of Serath)
    elseif ($name -match '(?i)3dartdigital|Survivors\s*of\s*Serath') {
        $cat = "fantasy"
        $creator = "3DArtDigital"
        $release = "Survivors of Serath"
        $item = $baseName
    }
    # 7. 2nd Dynasty (Sci-Fi Starships)
    elseif ($name -match '(?i)2nd\s*Dynasty|Starship\s*KS\s*by\s*2nd\s*Dynasty|TR02M01') {
        $cat = "spaceships"
        $creator = "2nd Dynasty"
        $item = $baseName
    }
    # 8. The Printing Goes Ever On (TPGEO)
    elseif ($name -match '(?i)TPGEO') {
        $cat = "fantasy"
        $creator = "The Printing Goes Ever On"
        $item = $baseName
    }
    # 9. Warp Miniatures
    elseif ($name -match '(?i)Warp\s*Miniatures') {
        $cat = "fantasy"
        $creator = "Warp Miniatures"
        $item = $baseName -replace '(?i)Warp\s*Miniatures\s*[-_ ]*', ''
    }
    # 10. Galaad Miniatures (Remaining packs)
    elseif ($name -match '(?i)Galaad\s*Miniatures') {
        $cat = "fantasy"
        $creator = "Galaad Miniatures"
        $item = $baseName
    }
    # 11. USMC / WWII / Modern Military
    elseif ($name -match '(?i)USMC|USA\s*MARINES|T-60-light-tank|T-90|su-76') {
        $cat = "WWII"
        $creator = "Military & Armor"
        $item = $baseName
    }
    # 12. Star Wars Proxies (Syndicate Pyke / Seb / Swamp Speeder)
    elseif ($name -match '(?i)Syndicate\s*Pyke|Swamp\s*Speeder|Star\s*Wars|Rebels\s*Time') {
        $cat = "sci fi"
        $creator = "Star Wars Galaxy"
        $item = $baseName
    }
    # 13. Warhammer 40k Proxies (Imperial Fists, Grey Knight, Votan, Voidscarred)
    elseif ($name -match '(?i)Imperial_Fists|grey\s*knight|Votan|Voidscarred|40000|Tau_Bases') {
        $cat = "sci fi"
        $creator = "Warhammer 40k Proxies"
        $item = $baseName
    }
    # 14. Dinosaurs & Trex
    elseif ($name -match '(?i)Trex|Tree\s*Rex') {
        $cat = "fantasy"
        $creator = "Dinosaurs & Monsters"
        $item = $baseName
    }
    # 15. Terrain & Kickstarter Sets (Time Warp, Trebuchet, Wastelands)
    elseif ($name -match '(?i)Time\s*Warp|Wastelands\+Core|Trebuchet|transmission-towers') {
        $cat = "terrain"
        $creator = "Terrain Scenery"
        $item = $baseName
    }
    # 16. Dragon Trappers Lodge (Leftover resize render tags)
    elseif ($name -match '(?i)trapper-tier|resize-trapper') {
        $cat = "fantasy"
        $creator = "Dragon Trappers Lodge"
        $item = $baseName
    }
    # 17. Necron / Robot Legion renders (rl-*)
    elseif ($name -match '(?i)^rl-') {
        $cat = "sci fi"
        $creator = "Robot Legions"
        $item = $baseName
    }
    # 18. Generic Wings / Bitz / Bases
    elseif ($name -match '(?i)^wing\d+\.stl|^Right_wingbase\.stl') {
        $cat = "bases"
        $creator = "Bitz & Accessories"
        $item = $baseName
    }
    # 19. Zombies & Undead
    elseif ($name -match '(?i)Zombie|Zombis') {
        $cat = "fantasy"
        $creator = "Undead & Zombies"
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
Write-Host "Matched with identified creators in Batch 5: $matchedCount of $($results.Count)"
