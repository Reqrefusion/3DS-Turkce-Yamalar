# -*- coding: utf-8 -*-
"""Bravely Default western UI -> Turkish translations.
The user's existing Common_en translation dictionary is the terminology authority.
Placeholders/test strings are intentionally omitted.
"""
from pathlib import Path
import json

try:
    _COMMON_TR = json.loads(Path(__file__).with_name("common_tr_dict.json").read_text(encoding="utf-8"))
except Exception:
    _COMMON_TR = {}


UI_TRANSLATIONS = {
'Lv':'Sv',
'Travel to':'Şuraya git',
'Specialty':'Uzmanlık','Job Command':'Meslek Komutu','Stat Affinities':'Stat Yatkınlığı',
'HP':'HP','MP':'BP','BP':'CP','JP':'MP','AGI':'ÇEV','STR':'GÜÇ','INT':'ZEK','DEX':'BEC','VIT':'DAY','MND':'İRA',
'Arms Aptitude':'Silah Yetkinliği','Swords':'Kılıçlar','Axes':'Baltalar','Spears':'Mızraklar','Rods':'Değnekler','Staves':'Asalar','Daggers':'Hançerler','Bows':'Yaylar','Katana':'Katana','Knuckles':'Muştalar',
'Armor Aptitude':'Zırh Yetkinliği','Shields':'Kalkanlar','Helms':'Miğferler','Armor':'Zırh',
'Tutorial Quests':'Eğitim Görevleri','Reward':'Ödül','Auto-playing':'Otomatik oynatma','Auto':'Otomatik','Skip':'Atla','Skip this event?':'Bu olayı atla mı?','Yes':'Evet','No':'Hayır',
'Tactics':'Taktikler','Friends':'Arkadaşlar','Abilink':'Yetenek Bağı','Status':'Durum','Sort':'Sırala','Config':'Ayarlar',
'Item List':'Eşya Listesi','Party Info':'Grup Bilgisi','Stats':'Statlar','P.ATK':'F.SAL','P.DEF':'F.SAV','M.ATK':'B.SAL','M.DEF':'B.SAV','Aim':'İsabet','Evade':'Kaçınma','Critical':'Kritik','Element':'Element','Immunities':'Bağışıklıklar','Resistances':'Dirençler',
'Job':'Meslek','Command':'Komut','Data List':'Veri Listesi','Update Stopped':'Güncelleme Durdu','Updated':'Güncellendi','Affinity':'Yakınlık','Play Time':'Oyun Süresi','Max Power':'Azami Güç','Job Count':'Meslek Sayısı','Ability Count':'Yetenek Sayısı','Norende Population':'Norende Nüfusu','Close':'Kapat','Next':'Sonraki',
'Friend Menu':'Arkadaş Menüsü','Guests':'Misafirler','Update Data':'Veriyi Güncelle','Update via Internet':'İnternetle Güncelle','Update via Local Wireless':'Yerel Kablosuzla Güncelle','Update StreetPass Data':'StreetPass Verisini Güncelle','Register Friend':'Arkadaş Kaydet','Register via Internet':'İnternetle Kaydet','Register via Local Wireless':'Yerel Kablosuzla Kaydet','Autopilot':'Otomatik Pilot',
' to Confirm/ Cancel':' Onayla/İptal','    to Confirm/ Cancel':'    Onayla/İptal','Cursor Position':'İmleç Konumu','Difficulty':'Zorluk','Easy':'Kolay','Normal':'Normal','Hard':'Zor','Message Speed':'Mesaj Hızı','Fast':'Hızlı','Slow':'Yavaş','Acquire ':'Kazan ','Acquire':'Kazan',
'Shortcut Settings':'Kısayol Ayarları','Text Settings':'Metin Ayarları','Japanese':'Japonca','English':'İngilizce','French':'Fransızca','Italian':'İtalyanca','German':'Almanca','Spanish':'İspanyolca','SFX Volume':'Efekt Sesi','Music Volume':'Müzik Sesi','Voice Volume':'Seslendirme','Autoplay':'Otomatik Oynatma','Restore Defaults':'Varsayılanları Yükle','Message Settings':'Mesaj Ayarları','Voice Settings':'Ses Ayarları','Battle Settings':'Savaş Ayarları','Confirm Turn Start':'Tur Başını Onayla','Update Data at Send':'Gönderirken Veriyi Güncelle','Game Settings':'Oyun Ayarları','Autosave':'Otomatik Kayıt','Destination Marker':'Hedef İşareti','Off':'Kapalı','Gain EXP':'EXP Kazanımı','Gain Job Points':'MP Kazanımı','Encounter Rate':'Karşılaşma Oranı','＋100%':'＋100%','Sound Settings':'Ses Ayarları',
'Enigmatic Writings':'Gizemli Yazılar','Notes':'Notlar','Encyclopedia':'Ansiklopedi','Help':'Yardım','Job Descriptions':'Meslek Açıklamaları','Event Viewer':'Olay İzleyici','People':'Kişiler','Locations':'Konumlar','Terms':'Terimler','Items':'Eşyalar','Bestiary':'Canavar Ansiklopedisi','Cmbt. Bonuses':'Savaş Bonusları','Abilities':'Yetenekler','Main Scenario':'Ana Senaryo','Sub-Scenario':'Yan Senaryo','Party Chat':'Parti Sohbeti','Movies':'Videolar','Voice':'Ses','Text':'Metin',
'Experience':'Deneyim','Current Lv':'Mevcut Sv','To Next Lv':'Sonraki Sv','Total EXP':'Toplam EXP','Total JP':'Toplam MP','Equip':'Kuşan','Optimum':'En İyi','Imm.':'Bağ.','Res.':'Dir.','Stat Values':'Stat Değerleri','Base Values':'Temel Değerler','Variable Info':'Değişken Bilgi','Remove':'Çıkar','Support Abilities':'Destek Yetenekleri','Unused Cost…':'Boş Maliyet…','Fixed Command':'Sabit Komut','Required':'Gerekli','Black Magic':'Kara Büyü','White Magic':'Beyaz Büyü','Destination':'Hedef','To Ability':'Yeteneğe','To Equip':'Ekipmana','Back':'Geri','Stat Changes':'Stat Değişimleri','Job Info':'Meslek Bilgisi','Ability List':'Yetenek Listesi','Max HP':'Azami HP','Max MP':'Azami BP','None':'Yok',
'Change Abilink partner?':'Yetenek Bağı ortağını değiştir?','The following support abilities will be':'Aşağıdaki destek yetenekleri','removed if you change the Abilink.':'Yetenek Bağı değişirse kaldırılacak.',
'Add Funds':'Para Ekle','Confirm':'Onayla','Purchase':'Satın Al','Balance':'Bakiye','Total':'Toplam','tax incl.':'vergi dahil','Owned':'Sahip',
'SP Drink purchased.\nDo you want to use it now?':'SP İçeceği satın alındı.\nŞimdi kullanmak ister misin?','Current SP Drink tickets':'Mevcut SP İçeceği Biletleri','Current SP Drinks':'Mevcut SP İçecekleri','Use SP Drink':'SP İçeceği Kullan','Purchase SP Drink':'SP İçeceği Satın Al','Proceed':'Devam','All':'Tümü','Magic Used':'Kullanılan Büyü','Time':'Süre',
'Location':'Konum','Inventory':'Envanter','Price':'Fiyat','Buy':'Al','Sell':'Sat','Exit':'Çıkış','Learned':'Öğrenildi','Funds':'Para','Max':'Azami',
'Your SD Card is already full of photos.':'SD Kartın fotoğraflarla dolu.','Could not recognize SD Card.':'SD Kart tanınamadı.','Your SD Card lacks enough space to\nsave a photo.':'SD Kartında fotoğraf kaydetmek için\nyeterli alan yok.',"You've no SD Card inserted.":'Takılı bir SD Kart yok.',
'Special List':'Özel Liste','Set Parts':'Parçaları Ayarla','Use Condition':'Kullanım Koşulu','Part List':'Parça Listesi','Special':'Özel','Attack Messages':'Saldırı Mesajları','One':'Tek','Support Messages':'Destek Mesajları','Heal':'İyileştir','Aid':'Yardım',
"I'm preparing to load the AR marker. Set me down\nupon a flat surface and leave me untouched for\na moment.\n\nBe careful to avoid hitting things or people around\nyou when playing.":'AR işaretini yüklemeye hazırlanıyorum. Beni düz\nbir yüzeye bırak ve kısa süre dokunma.\n\nOynarken çevrendeki eşya ve insanlara\nçarpmamaya dikkat et.',
'SP Drink':'SP İçeceği','SP Drink purchased.':'SP İçeceği satın alındı.','Do you want to use it now?':'Şimdi kullanmak ister misin?','Do you want to use an SP Drink':'Bir SP İçeceği kullanıp','to gain   SP?':'   SP kazanmak ister misin?','Use':'Kullan',
'ATK：':'SAL：','DEF：':'SAV：','M.ATK：':'B.SAL：','M.DEF：':'B.SAV：','Aim：':'İsabet：','Evade：':'Kaçınma：','Critical：':'Kritik：',
'Raise Amt':'Miktarı Artır','Lower Amt':'Miktarı Azalt','OK':'Tamam','Cancel':'İptal','Controls Help':'Kontrol Yardımı','Weak':'Zayıf','All Foes':'Tüm Düşmanlar','Foe List':'Düşman Listesi','All Allies':'Tüm Müttefikler','Ally List':'Müttefik Listesi','P.ATK:':'F.SAL:','P.DEF:':'F.SAV:','M.ATK:':'B.SAL:','M.DEF:':'B.SAV:','Aim:':'İsabet:','Evade:':'Kaçınma:','Critical:':'Kritik:','Purchasing:':'Satın Alma:','Selling:':'Satış:',
}

