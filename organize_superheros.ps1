# Superheros Category Organizer Script
param(
    [string]$CategoryPath = "X:\3d files\3d files\superheros",
    [string]$OutputCsv = "h:\webpage projects\persoanl 3d files organized\proposed_superheros_move.csv"
)

$files = Get-ChildItem -Path $CategoryPath -File
Write-Host "Analyzing $($files.Count) loose files in superheros..."

$results = @()

foreach ($f in $files) {
    $name = $f.Name
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext = $f.Extension.ToLower()

    $creator = "Marvel & DC"
    $release = "General"
    $item = $baseName

    # 1. C27 Collectibles (often named *-40mm-scale-on-*-base or ending with _@stl_zone or explicit C27)
    if ($name -match '(?i)C27|on-\d+mm-base|_@stl_zone|Mutant\s*Institution') {
        $creator = "C27"
        $item = $baseName -replace '(?i)C27[-_ ]*|[-_ ]*C27', ''
    }
    # 2. RN Estudio
    elseif ($name -match '(?i)RN\s*Estudio|RNEstudio') {
        $creator = "rne studios"
        $item = $baseName -replace '(?i)\[?RN\s*Estudio\]?[-_ ]*|RNEstudio[-_ ]*', ''
    }
    # 3. Sanix
    elseif ($name -match '(?i)Sanix') {
        $creator = "Sanix"
        $item = $baseName -replace '(?i)Sanix[-_ ]*', ''
    }
    # 4. Pixel 3D / BrunoArt / Bulkamancer (Marvel Rivals models)
    elseif ($name -match '(?i)Pixel_3D|BrunoArt|Bulkamancer|Marvel\s*Rivals') {
        $creator = "Marvel Rivals"
        $item = $baseName -replace '(?i)@?Pixel_3D_STL_?|BrunoArt3D_?|Bulkamancer\s*-\s*', ''
    }
    # 5. Trident Studios / Legion Miniatures / CGTrader
    elseif ($name -match '(?i)Trident\s*Studio|Legion\s*Miniatures|CGTrader|ActionStudios3D') {
        $creator = "Indie Studios"
        $item = $baseName
    }
    # 6. Hero Characters (Spider-Man, X-Men, Avengers, Batman, Hulk, etc.)
    elseif ($name -match '(?i)Spider|X-?Men|Wolverine|Deadpool|Captain|Iron\s*Man|Thor|Hulk|Doom|Strange|Bane|Catwoman|Aquaman|Carnage|Darkseid|Daredevil|Venom|Flash|Superman|Batman') {
        $creator = "Marvel & DC"
        $item = $baseName
    }

    # Clean up item text
    $item = ($item -replace '(?i)\.(zip|rar|7z|stl|jpg|png|obj)(\.00\d+)?$', '' -replace '@[a-zA-Z0-9_]+', '' -replace '\?@[a-zA-Z0-9_]+\?', '' -replace '\(\d+\)', '' -replace '_', ' ' -replace '\s+', ' ').Trim(' -_')
    if (-not $item) { $item = $baseName }

    # Proposed destination folder
    $destFolder = Join-Path $CategoryPath $creator

    # Clean new file name
    $newFileName = "$creator - $item$ext"

    $results += [PSCustomObject]@{
        OriginalFile = $name
        Extension    = $ext
        Category     = "superheros"
        Creator      = $creator
        CleanItem    = $item
        NewFileName  = $newFileName
        DestFolder   = $destFolder
    }
}

$results | Export-Csv -Path $OutputCsv -NoTypeInformation
Write-Host "Exported proposed superheros moves to $OutputCsv"
$results | Group-Object Creator | Select-Object Count, Name | Sort-Object Count -Descending | Format-Table -AutoSize
