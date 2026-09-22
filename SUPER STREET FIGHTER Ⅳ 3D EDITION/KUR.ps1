$ErrorActionPreference = "Stop"
$Patch = Join-Path $PSScriptRoot "YAMA\_eng"

Write-Host "Street Fighter IV 3D Edition - Türkçe Yama Kurulumu" -ForegroundColor Cyan
Write-Host "Yol olarak _eng klasörünü içeren ana klasörü veya doğrudan _eng klasörünü girebilirsiniz."
$InputPath = (Read-Host "Oyun dil klasörü yolu").Trim().Trim('"')
if (-not (Test-Path -LiteralPath $InputPath -PathType Container)) {
    throw "Girilen klasör bulunamadı: $InputPath"
}

$Resolved = (Resolve-Path -LiteralPath $InputPath).Path
if ((Split-Path -Leaf $Resolved) -ieq "_eng") {
    $Target = $Resolved
    $Root = Split-Path -Parent $Resolved
} else {
    $Root = $Resolved
    $Target = Join-Path $Root "_eng"
}

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    throw "Hedefte _eng klasörü bulunamadı: $Target"
}
if (-not (Test-Path -LiteralPath $Patch -PathType Container)) {
    throw "Paket içindeki YAMA\_eng klasörü bulunamadı."
}

$PatchRoot = (Resolve-Path -LiteralPath $Patch).Path.TrimEnd('\')
$PatchFiles = @(Get-ChildItem -LiteralPath $Patch -Recurse -File -Filter *.arc)
if ($PatchFiles.Count -ne 254) {
    throw "Yama dosyaları eksik veya bozuk. Beklenen 254 ARC, bulunan: $($PatchFiles.Count)"
}

$Missing = New-Object System.Collections.Generic.List[string]
foreach ($File in $PatchFiles) {
    $Rel = $File.FullName.Substring($PatchRoot.Length).TrimStart('\')
    if (-not (Test-Path -LiteralPath (Join-Path $Target $Rel) -PathType Leaf)) {
        $Missing.Add($Rel)
    }
}
if ($Missing.Count -gt 0) {
    Write-Host "Hedef _eng yapısı bu yama ile eşleşmiyor. Eksik örnekler:" -ForegroundColor Red
    $Missing | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
    throw "Toplam eksik hedef dosyası: $($Missing.Count). Kurulum iptal edildi."
}

$Backup = Join-Path $Root "_eng_SF4_TR_YEDEK"
if (-not (Test-Path -LiteralPath $Backup)) {
    Write-Host "Özgün _eng dosyaları yedekleniyor..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $Backup | Out-Null
    Copy-Item -Path (Join-Path $Target '*') -Destination $Backup -Recurse -Force
} else {
    Write-Host "Mevcut yedek korunuyor: $Backup" -ForegroundColor Yellow
}

Write-Host "Türkçe ARC dosyaları kopyalanıyor..." -ForegroundColor Yellow
Copy-Item -Path (Join-Path $Patch '*') -Destination $Target -Recurse -Force

Write-Host "Kurulum tamamlandı." -ForegroundColor Green
Write-Host "Oyunda İngilizce dil setini kullanın."
Write-Host "Yedek: $Backup"
Read-Host "Kapatmak için Enter"
