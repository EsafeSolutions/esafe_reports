param([string]$Keystore = '', [string]$Alias = 'androiddebugkey')
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$toolsRoot = Join-Path $projectRoot '.qa\android-tools'
$javaRoot = (Get-ChildItem -LiteralPath (Join-Path $toolsRoot 'jdk') -Directory | Select-Object -First 1).FullName
$sdk = (Get-ChildItem -LiteralPath (Join-Path $toolsRoot 'platform') -Directory | Select-Object -First 1).FullName
$buildTools = (Get-ChildItem -LiteralPath (Join-Path $toolsRoot 'build-tools') -Directory | Select-Object -First 1).FullName
$source = Join-Path $projectRoot 'native\android\app\src\main'
$build = Join-Path $projectRoot '.qa\android-build'
$output = Join-Path $projectRoot 'downloads'
foreach ($dir in @($build, "$build\generated", "$build\classes", "$build\dex", $output)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

function Run($Executable, $Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Build command failed: $Executable" }
}
$androidJar = Join-Path $sdk 'android.jar'
Run "$buildTools\aapt2.exe" @('compile', '--dir', "$source\res", '-o', "$build\resources.zip")
Run "$buildTools\aapt2.exe" @('link', '-I', $androidJar, '--manifest', "$source\AndroidManifest.xml", '--java', "$build\generated", '-o', "$build\base.apk", "$build\resources.zip")
$javaFiles = @((Get-ChildItem -LiteralPath "$source\java" -Recurse -Filter '*.java').FullName) + @((Get-ChildItem -LiteralPath "$build\generated" -Recurse -Filter '*.java').FullName)
Run "$javaRoot\bin\javac.exe" (@('-encoding', 'UTF-8', '--release', '8', '-classpath', $androidJar, '-d', "$build\classes") + $javaFiles)
Run "$javaRoot\bin\jar.exe" @('cf', "$build\classes.jar", '-C', "$build\classes", '.')
Run "$javaRoot\bin\java.exe" @('-cp', "$buildTools\lib\d8.jar", 'com.android.tools.r8.D8', '--min-api', '24', '--lib', $androidJar, '--output', "$build\dex", "$build\classes.jar")
Run "$javaRoot\bin\jar.exe" @('uf', "$build\base.apk", '-C', "$build\dex", 'classes.dex')
Run "$buildTools\zipalign.exe" @('-f', '-p', '4', "$build\base.apk", "$build\aligned.apk")

$development = -not $Keystore
if ($development) {
    $Keystore = Join-Path $projectRoot '.qa\android-signing\development.jks'
    New-Item -ItemType Directory -Path (Split-Path $Keystore) -Force | Out-Null
    if (-not (Test-Path -LiteralPath $Keystore)) {
        Run "$javaRoot\bin\keytool.exe" @('-genkeypair', '-keystore', $Keystore, '-storepass', 'android', '-keypass', 'android', '-alias', $Alias, '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000', '-dname', 'CN=ESAFE Development, O=ESAFE, C=LK')
    }
    $env:ESAFE_APK_STORE_PASS = 'android'
    $env:ESAFE_APK_KEY_PASS = 'android'
} elseif (-not $env:ESAFE_APK_STORE_PASS -or -not $env:ESAFE_APK_KEY_PASS) { throw 'Set ESAFE_APK_STORE_PASS and ESAFE_APK_KEY_PASS locally for release signing.' }
$name = if ($development) { 'Esafe-BLABS-Android-development.apk' } else { 'Esafe-BLABS-Android.apk' }
$apk = Join-Path $output $name
try {
    Run "$javaRoot\bin\java.exe" @('-jar', "$buildTools\lib\apksigner.jar", 'sign', '--v4-signing-enabled', 'false', '--ks', $Keystore, '--ks-key-alias', $Alias, '--ks-pass', 'env:ESAFE_APK_STORE_PASS', '--key-pass', 'env:ESAFE_APK_KEY_PASS', '--out', $apk, "$build\aligned.apk")
} finally {
    if ($development) { Remove-Item Env:ESAFE_APK_STORE_PASS,Env:ESAFE_APK_KEY_PASS }
}
Run "$javaRoot\bin\java.exe" @('-jar', "$buildTools\lib\apksigner.jar", 'verify', '--verbose', $apk)
Run "$buildTools\aapt.exe" @('dump', 'badging', $apk)
$publicDownloads = Join-Path $projectRoot 'lumen_reports\public\downloads'
if (Test-Path -LiteralPath (Join-Path $projectRoot 'lumen_reports\public')) {
    New-Item -ItemType Directory -Path $publicDownloads -Force | Out-Null
    Copy-Item -LiteralPath $apk -Destination (Join-Path $publicDownloads $name) -Force
}
Write-Output "Built $apk"
Get-FileHash -LiteralPath $apk -Algorithm SHA256 | Format-List
