# Comprehensive Category Tidy-Up Script (Remaining Categories)
param(
    [string]$BasePath = "X:\3d files\3d files"
)

$categories = @("bases", "smaller scale", "modern and post apoc", "cyberpunk", "chibi", "historical", "sci fi", "fantasy", "anime", "spaceships", "dice towers")

$totalMoved = 0
$totalErrors = 0

foreach ($cat in $categories) {
    $catPath = Join-Path $BasePath $cat
    if (-not (Test-Path -LiteralPath $catPath)) { continue }

    $files = Get-ChildItem -Path $catPath -File
    if ($files.Count -eq 0) { continue }

    Write-Host "Organizing category [$cat] ($($files.Count) loose files)..."

    foreach ($f in $files) {
        $name = $f.Name
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
        $ext = $f.Extension.ToLower()

        $creator = "General Archive"

        # Creator matching rules by category
        if ($cat -eq "bases") {
            if ($name -match '(?i)Asgard\s*Rising') { $creator = "Asgard Rising" }
            elseif ($name -match '(?i)Admiral\s*Apocalypse') { $creator = "Admiral Apocalypse" }
            elseif ($name -match '(?i)Titan\s*Forge') { $creator = "Titan Forge" }
            elseif ($name -match '(?i)Wargame\s*Base|Themeatic\s*Bases') { $creator = "Bases & Toppers" }
            else { $creator = "Bases & Toppers" }
        }
        elseif ($cat -eq "smaller scale") {
            if ($name -match '(?i)The\s*Lazy\s*Forger|Lazy\s*Forger') { $creator = "The Lazy Forger" }
            elseif ($name -match '(?i)Epic|6mm|10mm|15mm') { $creator = "Epic & Small Scale" }
            else { $creator = "Small Scale Units" }
        }
        elseif ($cat -eq "modern and post apoc") {
            if ($name -match '(?i)Vault\s*Z|Vaultz') { $creator = "VaultZ Miniatures" }
            elseif ($name -match '(?i)TurnBase') { $creator = "TurnBase Miniatures" }
            elseif ($name -match '(?i)Zombie|Walking\s*Dead') { $creator = "Zombies & Survivors" }
            else { $creator = "Modern & Post-Apoc Units" }
        }
        elseif ($cat -eq "cyberpunk") {
            if ($name -match '(?i)UNIT\s*9|UNIT9') { $creator = "UNIT9" }
            elseif ($name -match '(?i)Cyber\s*Forge') { $creator = "Cyber Forge" }
            else { $creator = "Cyberpunk Units" }
        }
        elseif ($cat -eq "chibi") {
            $creator = "Chibi Characters"
        }
        elseif ($cat -eq "historical") {
            if ($name -match '(?i)Romans') { $creator = "Romans" }
            else { $creator = "Historical Units" }
        }
        elseif ($cat -eq "sci fi") {
            if ($name -match '(?i)Skull\s*Forge') { $creator = "Skull Forge Studios" }
            elseif ($name -match '(?i)Station\s*Forge|StationForge') { $creator = "StationForge" }
            elseif ($name -match '(?i)The\s*Makers\s*Cult') { $creator = "The Makers Cult" }
            else { $creator = "Sci-Fi Units & Proxies" }
        }
        elseif ($cat -eq "fantasy") {
            if ($name -match '(?i)OnePageRules') { $creator = "OnePageRules" }
            elseif ($name -match '(?i)Titan\s*Forge') { $creator = "Titan Forge" }
            elseif ($name -match '(?i)Dragon\s*Trappers') { $creator = "Dragon Trappers Lodge" }
            else { $creator = "Fantasy Heroes & Adventurers" }
        }
        elseif ($cat -eq "anime") {
            if ($name -match '(?i)RN\s*Estudio|RNEstudios') { $creator = "RNE studios" }
            else { $creator = "Anime Characters" }
        }
        elseif ($cat -eq "spaceships") {
            if ($name -match '(?i)Voxelhouse') { $creator = "Voxelhouse" }
            elseif ($name -match '(?i)2nd\s*Dynasty') { $creator = "2nd Dynasty" }
            else { $creator = "Fleet & Spaceships" }
        }
        elseif ($cat -eq "dice towers") {
            $creator = "Dice Towers & Holders"
        }

        # Clean item name
        $item = ($baseName -replace '(?i)\.(zip|rar|7z|stl|jpg|png|obj)(\.00\d+)?$', '' -replace '@[a-zA-Z0-9_]+', '' -replace '\?@[a-zA-Z0-9_]+\?', '' -replace '\(\d+\)', '' -replace '_', ' ' -replace '\s+', ' ').Trim(' -_')
        if (-not $item) { $item = $baseName }

        $destDir = Join-Path $catPath $creator
        $destFile = Join-Path $destDir "$creator - $item$ext"

        try {
            if (-not (Test-Path -LiteralPath $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Move-Item -LiteralPath $f.FullName -Destination $destFile -Force
            $totalMoved++
        } catch {
            Write-Error "Error moving $($f.FullName): $_"
            $totalErrors++
        }
    }
}

Write-Host "Category sweep complete! Total files moved: $totalMoved, Errors: $totalErrors"
