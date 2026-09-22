$ErrorActionPreference = "Stop"
Write-Host "Street Fighter IV 3D Edition - Türkçe Yama Kaldırma" -ForegroundColor Cyan
$InputPath = (Read-Host "_eng klasörünü içeren ana klasör veya doğrudan _eng yolu").Trim().Trim('"')
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
$Backup = Join-Path $Root "_eng_SF4_TR_YEDEK"
if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    throw "Hedef _eng klasörü bulunamadı: $Target"
}
if (-not (Test-Path -LiteralPath $Backup -PathType Container)) {
    throw "Kurucu yedeği bulunamadı: $Backup"
}
Write-Host "Özgün dosyalar geri yükleniyor..." -ForegroundColor Yellow
Copy-Item -Path (Join-Path $Backup '*') -Destination $Target -Recurse -Force
Write-Host "Yama kaldırıldı ve yedek geri yüklendi." -ForegroundColor Green
Write-Host "Yedek klasörü güvenlik için silinmedi: $Backup"
Read-Host "Kapatmak için Enter"
