# PowerShell Classifier Script for 3D Library Files (Batch 3)
param(
    [string]$SourcePath = "X:\3d files\3d files",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_organization_batch3.csv"
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

    # 1. Wraith Kings Army (Fantasy / Undead)
    if ($name -match '(?i)^Wraith\s*Kings\s*Army\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "Wraith Kings Army"
        $item = $Matches[1]
    }
    # 2. Vault Z / Vaultz Miniatures (Post-Apoc / Modern)
    elseif ($name -match '(?i)Vault\s*Z|Vaultz\s*Miniatures') {
        $cat = "modern and post apoc"
        $creator = "VaultZ Miniatures"
        $item = $baseName
    }
    # 3. Vesper Project (Sci-Fi / Mechs & Vehicles)
    elseif ($name -match '(?i)^Vesper\s*Project\s*[-_ ]*(.*)') {
        $cat = "sci fi"
        $creator = "Vesper Project"
        $item = $Matches[1]
    }
    # 4. Vae Victis Miniatures
    elseif ($name -match '(?i)Vae\s*Victis\s*[-_ ]*(\d{4}[-_]?\d{2})?\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "Vae Victis Miniatures"
        if ($Matches[1]) { $release = $Matches[1] }
        $item = if ($Matches[2]) { $Matches[2] } else { $baseName }
    }
    # 5. Witchsong Miniatures
    elseif ($name -match '(?i)Witch[sS]ong\s*[-_ ]*(.*)') {
        $cat = "fantasy"
        $creator = "Witchsong Miniatures"
        $item = $Matches[1]
    }
    # 6. The Printing Goes Ever On
    elseif ($name -match '(?i)The[-_ ]Printing[-_ ]Goes[-_ ]Ever[-_ ]On') {
        $cat = "fantasy"
        $creator = "The Printing Goes Ever On"
        $item = $baseName -replace '(?i)The[-_ ]Printing[-_ ]Goes[-_ ]Ever[-_ ]On[-_ ]*', ''
    }
    # 7. Print Your Monsters
    elseif ($name -match '(?i)Print[-_ ]Your[-_ ]Monsters') {
        $cat = "fantasy"
        $creator = "Print Your Monsters"
        $item = $baseName -replace '(?i)[-_ ]*Print[-_ ]Your[-_ ]Monsters[-_ ]*', ''
    }
    # 8. Surrogate Miniatures / Void Jesters
    elseif ($name -match '(?i)Surrogate\s*Miniatures|Void\s*Jesters.*Surrogate|Rubeus_Marines.*Surrogate') {
        $cat = "sci fi"
        $creator = "Surrogate Miniatures"
        $item = $baseName
    }
    # 9. Dragon Trappers Lodge (Batch 3 variants)
    elseif ($name -match '(?i)The[-_ ]Dragon[-_ ]Trapper''?s[-_ ]Lodge') {
        $cat = "fantasy"
        $creator = "Dragon Trappers Lodge"
        if ($name -match '(?i)(21-3)') { $release = "2021-03" }
        $item = $baseName -replace '(?i)The[-_ ]Dragon[-_ ]Trapper''?s[-_ ]Lodge[-_ ]*', ''
    }
    # 10. The Makers Cult (Batch 3 variants)
    elseif ($name -match '(?i)The[-_ ]Makers[-_ ]Cult') {
        $cat = "sci fi"
        $creator = "The Makers Cult"
        $item = $baseName -replace '(?i)The[-_ ]Makers[-_ ]Cult[-_ ]*', ''
    }
    # 11. Skullforge / Skull Forge Studios (Batch 3 variants)
    elseif ($name -match '(?i)Skullforge|Skull\s*Forge') {
        $cat = "sci fi"
        $creator = "Skull Forge Studios"
        $item = $baseName -replace '(?i)Skullforge\s*Studios?|Skull\s*Forge\s*Studios?', ''
    }
    # 12. Socratis / StationForge / Sci-Fi Proxies
    elseif ($name -match '(?i)^Socratis\s+(.*)') {
        $cat = "sci fi"
        $creator = "StationForge"
        $release = "Socratis"
        $item = $Matches[1]
    }
    # 13. Tyranids / Warhammer 40k Proxies
    elseif ($name -match '(?i)VOD\s*-\s*TYRANIDS|tyranid|Skragrott|Slayer|Thunderers|soh\s+trophy|vilitch') {
        $cat = "sci fi"
        $creator = "Warhammer Proxies"
        $item = $baseName
    }
    # 14. WWII / Military Buildings & Vehicles
    elseif ($name -match '(?i)WW2[-_ ]|WWII\s*RELEASE|WoW\s*Buildings.*WW2|Valentine-28mm|Solon\s*Tank|Sheridan\s*tank') {
        $cat = "WWII"
        $creator = "WWII & Military"
        $item = $baseName
    }
    # 15. Terrain / Scenery
    elseif ($name -match '(?i)The\s*Cottage|Witchcraft\s*Night\s*scenery|Wizard\s*lab|Viking\s*Village|Small\s*Ancient\s*Stone|sewers|Standing\s*Stones?|Skyhall') {
        $cat = "terrain"
        $creator = "Terrain Scenery"
        $item = $baseName
    }
    # 16. Star Wars proxies
    elseif ($name -match '(?i)Jawas|Rebel\s*Edrio|Rebel\s*medics|Recusant|Star\s*Wars') {
        $cat = "sci fi"
        $creator = "Star Wars Galaxy"
        $item = $baseName
    }
    # 17. Resident Evil
    elseif ($name -match '(?i)Resident\s*evil|Licker') {
        $cat = "modern and post apoc"
        $creator = "Resident Evil"
        $item = $baseName
    }
    # 18. Superheroes (Marvel / DC)
    elseif ($name -match '(?i)wolverine|wonder\s*woman') {
        $cat = "superheros"
        $creator = "Marvel & DC"
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
Write-Host "Matched with identified creators in Batch 3: $matchedCount of $($results.Count)"