EXACT_LOCATIONS = {
'Twisted Treetop':'Bükülmüş Ağaç Tepesi','Eisen Bridge':'Eisen Köprüsü','SS Funky Francisca':'SS Funky Francisca',
'Altar of Wind':'Rüzgar Sunağı','Altar of Water':'Su Sunağı','Altar of Fire':'Ateş Sunağı','Altar of Earth':'Toprak Sunağı','Altar of Darkness':'Karanlık Sunağı',
'Northern Hidden Village':'Kuzey Gizli Köy','Western Hidden Village':'Batı Gizli Köy','Thieves\' Den':'Hırsızlar İni','Temple of Water':'Su Tapınağı','Temple of Fire':'Ateş Tapınağı','Temple of Earth':'Toprak Tapınağı','Vampire Castle':'Vampir Kalesi','Council Chamber':'Konsey Salonu','House by the Sea':'Deniz Kenarındaki Ev','Central Healing Tower':'Merkez Şifa Kulesi','Gravemark Village':'Gravemark Köyü','Goodman Residence':'Goodman Konağı','Cellar Laboratory':'Mahzen Laboratuvarı','Grand Mill Works':'Büyük Değirmen','Yulyana Woods Needleworks':'Yulyana Ormanı Nakışhanesi','The Drunken Pig Tavern':'Sarhoş Domuz Meyhanesi','The Sea Slug':'Deniz Sümüklüböceği',
'Eternian Central Command':'Eternia Merkez Karargahı',"Grand Marshal's Daughter's Room":'Büyük Mareşalin Kızının Odası','White Magic Circulation Hub':'Ak Büyü Dolaşım Merkezi','Engine Room Core':'Makine Dairesi Çekirdeği','Starkfort War Room':'Starkfort Savaş Odası',
'Ancheim Palace':'Ancheim Sarayı','Khamer Profiteur Merchantry':'Khamer Profiteur Ticarethaneleri','Florie Dwelling':'Florie Konutu','Hartschild':'Hartschild','Starkfort':'Starkfort','Eternia':'Eternia',
}

