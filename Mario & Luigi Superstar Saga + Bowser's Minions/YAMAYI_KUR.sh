#!/usr/bin/env bash
set -e
BASE="$(cd "$(dirname "$0")" && pwd)"
PATCH="$BASE/Yama/romfs"
TITLEID="00040000001B9000"

echo "MLSS Türkçe Yama Kurulumu"
echo "1 - Citra / Lime3DS / Azahar kullanıcı klasörüne kur"
echo "2 - Çıkarılmış RomFS klasörüne kur"
printf "Seçim: "
read -r choice
case "$choice" in
  1)
    printf "Emülatör kullanıcı klasörü: "
    read -r target
    dest="$target/load/mods/$TITLEID/romfs"
    ;;
  2)
    printf "RomFS kök klasörü: "
    read -r target
    dest="$target"
    ;;
  *)
    echo "Geçersiz seçim."
    exit 1
    ;;
esac
[ -d "$target" ] || { echo "Belirtilen klasör bulunamadı."; exit 2; }
[ -f "$PATCH/Msg/EU_en/Area.msbt" ] || { echo "Mesaj yama dosyaları bulunamadı."; exit 3; }
[ -f "$PATCH/Obj/EU/BUI.dat" ] || { echo "Grafik UI yama dosyaları bulunamadı."; exit 3; }
mkdir -p "$dest"
cp -a "$PATCH"/. "$dest"/
echo "Kurulum tamamlandı: $dest"
echo "Mesaj/font: $dest/Msg/EU_en"
echo "Grafik UI: $dest/Obj/EU"
