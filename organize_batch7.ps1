# PowerShell Classifier Script for 3D Library Files (Batch 7 - Comprehensive Catch-All)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization_batch7.csv"
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

    # 1. Galaad Miniatures
    if ($name -match '(?i)Galaad\s*Miniatures') {
        $cat = "fantasy"
        $creator = "Galaad Miniatures"
        if ($name -match '(?i)(September_Release|September)') { $release = "September Release" }
        $item = $baseName
    }
    # 2. Stormlight Archive (remaining)
    elseif ($name -match '(?i)STORMLIGHT') {
        $cat = "fantasy"
        $creator = "Brotherwise Games / Stormlight"
        $release = "Stormlight Archive"
        $item = $baseName -replace '(?i)STORMLIGHT[-_ ]*', ''
    }
    # 3. StationForge / Scavenger (Station Forge preview / bits)
    elseif ($name -match '(?i)Station\s*Forge') {
        $cat = "sci fi"
        $creator = "StationForge"
        $item = $baseName
    }
    # 4. Highlands Miniatures / Dragon Trappers (resize image tags)
    elseif ($name -match '(?i)highlands\s*miniatures') {
        $cat = "fantasy"
        $creator = "Highlands Miniatures"
        $item = $baseName
    }
    elseif ($name -match '(?i)resize[-_ ]august2021[-_ ]feywild|resize[-_ ]trapper') {
        $cat = "fantasy"
        $creator = "Dragon Trappers Lodge"
        $item = $baseName
    }
    # 5. D&D / Bestiary Monsters (25mm / 50mm bases, scale previews, D&D monsters)
    elseif ($name -match '(?i)\[(25mm|50mm)\s*Base\]|remorhaz|Strahd|tabaxi|YuanTi|Treant|Trolls|Vampire\s*queen|Worm.*Eldritch|Woldling\s*Wretch|Young\s*Devourer|Soul\s*Eater|Varagur|Violet\s*fungus|water[-_ ]witch|wizardgirl') {
        $cat = "fantasy"
        $creator = "D&D & RPG Monsters"
        $item = $baseName
    }
    # 6. Fantasy Heroes, Paladins & Barbarians (Razbok, Shainda, Valkyrie, R - Rangers, etc.)
    elseif ($name -match '(?i)Razbok|Shainda|Valkyrie\s*Paladin|R\s*-\s*Rangers|Slave\s*Orcs|Slave\s*princess|seasonedhunter|Slingers|Stick_GobRanger|Trixli|Warrel_Sorcerer|Watatsumi|Yivekha|young\s*and\s*naive|Winged\s*Husars') {
        $cat = "fantasy"
        $creator = "Fantasy Heroes & Adventurers"
        $item = $baseName
    }
    # 7. Sci-Fi / Warhammer / Grimdark Units & Vehicles (Syndicate, Spartan, Repulsor, Tersus, Tech Thralls, etc.)
    elseif ($name -match '(?i)Syndicate\s*thugs|Spartan\s*III|Repulsor_Heavy|triggerfish|turbo-tripod|Tech_Thralls|Tersus|Technical\s*-\s*Goblin|The\s*Tyrant|THE_OMEGAS|TL_xenos|Union\s*vanguard|Space_ANTIFA|SCI-FI_') {
        $cat = "sci fi"
        $creator = "Sci-Fi Units & Proxies"
        $item = $baseName
    }
    # 8. Dice Towers, Incense Holders & Decorative
    elseif ($name -match '(?i)dice[-_ ]tower|Incense\s*Holder|Turtle_snack|Deck\s*Box') {
        $cat = "dice towers"
        $creator = "Dice Towers & Holders"
        $item = $baseName
    }
    # 9. Military, Tanks & Historical (Romans, Russia, Tank.zip, Tank Crews, Truck B, Warmachines)
    elseif ($name -match '(?i)Romans_STL|RUSSIA|Tank\s*Crews|Tank\.zip|Truck\s*B|Warmachines|WarfareStrike') {
        $cat = "historical"
        $creator = "Historical & Military"
        $item = $baseName
    }
    # 10. Terrain, Scenery & Architecture (Viking Village, Spiritdale, Sand-Worm, Skull Cave, Stone monoliths, Temple, etc.)
    elseif ($name -match '(?i)VIKING\+VILLAGE|Spiritdale|Skull\s*Cave|Stone\s*monoliths|The\s*villagers\s*house|The\s*War\s*Zone|The\s*Dark\s*City|Standing\+Stone|Saguaro\s*Cactus|Siege\s*Tower|SiegeLadder') {
        $cat = "terrain"
        $creator = "Terrain Scenery"
        $item = $baseName
    }
    # 11. Generic Preview renders / Screenshots (resize-*, screenshot-*, render*)
    elseif ($name -match '(?i)^resize-|^Screenshot|^render|^\.jpg|^\.png') {
        $cat = "other"
        $creator = "Render Previews & Screenshots"
        $item = $baseName
    }
    # 12. Starter / Welcome Packs
    elseif ($name -match '(?i)Welcome\s*Pack|STARTER\s*PACK') {
        $cat = "other"
        $creator = "Welcome & Starter Packs"
        $item = $baseName
    }
    # 13. General Stretch Goals & Kickstarter Bundles
    elseif ($name -match '(?i)Stretch\s*Goals') {
        $cat = "other"
        $creator = "Kickstarter Stretch Goals"
        $item = $baseName
    }
    # 14. Unknown/Text/Notes (recap.txt, update notes)
    elseif ($ext -eq ".txt") {
        $cat = "other"
        $creator = "Release Notes"
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
Write-Host "Matched with identified creators in Batch 7: $matchedCount of $($results.Count)"