REPLACEMENTS = [
('Norende Ravine','Norende Vadisi'),('Ruins of Centro Keep','Centro Kalesi Harabeleri'),('Lontano Villa','Lontano Villası'),('Temple of Wind','Rüzgar Tapınağı'),('Vestment Cave','Vestment Mağarası'),('Harena Ruins','Harena Harabeleri'),('Grand Mill Works','Büyük Değirmen Atölyesi'),('Miasma Woods','Miasma Ormanı'),('Mount Fragmentum','Fragmentum Dağı'),('Witherwood','Witherwood Ormanı'),('Florem Gardens','Florem Bahçeleri'),('Twilight Ruins','Alacakaranlık Harabeleri'),('Mythril Mines','Mithril Madenleri'),('Underflow','Yeraltı Akıntısı'),('Starkfort Interior','Starkfort İç Kısım'),('Grapp Keep','Grapp Kalesi'),('Engine Room','Makine Dairesi'),('Central Command - Prison','Merkez Karargah - Hapishane'),('Central Command','Merkez Komuta'),('Everlast Tower','Everlast Kulesi'),('Vampire Castle','Vampir Kalesi'),('Dark Aurora','Karanlık Aurora'),("Dimension's Hasp",'Boyut Kilidi'),('Kingdom of Caldisla','Caldisla Krallığı'),('Florem','Florem'),('Grandship','Grandship'),
]
SUFFIX = {
'Trail':'Patika','Climb':'Tırmanış','Vista':'Manzara','Peak':'Zirve','South':'Güney','Central':'Merkez','North':'Kuzey','West':'Batı','East':'Doğu','Slope':'Yamaç','Interior':'İç Kısım','City Entrance':'Şehir Girişi','Plaza':'Meydan',"Matriarch's Hall":'Anaerkil Salonu','Upper Deck':'Üst Güverte','Markets':'Pazarlar','Bridge':'Köprü','Deck':'Güverte','Town':'Şehir','Palace':'Saray','Inn':'Han',
}

