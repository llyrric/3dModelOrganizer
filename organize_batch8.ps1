# PowerShell Classifier Script for 3D Library Files (Batch 8 - 100% Complete Resolution)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization_batch8.csv"
)

$files = Get-ChildItem -Path $SourcePath -File
Write-Host "Analyzing $($files.Count) remaining root files..."

$results = @()

foreach ($f in $files) {
    $name = $f.Name
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext = $f.Extension.ToLower()

    $cat = "other"
    $creator = "General Archive"
    $release = "General"
    $item = $baseName

    # 1. Stormlight Archive (Sanitize creator folder to Brotherwise Games - Stormlight)
    if ($name -match '(?i)STORMLIGHT') {
        $cat = "fantasy"
        $creator = "Brotherwise Games - Stormlight"
        $release = "Stormlight Archive"
        $item = $baseName -replace '(?i)STORMLIGHT[-_ ]*', ''
    }
    # 2. Galaad Miniatures
    elseif ($name -match '(?i)Galaad') {
        $cat = "fantasy"
        $creator = "Galaad Miniatures"
        $release = "September Release"
        $item = $baseName
    }
    # 3. Highlands Miniatures (Skeleton full unit anniversary)
    elseif ($name -match '(?i)highlands') {
        $cat = "fantasy"
        $creator = "Highlands Miniatures"
        $item = $baseName
    }
    # 4. Kukulkan / Mayan Mythos (SMITE / Seduced Kukulkan)
    elseif ($name -match '(?i)Kukulcan|Kukulkan') {
        $cat = "fantasy"
        $creator = "Mythological & Gods"
        $item = $baseName
    }
    # 5. Japanese / Asian Fantasy (Ryujin Norinaga, Tales of Ryuboken, Desert Daimyo)
    elseif ($name -match '(?i)Ryujin|Ryuboken|desert\s*daimyo') {
        $cat = "fantasy"
        $creator = "Asian & Samurai Fantasy"
        $item = $baseName
    }
    # 6. Giants, Trolls & Big Monsters
    elseif ($name -match '(?i)Tarnaruk|Ursa|Ursalioth|Infernal\s*Magma|Wild\s*Creatures|Tangleheart') {
        $cat = "fantasy"
        $creator = "Giants & Monsters"
        $item = $baseName
    }
    # 7. Undead, Skulls, Demons & Elements
    elseif ($name -match '(?i)SKELETON|Daemonic|Aeterni|Bonelord|Vengeful_spirits|UNDEAD|SKULL_HUNTER|RoarOfTheEverdeath|Sepulchral|QueenofChaos|Screaming-Balefire|Summoned\s*Elementals|Host\s*of\s*the\s*Demonicus') {
        $cat = "fantasy"
        $creator = "Undead & Chaos"
        $item = $baseName
    }
    # 8. Fantasy Warriors & Adventurers
    elseif ($name -match '(?i)Rukh|GREEN\s*KNIGHT|Throne\s*Guard|Thugs|Warriors|Wai\+Toa|wind-knights|Sverting|Stormparty|The\s*preserver|The\s*Sheriff|Black\s*Watch|mystical\s*count|benjo|Stiletto|Vinny|Super\s*Warrior|rafinus|Rebeldes\s*Montables|Tortle|Unegen') {
        $cat = "fantasy"
        $creator = "Fantasy Heroes & Adventurers"
        $item = $baseName
    }
    # 9. Lizardmen / Seraphon (Seraphone, Skink, Sand-Worm)
    elseif ($name -match '(?i)Seraphone|SKINK|Sand-Worm') {
        $cat = "fantasy"
        $creator = "Saurian & Reptilian"
        $item = $baseName
    }
    # 10. Sci-Fi Units, Vehicles & Bitz
    elseif ($name -match '(?i)Rhino|Replicator|Requiem|Sniper|Spawn-Pods|Lord\s*of\s*Battle|starwatchers|Zanat|pleasure\s*knight|STC|Radio\s*Sets|RAT\s*SLINGER|Sky\s*Ravagers|Solar\s*Eclipsed|Ancient\s*Hunting|thriving\s*planet|tourelle|HERETECH|Sentinel') {
        $cat = "sci fi"
        $creator = "Sci-Fi Units & Proxies"
        $item = $baseName
    }
    # 11. Bases, Ropes, Bitz & Templates
    elseif ($name -match '(?i)sfs\s*base|RopeSupport|STL_WHEEL|Template-Ice|Torch|Smoking_Dragon') {
        $cat = "bases"
        $creator = "Bitz & Accessories"
        $item = $baseName
    }
    # 12. Previews, Social Images & Servants Quarters
    elseif ($name -match '(?i)WhatsApp|s-l1600|s-l500|RDT_|rendeall|Sans\s*titre|Scorpion\.png|Stacks\.png|Stagetop\.png|Superior|Titan\s*[13]|ToadLord|TreasureIsland|University\s*of\s*Ardris|Under\s*Dark|wfbfe2sn|sekolin|Queen\s*of\s*the\s*Glacial|ServantsQuarter') {
        $cat = "other"
        $creator = "Render Previews & Screenshots"
        $item = $baseName
    }
    # 13. Remaining Kickstarter/Monthly Bundles
    elseif ($name -match '(?i)SK_December|Septembre\s*2019|September23-adv|Rought\s*and\s*Tumble|ruleta|Rules|Umbralshade|scarecrow|Rokk\s*Band') {
        $cat = "other"
        $creator = "Community & Monthly Bundles"
        $item = $baseName
    }
    # 14. Unicode / Russian unnamed character sculpts
    elseif ($name -match '\.obj$') {
        $cat = "other"
        $creator = "3D Character Models"
        $item = "Character Sculpt " + [System.Guid]::NewGuid().ToString().Substring(0, 4)
    }

    # Clean up item text
    $item = ($item -replace '(?i)\.(zip|rar|7z|stl|jpg|png|obj)(\.00\d+)?$', '' -replace '@[a-zA-Z0-9_]+', '' -replace '\?@[a-zA-Z0-9_]+\?', '' -replace '\(\d+\)', '' -replace '_', ' ' -replace '\s+', ' ').Trim(' -_')
    if (-not $item) { $item = $baseName }

    # Proposed file and folder paths
    $newFileName = ""
    if ($creator -ne "General Archive" -and $release -ne "General") {
        $newFileName = "$creator - $release - $item$ext"
    } elseif ($creator -ne "General Archive") {
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

$matchedCount = ($results | Where-Object { $_.Creator -ne "General Archive" }).Count
Write-Host "Fully Classified in Batch 8: $matchedCount of $($results.Count)"
