# PowerShell Classifier Script for 3D Library Files (Batch 6)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization_batch6.csv"
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

    # 1. Highlands Miniatures (Gallia Knights, etc.)
    if ($name -match '(?i)highlands\s*miniatures|KNIGHTS\s*OF\s*GALLIA') {
        $cat = "fantasy"
        $creator = "Highlands Miniatures"
        $item = $baseName
    }
    # 2. TytanTroll Miniatures (TTM_*, TT 2019)
    elseif ($name -match '(?i)^TTM_|TT\s*2019\s*Patreon') {
        $cat = "fantasy"
        $creator = "TytanTroll Miniatures"
        $item = $baseName
    }
    # 3. Vae Victis Miniatures (VVM_*)
    elseif ($name -match '(?i)^VVM_') {
        $cat = "fantasy"
        $creator = "Vae Victis Miniatures"
        $item = $baseName
    }
    # 4. OnePageRules (Saurian / Reptilian / Swamp Goblins / Grimdark Future)
    elseif ($name -match '(?i)Reptilian_|SWAMP\s*GOBLIN|SWAMP\s*FROGS|Saurus\s*Rovers') {
        $cat = "fantasy"
        $creator = "OnePageRules"
        $release = "Saurian Ancients"
        $item = $baseName
    }
    elseif ($name -match '(?i)Grimdark\s*Future') {
        $cat = "sci fi"
        $creator = "OnePageRules"
        $release = "Grimdark Future"
        $item = $baseName
    }
    # 5. Star Wars Galaxy (Trono Palpatine, Luke Tauntaun, Trono Snoke)
    elseif ($name -match '(?i)Palpatine|Snoke|luke\+tauntaun') {
        $cat = "sci fi"
        $creator = "Star Wars Galaxy"
        $item = $baseName
    }
    # 6. ImperitumArt
    elseif ($name -match '(?i)ImperitumArt') {
        $cat = "sci fi"
        $creator = "ImperitumArt"
        $item = $baseName
    }
    # 7. Trident Studios
    elseif ($name -match '(?i)Trident\s*Studios') {
        $cat = "spaceships"
        $creator = "Trident Studios"
        $item = $baseName
    }
    # 8. Gambody / Game of Thrones (Viserion Ice Dragon)
    elseif ($name -match '(?i)Viserion|GAMBODY') {
        $cat = "fantasy"
        $creator = "Gambody"
        $item = $baseName
    }
    # 9. Titans of Adventures
    elseif ($name -match '(?i)TITANS\s*OF\s*ADVENTURES') {
        $cat = "fantasy"
        $creator = "Titans of Adventures"
        $item = $baseName
    }
    # 10. Sentinels of the Eastern Peaks
    elseif ($name -match '(?i)Sentinels\s*of\s*the\s*Eastern\s*Peaks') {
        $cat = "fantasy"
        $creator = "Sentinels of the Eastern Peaks"
        $item = $baseName
    }
    # 11. Wood Elves / SE Warriors / Elves
    elseif ($name -match '(?i)^SE\s+Warrior|^SE\s+Lyriel|Wood\s*Elves\s*Heroes|Watchers\s*of\s*Glade') {
        $cat = "fantasy"
        $creator = "Wood Elves Collection"
        $item = $baseName
    }
    # 12. Guards & Soldiers (North Quarter, Hired Guard, Queens Guard)
    elseif ($name -match '(?i)^Set\s+[123]\s*-\s*.*Guard') {
        $cat = "fantasy"
        $creator = "City Guard Sets"
        $item = $baseName
    }
    # 13. WWII Armor & Vehicles (t34, Tankadillo, Tanktraps, SP.MV)
    elseif ($name -match '(?i)t34_85|Tanktraps|SP\.MV\.|Tankadillo|VE\s*Day') {
        $cat = "WWII"
        $creator = "Military & Armor"
        $item = $baseName
    }
    # 14. Space Marine / Warhammer 40k Proxies
    elseif ($name -match '(?i)Space\s*Marine\s*Grav|Space\s*Knight\s*Recurs|taintedbolter|taldeer') {
        $cat = "sci fi"
        $creator = "Warhammer 40k Proxies"
        $item = $baseName
    }
    # 15. Terrain & Cyberpunk Scenery
    elseif ($name -match '(?i)tycho-starport|SilentCoinTaproom|Arcane\s*Dragon\s*Tavern|warp_gate') {
        $cat = "terrain"
        $creator = "Terrain Scenery"
        $item = $baseName
    }
    # 16. Utility / Calibration Models
    elseif ($name -match '(?i)Cones\s*of\s*Calibration|Showcase\s*Commander\s*Deck|texture_rollers') {
        $cat = "other"
        $creator = "Printing Utilities & Tools"
        $item = $baseName
    }
    # 17. Pop Culture / Novelty (Shrek, Skibidi, Simpsons, FNAF Toy Chica, Space Invader)
    elseif ($name -match '(?i)Shrek|skibidi|SIMPSONS|toy-chica|space-invader-toilet|Ziggs') {
        $cat = "other"
        $creator = "Pop Culture & Novelty"
        $item = $baseName
    }
    # 18. Generic Animals & Dragons (Wyvern, Kirin, Dragon, Snowy Owl)
    elseif ($name -match '(?i)snowy-owl|Kirin|wyvern|Wild\s*Forest\s*Dragon|storm-dragon|stlanimals') {
        $cat = "fantasy"
        $creator = "Creatures & Dragons"
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
Write-Host "Matched with identified creators in Batch 6: $matchedCount of $($results.Count)"