def translate_location(s:str):
    # Prefer the user's own translated location terminology whenever the same
    # English source string already exists in Common_en.
    cv=_COMMON_TR.get(s)
    if cv and cv!=s:
        return cv
    if s in EXACT_LOCATIONS: return EXACT_LOCATIONS[s]

    # For floor/wing variants, first translate the base place with the user's
    # terminology, then localize the suffix. This keeps e.g. Lontano Villası and
    # Büyük Değirmen Atölyesi consistent on every floor.
    if ' - ' in s:
        base,suf=s.rsplit(' - ',1)
        bcv=_COMMON_TR.get(base)
        if bcv and bcv!=base:
            outbase=bcv
        elif base in EXACT_LOCATIONS:
            outbase=EXACT_LOCATIONS[base]
        else:
            outbase=base
            for a,b in REPLACEMENTS:
                if outbase.startswith(a): outbase=b+outbase[len(a):]; break
        if suf in SUFFIX:
            suf=SUFFIX[suf]
        else:
            # Preserve floor/basement numbers while translating directions.
            words={'East':'Doğu','West':'Batı','North':'Kuzey','South':'Güney','Central':'Merkez','Interior':'İç Kısım'}
            parts=suf.split(' ')
            parts=[words.get(x,x) for x in parts]
            suf=' '.join(parts)
        out=outbase+' - '+suf
        return out if out!=s else None

    out=s
    for a,b in REPLACEMENTS:
        if out.startswith(a): out=b+out[len(a):]; break
    return out if out!=s else None

def translate_ui(s:str, pane='', ordinal=0, context=''):
    # Compact, context-specific labels for genuinely narrow panes. These keep the
    # same concepts/terminology but avoid unreadably shrinking Turkish text.
    if 'Layout/99_Battle' in context:
        compact={'All Allies':'Tümü','Ally List':'Dostlar','All Foes':'Düşmanlar','Foe List':'Düş. Listesi','OK':'Onay'}
        if s in compact: return compact[s]
    if s=='Bestiary' and 'Layout/17_D_Report' in context: return 'Canavarlar'
    if s=='Abilink' and 'Layout/08_MainMenu' in context: return 'Ytnk. Bağı'
    if s=='Friends' and 'EndRoll' in context: return 'Arkadaş'
    if s=='Evade' and any(x in context for x in ('Layout/13_ItemMenu','Layout/17_D_Report','Layout/50_Shop')): return 'Kaçın.'
    if s=='Heal' and 'Layout/51_Skill' in context: return 'Şifa'
    if s=='Aid' and 'Layout/51_Skill' in context: return 'Yard.'

    # Context-sensitive exceptions where the same English source term has a
    # different meaning in gameplay text.
    if s=='Slow' and ('Config' in context or 'message' in pane.lower() or 'msg' in pane.lower()):
        return 'Yavaş'
    if s=='Time' and ('Colony' in context or 'time' in pane.lower()):
        return 'Süre'

    # The user's Common_en translation is the terminology authority. This
    # prevents UI terms such as Abilink / White Magic / Party Chat / MND from
    # drifting away from the main patch.
    cv=_COMMON_TR.get(s)
    if cv and cv!=s:
        return cv

    if s in UI_TRANSLATIONS: return UI_TRANSLATIONS[s]
    # Preserve obvious layout/test placeholders and punctuation/numbers.
    stripped=s.replace('\n','')
    if not stripped or set(stripped)<=set('aiw/ .:-_0123456789%＋'):
        return None
    # MiniMap location labels are highly reliable localizable strings.
    if '/MiniMap/' in context or 'MAP_' in context:
        return translate_location(s)
    return None
