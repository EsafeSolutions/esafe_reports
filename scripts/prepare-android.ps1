$ErrorActionPreference = 'Stop'
$toolsRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\.qa\android-tools'))
New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
$ProgressPreference = 'SilentlyContinue'

function Get-Archive($Url, $Name, $Destination, $Sha256 = '') {
    $archivePath = Join-Path $toolsRoot $Name
    if (-not (Test-Path -LiteralPath $archivePath)) {
        Write-Output "Downloading $Name"
        Invoke-WebRequest -Uri $Url -OutFile $archivePath -TimeoutSec 600
    }
    if ($Sha256 -and (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLower() -ne $Sha256.ToLower()) {
        throw "Checksum mismatch: $Name"
    }
    if (-not (Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
        Expand-Archive -LiteralPath $archivePath -DestinationPath $Destination -Force
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $toolsRoot 'jdk'))) {
    $release = Invoke-RestMethod -Uri 'https://api.adoptium.net/v3/assets/latest/17/hotspot?architecture=x64&image_type=jdk&os=windows&vendor=eclipse'
    $package = $release[0].binary.package
    Get-Archive $package.link 'jdk17.zip' (Join-Path $toolsRoot 'jdk') $package.checksum
}

[xml]$repository = (Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/repository2-1.xml' -TimeoutSec 60).Content
foreach ($spec in @(@{Id='platforms;android-36'; Dir='platform'}, @{Id='build-tools;36.0.0'; Dir='build-tools'})) {
    $target = Join-Path $toolsRoot $spec.Dir
    if (Test-Path -LiteralPath $target) { continue }
    $entry = $repository.SelectNodes('//*[local-name()="remotePackage"]') | Where-Object { $_.path -eq $spec.Id } | Select-Object -First 1
    $archive = $entry.archives.archive | Where-Object { -not $_.'host-os' -or $_.'host-os' -eq 'windows' } | Select-Object -First 1
    if (-not $archive.complete.url) { throw "Android package unavailable: $($spec.Id)" }
    Get-Archive ('https://dl.google.com/android/repository/' + $archive.complete.url) ($spec.Dir + '.zip') $target
}
Write-Output "Android toolchain ready in $toolsRoot"
