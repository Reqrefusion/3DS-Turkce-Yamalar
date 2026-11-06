# -*- coding: utf-8 -*-
"""Additional ItemTable translations for Bravely Default TR v3.7.
User-facing terminology follows the project's existing UI vocabulary.
"""
import re

NAME_EXACT = {
'Long Sword':'Uzun Kılıç','Mythril Sword':'Mithril Kılıç','Ice Brand':'Buz Kılıcı','Sleep Blade':'Uyku Kılıcı','Rune Blade':'Rün Kılıcı','Chaos Blade':'Kaos Kılıcı','Night Emperor':'Gece İmparatoru','Silver Sword':'Gümüş Kılıç','Golden Sword':'Altın Kılıç','Soaring V Blade':'Yükselen V Kılıcı','Sword of T':"T'nin Kılıcı",'Sword of R':"R'nin Kılıcı",
'Mythril Axe':'Mithril Balta','Viking Axe':'Viking Baltası','War Axe':'Savaş Baltası','Heavy Axe':'Ağır Balta','Flare Hatchet':'Alev Baltası','Cross Axe':'Haç Balta','Giant Axe':'Dev Baltası','Grinder Axe':'Öğütücü Balta','Silver Axe':'Gümüş Balta','Golden Axe':'Altın Balta','Fox Tail':'Tilki Kuyruğu',
'Valkyrie Halberd':'Valkür Teberi','Mythril Spear':'Mithril Mızrak','Holy Lance':'Kutsal Mızrak','Cross Spear':'Haç Mızrağı','Crimson Spear':'Kızıl Mızrak',"Lü Bu’s Spear":"Lü Bu’nun Mızrağı",'Silver Lance':'Gümüş Mızrak','Golden Spear':'Altın Mızrak','Silver Glaive':'Gümüş Glaive',
"Wizard’s Rod":'Büyücü Asası','Mythril Rod':'Mithril Asa','Rod of Fire':'Ateş Asası','Rod of Ice':'Buz Asası',"Demon’s Rod":'İblis Asası','Poison Rod':'Zehir Asası','Battle Mace':'Savaş Gürzü','Hammer Mace':'Çekiç Gürzü',"Ogre’s Club":'Ogre Sopası','Silver Rod':'Gümüş Asa','Golden Rod':'Altın Asa',
'Mythril Staff':'Mithril Değnek','Jade Crosier':'Yeşim Değnek','Gale Staff':'Fırtına Değneği',"Demon’s Staff":'İblis Değneği','Oaken Pole':'Meşe Sırığı','Iron Pole':'Demir Sırık','Diamond Staff':'Elmas Değnek','Simian Staff':'Maymun Değneği','Silver Staff':'Gümüş Değnek','Golden Staff':'Altın Değnek',
'Mage Masher':'Büyücü Ezici','Frenzy Dagger':'Çılgınlık Hançeri','Mythril Dagger':'Mithril Hançer','Orichal Dagger':'Orikalkum Hançer','Main-Gauche':'Main-Gauche',"Thief’s Knife":'Hırsız Bıçağı','Assassin Dagger':'Suikastçı Hançeri','Air Knife':'Hava Bıçağı','Carving Knife':'Oyma Bıçağı','Silver Dagger':'Gümüş Hançer','Golden Dagger':'Altın Hançer','Falcon Knife':'Şahin Bıçağı','Magic Knife':'Büyü Bıçağı',
'Birch Bow':'Huş Yayı','Iron Bow':'Demir Yay','Composite Bow':'Kompozit Yay','Ancient Bow':'Kadim Yay','Mythril Bow':'Mithril Yay','Aeolian Bow':'Aeolus Yayı','Killer Bow':'Katil Yay',"Yoichi’s Bow":'Yoichi’nin Yayı','Elven Bow':'Elf Yayı',"Artemis’s Bow":'Artemis’in Yayı',"Angel’s Bow":'Melek Yayı','Silver Bow':'Gümüş Yay','Golden Bow':'Altın Yay',
'Silver Katana':'Gümüş Katana','Golden Katana':'Altın Katana','Katana of Victory':'Zafer Katanası',
'Iron Knuckles':'Demir Muşta','Spiked Knuckles':'Çivili Muşta','Hammer Knuckles':'Çekiç Muşta','Mythril Knuckles':'Mithril Muşta','Divine Fists':'İlahi Yumruklar','Hadean Claws':'Hades Pençeleri','Toxic Claws':'Zehirli Pençeler','Thumbing Claws':'Kör Eden Pençeler','Kaiser Knuckles':'Kaiser Muştası','Bastet Claws':'Bastet Pençeleri','Silver Knuckles':'Gümüş Muşta','Golden Knuckles':'Altın Muşta',
'Round Shield':'Yuvarlak Kalkan','Large Shield':'Büyük Kalkan','Spiked Shield':'Çivili Kalkan','Cross Shield':'Haç Kalkanı','Mythril Shield':'Mithril Kalkan','Adamant Shield':'Adamant Kalkan','Iceflame Shield':'Buzalev Kalkanı','Lustrous Shield':'Parlak Kalkan','Dark Shield':'Karanlık Kalkan','Blessed Shield':'Kutsanmış Kalkan','Aegis Shield':'Aegis Kalkanı','Bloody Shield':'Kanlı Kalkan',
'Bronze Gauntlets':'Bronz Eldiven','Mythril Gloves':'Mithril Eldiven','Giant’s Gloves':'Dev Eldiveni','Adamant Gauntlets':'Adamant Eldiven','Thief Gloves':'Hırsız Eldiveni','Genji Gloves':'Genji Eldiveni','Heike Gloves':'Heike Eldiveni','Bronze Bangle':'Bronz Bilezik','Iron Bangle':'Demir Bilezik','Mythril Bangle':'Mithril Bilezik','Adamant Bangle':'Adamant Bilezik','Power Bracers':'Güç Bileklikleri','Hyper Bracers':'Hiper Bileklikler','Heart Ring':'Kalp Yüzüğü','Life Ring':'Yaşam Yüzüğü','Soul of Thamasa':'Thamasa’nın Ruhu','Force Armlets':'Güç Kollukları','Magic Armlets':'Büyü Kollukları','Hermes Sandals':'Hermes Sandaletleri','Hermes Shoes':'Hermes Ayakkabıları','Artisan Gloves':'Zanaatkâr Eldiveni','Dwarven Gloves':'Cüce Eldiveni',
'Flame Charm':'Alev Tılsımı','Ice Charm':'Buz Tılsımı','Thunder Charm':'Yıldırım Tılsımı','Wind Charm':'Rüzgâr Tılsımı','Earth Charm':'Toprak Tılsımı','Light Charm':'Işık Tılsımı','Dark Charm':'Karanlık Tılsımı','Mage Shell':'Büyücü Kabuğu','Barrier Shroud':'Bariyer Örtüsü','Black Belt':'Kara Kuşak','Star Pendant':'Yıldız Kolye','Silver Glasses':'Gümüş Gözlük','White Cape':'Beyaz Pelerin','Earthing Rod':'Topraklama Çubuğu','Peace Ring':'Huzur Yüzüğü','Rebuff Locket':'Red Kolyesi','Safety Ring':'Güvenlik Yüzüğü','Courage Ring':'Cesaret Yüzüğü','Ward Bangle':'Koruma Bileziği','Taunt Bangle':'Tahrik Bileziği','Growth Egg':'Gelişim Yumurtası','Golden Egg':'Altın Yumurta','Red Muleta':'Kırmızı Muleta','Smiley Badge':'Gülen Rozet','Reflect Ring':'Yansıtma Yüzüğü','Gale Hairpin':'Fırtına Tokası','Alarm Earrings':'Alarm Küpeleri','Venture Badge':'Macera Rozeti',
'Leather Cap':'Deri Başlık','Feather Hat':'Tüylü Şapka','Tiger Mask':'Kaplan Maskesi','Acorn Hat':'Palamut Şapkası','Black Cowl':'Kara Başlık','Adamant Hat':'Adamant Şapka','Red Cap':'Kırmızı Başlık','Royal Crown':'Kraliyet Tacı','Pointy Hat':'Sivri Şapka','Cat-Ear Hood':'Kedi Kulaklı Başlık','Laurel Wreath':'Defne Tacı',"Mage’s Hat":'Büyücü Şapkası','Holy Miter':'Kutsal Mitra','Lambent Hat':'Işıltılı Şapka',"Lamia’s Tiara":'Lamia’nın Tacı','Gold Hairpin':'Altın Toka',
'Bronze Helm':'Bronz Miğfer','Iron Helm':'Demir Miğfer','Mythril Helm':'Mithril Miğfer','Yggdrasil Helm':'Yggdrasil Miğferi','Orichalcum Helm':'Orikalkum Miğfer','Adamant Helm':'Adamant Miğfer','Genji Helm':'Genji Miğferi','Heike Helm':'Heike Miğferi','Crystal Helm':'Kristal Miğfer',
'Linen Cuirass':'Keten Zırh','Kenpo Gi':'Kenpo Gi','Bronze Breastplate':'Bronz Göğüslük','Mythril Plate':'Mithril Plaka','Mirage Vest':'Serap Yeleği','Power Sash':'Güç Kuşağı','Viking Coat':'Viking Paltosu','Adamant Vest':'Adamant Yelek','Star Corslet':'Yıldız Zırhı','Brave Suit':'Brave Giysisi','Crystal Vest':'Kristal Yelek','Hempen Tunic':'Kenevir Tunik','Silk Robe':'İpek Cübbe','Tabby Suit':'Tekir Giysi','Floral Robe':'Çiçekli Cübbe','Black Robe':'Kara Cübbe','White Robe':'Beyaz Cübbe','Gaia Gear':'Gaia Giysisi','Luminous Robe':'Işıltılı Cübbe','Rainbow Dress':'Gökkuşağı Elbisesi','Lordly Robes':'Asil Cübbeler','Bravo Bikini':'Bravo Bikini','Onion Shirt':'Soğan Gömleği',"Melodist’s Shirt":'Melodistin Gömleği',"Knight’s Tunic":'Şövalye Tuniği',"Edea’s Garb":'Edea’nın Giysisi','Plain Tunic':'Sade Tunik','Leather Armor':'Deri Zırh','Bronze Armor':'Bronz Zırh','Iron Armor':'Demir Zırh','Mythril Armor':'Mithril Zırh','Yggdrasil Armor':'Yggdrasil Zırhı','Orichalcum Mail':'Orikalkum Zırh','Adamant Armor':'Adamant Zırh','Genji Armor':'Genji Zırhı','Heike Armor':'Heike Zırhı','Crystal Mail':'Kristal Zırh','Dimensional Garb':'Boyutsal Giysi','Bravo Bunny':'Bravo Tavşanı','Eastern War Garb':'Doğu Savaş Giysisi','Cadet Uniform':'Harbiyeli Üniforması',
'Teleport Stone':'Işınlanma Taşı','Bomb Fragment':'Bomba Parçası','Antarctic Wind':'Antarktik Rüzgâr',"Zeus’s Wrath":'Zeus’un Gazabı','Tengu Yawn':'Tengu Esnemesi','Earth Drum':'Toprak Davulu','Beast Liver':'Canavar Karaciğeri','Hard Scale':'Sert Pul','Insect Antenna':'Böcek Anteni','Monster Fiber':'Canavar Lifi','Spirit Bone':'Ruh Kemiği','Demon Tail':'İblis Kuyruğu','Dragon Fang':'Ejder Dişi','Fairy Wing':'Peri Kanadı','Fulmen Shard':'Fulmen Parçası','Desert Rose':'Çöl Gülü','Dark Matter':'Karanlık Madde','Rage Orb':'Öfke Küresi','Resist Blind':'Körlük Direnci','Resist Silence':'Susturma Direnci','Resist Sleep':'Uyku Direnci','Resist Dread':'Dehşet Direnci','Quarter Elixir':'Çeyrek İksir','Half Elixir':'Yarım İksir','Dry Ether':'Kuru Eter','Smelling Salts':'Kokulu Tuz','SP Drink Ticket':'SP İçeceği Bileti','Strange Hourglass':'Tuhaf Kum Saati',
}

# Preserve proper names / internal test entries unless a natural Turkish UI name is known.
def translate_item_name(s):
    if s in NAME_EXACT: return NAME_EXACT[s]
    if 'Dummy' in s or s in {'Donnerjäger','Donnerschütz','Kiku-Ichimonji','Mutsu-no-Kami','Ama-no-Murakumo','Deus Ex Machina','Susano-o','Main-Gauche'}:
        return s
    # conservative fallbacks
    return None

# Equipment descriptions 1..277, kept concise to fit the original description panes.
_EQUIP = '''
Basit tasarımlı, geniş ağızlı bir kılıç.
Uzun demir ağızlı bir kılıç.
Çift elle kullanılan çelik bir büyük kılıç.
Çöl halkının kullandığı kavisli bir kılıç.
Çok büyük ve ağır bir büyük kılıç.
Kuşanıldığında F.SAV'ı artıran bir kılıç.
Nadir mithrilden yapılmış süslü bir kılıç.
Magmada dövülmüş, ateş gücü taşıyan bir kılıç.
Buz gibi metalden, su gücü taşıyan bir kılıç.
Drain yeteneğine sahip büyülü bir kılıç.
Nadiren uyku etkisi veren bir kılıç.
Rünlü, B.SAL'ı artıran bir kılıç.
Büyük bir kralın ışık gücü taşıyan kılıcı.
Nadiren şaşkınlık etkisi veren bir kılıç.
Efsanevi paladin Roland'ın kılıcı.
Nadiren büyülenme etkisi veren uğursuz bir kılıç.
Ölümsüzlere karşı özellikle etkili gümüş bir kılıç.
Baştan uca altın kaplı görkemli bir kılıç.
Dostluk, çaba ve zaferi simgeleyen bir kılıç.
Savaşçı “T”nin toprak gücü taşıyan kılıcı.
Savaşçı “R”nin ışık gücü taşıyan kılıcı.
Avcıların kullandığı küçük, çok amaçlı bir balta.
Nadir mithrilden yapılmış süslü bir balta.
Sucul düşmanlara karşı özellikle etkili bir balta.
Savaşta kullanım için dengelenmiş bir balta.
Devasa, ağır ve çift ağızlı bir balta.
Ateş gücü taşıyan küçük bir balta.
Kill yeteneğini kullanmayı sağlayan büyük bir balta.
İblislere karşı özellikle etkili kutsal bir balta.
Kadim devlerin kullandığı tek ağızlı büyük bir balta.
Kayaları yaran, toprak gücü taşıyan büyük bir balta.
Nadiren dehşet etkisi veren büyük bir balta.
İradeyi artıran tek ağızlı büyük bir balta.
Altınla bezenmiş görkemli, çift ağızlı bir balta.
Çevikliği artıran tilki tanrısı baltası.
Canavar avına uygun çift ağızlı bir balta.
Basit ve kolay kullanılan bir mızrak.
Ucunda büyük bir bıçak bulunan sırıklı silah.
Ucunda çivili balta bulunan çok amaçlı sırıklı silah.
Valkürlerin kullandığı ayrıntılı bir teber.
Nadir mithrilden yapılmış süslü bir mızrak.
Kutsal güç taşıyan ışık mızrağı.
Doğudan gelen, ölümsüz avlayan bir mızrak.
Ünlü bir savaşçının simgesi olan kan kırmızısı mızrak.
Deniz tanrısının yıldırım gücü taşıyan mızrağı.
Sucul düşmanlara karşı etkili kutsal bir mızrak.
Savaş tanrısının kullandığı isabetli bir mızrak.
Kadim bir savaş lordunun kullandığı göksel teber.
Sucul düşmanlara karşı etkili, kaliteli bir mızrak.
Altın süslemeli görkemli bir mızrak.
Thunderclap olarak da bilinen büyülü mızrak.
B.SAV'ı artıran gümüş mızrak.
Büyü gücünü artıran taş takılı bir asa.
Kara Büyücüler için büyü gücünü artıran asa.
Nadir mithrilden yapılmış süslü bir asa.
Ateş saldırılarını güçlendiren bir asa.
Su saldırılarını güçlendiren bir asa.
Karanlık saldırılarını güçlendiren vahşi bir asa.
Tek hedefe Aspir yapan bir asa.
Yüksek olasılıkla zehir etkisi veren bir asa.
Rastgele Kara Büyü yapan bir asa.
Kalın çelikten yapılmış ağır, küt bir silah.
Çivili demir top başlı küt bir silah.
Savaş ve zanaat için kullanılan çekiç biçimli bir gürz.
Yıldırım saldırılarını güçlendiren bir gürz.
Yıldırım saldırılarını güçlendiren bir asa.
Saf altından yapılmış ağır ve gösterişli bir asa.
Kutsal bir daldan oyulmuş ince bir değnek.
İnce işlenmiş mithril uçlu bir değnek.
Mücevherli halka başlı bir rahip değneği.
Cure yapan şifa değneği.
Bir zamanlar kaybolmuş, rüzgâr saldırılarını güçlendiren değnek.
Tek hedefe Esuna yapan mistik bir değnek.
Tek hedefe Raise yapan mucizevi bir değnek.
Kadim kötülükten gelen karanlık gücü taşıyan değnek.
Sertleştirilmiş meşeden oyulmuş bir sırık.
Pürüzsüz yüzeyli ağır demir sırık.
Kristalleşmiş elmas tozundan yapılmış bir sırık.
Çoklu hedef saldırılarını güçlendiren bir sırık.
Görkemli, gümüş kaplama bir değnek.
Saf altın başlı gösterişli bir değnek.
Standart, hafif ve çift ağızlı bir hançer.
Nadiren susturma etkisi veren kadim bir hançer.
Harena bölgesinden kavisli bir hançer.
Nadiren çılgınlık etkisi veren barbar hançeri.
Nadir mithrilden yapılmış jilet keskinliğinde hançer.
Değerli orikalkumdan yapılmış bir hançer.
Kaçınmayı artıran geniş ağızlı bir hançer.
Mug yeteneğine sahip bir hançer.
Yüksek kritik oranlı, insansılara karşı etkili hançer.
Nadiren ölüm etkisi veren gizli bir hançer.
Kadim, çift ağızlı kısa bir kılıç.
Kaçınmayı artıran ninja hançeri.
Rüzgâr gücü taşıyan kaliteli, çift ağızlı bıçak.
Kaçınmayı artıran ilahi güçte bir bıçak.
Namahage ogrunun kullandığı tek ağızlı bıçak.
Canavarlara karşı özellikle etkili geniş bir hançer.
Saf altından yapılmış gösterişli bir hançer.
Çevikliği artıran eşsiz bir silah.
B.SAL'ı artıran eşsiz bir silah.
Quick kullanmayı sağlayan bir hançer.
İblisler ve uçan düşmanlara karşı etkili bir yay.
Uçan düşmanlara karşı etkili demir yay.
Uçan düşmanlara karşı etkili, nadiren zehirleyen yay.
Uçan düşmanlara karşı etkili, nadiren felç eden yay.
Uçan düşmanlara karşı etkili kaliteli mithril yay.
Pençelerden yapılmış, uçan düşmanlara karşı etkili yay.
Haste yeteneğine sahip, uçan düşmanlara karşı etkili yay.
Uçan düşmanlara karşı etkili, nadiren ölüm veren yay.
Yüksek kritik oranlı, uçan düşmanlara karşı etkili yay.
Uçan düşmanlara karşı etkili, nadiren şaşırtan yay.
Av tanrıçasına ait, uçan düşmanlara karşı etkili yay.
Uçan düşmanlara karşı etkili, nadiren büyüleyen yay.
Uçan düşmanlara karşı etkili, nadiren susturan yay.
Altın kaplı, uçan düşmanlara karşı etkili yay.
Thunder Hunter olarak bilinen büyülü bir yay.
Katana adı verilen kavisli kesici bir kılıç.
Mithril çeliğinden ustalıkla dövülmüş bir kılıç.
Koyu renkli, yüksek dayanımlı düz bir katana.
Keskin ağızlı, ince ve zarif bir kılıç.
Güzel dalgalı çeliğe sahip bir kılıç.
Yıldırım gücü taşıyan ve yıldırımı geçersiz kılan bir kılıç.
Defang yeteneğine sahip gizemli bir kılıç.
Bir zamanlar devrimci bir liderin kullandığı kılıç.
Ejderlere karşı etkili tarihî bir kılıç.
Ustanın öğrencisine verdiği kılıç.
Karanlığa direnç sağlayan gümüş bir kılıç.
Tamamen altından yapılmış gösterişli bir katana.
Dostluk ve zaferi simgeleyen özel bir silah.
Yumruk dövüşünde kullanılan çelik silahlar.
Keskin çiviler takılı yumruk silahları.
Çelik ve kurşundan yıkıcı yumruk silahları.
Mithril çeliğinden kaliteli yumruk silahları.
İlahi çivili, ışık gücü taşıyan muştalar.
Yeraltı dünyasından gelen karanlık pençeler.
Vuruşta zehir etkisi verebilen pençeler.
Vuruşta körlük etkisi verebilen pençeler.
Fetihçi bir imparatorun kullandığı muştalar.
Canavarlara karşı özellikle etkili kedi pençeleri.
Ejderlere karşı etkili seçkin muştalar.
Altından yapılmış lüks ve ağır muştalar.
Yakın dövüş için küçük bir kalkan.
Deri kaplı büyük, yuvarlak kalkan.
Mermileri engellemek için dev bir kalkan.
Saldırıları güçlendiren tehditkâr bir kalkan.
Şövalyelerin kullandığı eliptik kalkan.
Mithril çeliğinden modern bir kalkan.
Adamant kabuktan yapılmış bir kalkan.
Ateş ve suyu geçersiz kılan mucizevi kalkan.
Işığı geçersiz kılan kutsal kalkan.
Karanlığı geçersiz kılan simsiyah kalkan.
Cura yeteneğine sahip şanlı bir kalkan.
Dehşeti geçersiz kılan kutsal kalkan.
Savunmayı artırıp kaçınmayı düşüren kalkan.
Thunder Protector olarak bilinen büyülü kalkan.
Kalın ve ağır bronz eldivenler.
Parmak eklemleri hareketli demir eldivenler.
Nadir mithrilden güçlü ve hafif eldivenler.
Gücü artırıp beceriyi düşüren eldivenler.
Adamant kabuktan mitten biçimli eldivenler.
Çalma şansını artıran eldivenler.
Kadim bir savaşçı klanından kalma eldivenler.
Gururlu bir savaşçı klanının kullandığı eldivenler.
HP'yi artıran süslü bronz bilezik.
HP'yi artıran ayrıntılı demir bilezik.
HP'yi artıran göz alıcı mithril bilezik.
HP'yi artıran adamant kabuk bilezik.
Gücü artıran dövüşçü bilek sargıları.
Gücü büyük ölçüde artıran deri bantlar.
MP'yi büyük ölçüde artıran gizemli yüzük.
HP'yi büyük ölçüde artıran tuhaf yüzük.
Zekâyı artıran güzel bir muska.
Zekâyı büyük ölçüde artıran ilahi muska.
İradeyi artıran işlemeli metal kolluklar.
İradeyi büyük ölçüde artıran şeytani kolluklar.
Çevikliği artıran hafif sandaletler.
Çevikliği büyük ölçüde artıran çok hızlı ayakkabılar.
Beceriyi artıran esnek eldivenler.
Beceriyi büyük ölçüde artıran demirci eldivenleri.
Ateşi bastıran bir tılsım.
Suyu bastıran bir tılsım.
Yıldırımı bastıran bir tılsım.
Rüzgârı bastıran bir tılsım.
Toprağı bastıran bir tılsım.
Işığı bastıran bir tılsım.
Karanlığı bastıran bir tılsım.
Cilde uygulandığında B.SAV'ı artıran bir tılsım.
B.SAV'ı büyük ölçüde artıran bir örtü.
Kritik oranını artıran usta kuşağı.
Zehri geçersiz kılan yıldız biçimli kolye.
Körlüğü geçersiz kılan biçimsiz gözlük.
Susturmayı geçersiz kılan ince ve güzel pelerin.
Uykuyu geçersiz kılan mandal biçimli aksesuar.
Felci geçersiz kılan kemer aksesuarı.
Şaşkınlığı geçersiz kılan huzur yüzüğü.
Büyülenmeyi geçersiz kılan kolye.
Ölümü geçersiz kılan kaplamalı yüzük.
Dehşeti geçersiz kılan dayanışma yüzüğü.
Düşmanları gruptan uzak tutan kolluk.
Canavarları gruba çeken kolluk.
pg kazancından vazgeçip EXP ve JP'yi ikiye katlayan yumurta.
EXP ve JP'den vazgeçip pg'yi ikiye katlayan yumurta.
Hedef olma oranını artıran parlak kırmızı kumaş.
Hedef olma oranını sabitleyen dostça bir rozet.
Savaş başında Reflect uygulayan yüzük.
Müttefiklerin ilk saldırı şansını artıran süs.
Düşmanların ilk saldırı şansını azaltan küpeler.
Müttefiklerin Brave Attack oranını artıran rozet.
Düşmanların Brave Attack oranını azaltan aygıt.
Dikilmiş deri şeritlerden yapılmış başlık.
Tüylerle süslü kalın bir şapka.
Kuşanana cesaret veren kaplan maskesi.
Dev palamut kabuğundan yapılmış hafif şapka.
Kuşanıldığında gücü artıran bir baş bandı.
Kaçınmayı artıran koyu renkli başlık.
Kaçınmayı artıran kabuk şapka.
Güç ve çevikliği artıran kan kırmızısı başlık.
Çoğu durum bozukluğunu geçersiz kılan kurdele.
Kraliyet ailesine ait zarif bir taç.
B.SAL'ı artıran keçe şapka.
B.SAL'ı artıran üç köşeli şapka.
B.SAL'ı artıran kedi biçimli başlık.
B.SAL'ı artıran defne tacı.
B.SAL'ı artıran geniş kenarlı sivri şapka.
B.SAL'ı artıran törensel şapka.
Zihni odaklayarak B.SAL'ı artıran taç.
Yıldırımı güçlendirip B.SAL'ı artıran şapka.
Büyülenmeyi geçersiz kılan ayrıntılı bir taç.
MP tüketimini azaltan altın toka.
Tüm başı koruyan bir miğfer.
İnce ama sağlam demir miğfer.
Mithrilden dövülmüş güzel bir miğfer.
Yggdrasil kabuğundan yapılmış miğfer.
Nadir orikalkum kaplı sağlam miğfer.
Adamant kabuktan yapılmış eşsiz miğfer.
Kadim bir savaşçı klanından kalma miğfer.
Kaçınmayı artıran kadim savaşçı miğferi.
Kristal parçalarından yapılmış güzel miğfer.
Rünlerle güçlendirilmiş kumaş zırh.
Kaçınmayı artıran dövüş sanatları giysisi.
Göğsü tamamen örten bir göğüslük.
Nadir mithrilden ayrıntılı göğüslük.
Kaçınmayı artıran sık dokunmuş yelek.
Gücü artıran gizemli bir kuşak.
Küçük metal plakalarla dikilmiş kumaş zırh.
Denizcilerin sevdiği kalın bir palto.
Adamant kabuktan yapılmış sağlam yelek.
Tecrübeli bir sanatçının kostümü.
Savaş başında fazladan 1 BP veren bir giysi.
Kristal parçalarıyla süslü yelek.
Kenevirden yapılmış kalın tunik.
B.SAL'ı artıran dökümlü ipek cübbe.
Zehri geçersiz kılan tüylü kedi giysisi.
B.SAL'ı artıran çiçek yapraklarından cübbe.
Zekâyı büyük ölçüde artıran gizemli cübbe.
İradeyi büyük ölçüde artıran mistik cübbe.
Toprak saldırılarını güçlendiren cübbe.
Işık saldırılarını güçlendiren mistik cübbe.
Şaşkınlığı geçersiz kılan parlak elbise.
İrade ve B.SAL'ı artıran asil cübbe.
Vestalleri kristalin ritmine uyumlar.
Cesur ve dikkat çekici bir kıyafet.
Tiz'in giydiği, görünümü sürekli değişen kıyafet.
Ringabel'in giydiği, görünümü sürekli değişen kıyafet.
Agnès'in giydiği, görünümü sürekli değişen kıyafet.
Edea'nın giydiği, görünümü sürekli değişen kıyafet.
Serbest Savaşçı görünümünü koruyan kıyafet.
Tabaklanmış deriden basit zırh.
Vücudun yarısını örten hafif zırh.
Demirden yapılmış tam plaka zırh.
Katmanlı mithrilden tam plaka zırh.
Yggdrasil kabuğundan büyülü zırh.
Nadir orikalkumdan gösterişli zırh.
Adamant kabuktan yapılmış tam vücut zırhı.
Kadim bir savaşçı klanından kalma zırh.
Gururlu bir savaşçı klanının kullandığı zırh.
Kristal parçalarından yapılmış zırh.
'''.strip().splitlines()

# These 277 strings match the first equipment-description block in the source table.
def equipment_desc_map(source_list):
    if len(_EQUIP)!=277:
        raise AssertionError(('equipment translation count',len(_EQUIP)))
    return dict(zip(source_list[:277],_EQUIP))

EL={'fire':'ateş','water':'su','lightning':'yıldırım','wind':'rüzgâr','earth':'toprak','light':'ışık','dark':'karanlık'}
AIL={'poison':'zehir','blind':'körlük','silence':'susturma','sleep':'uyku','dread':'dehşet'}
STAT={'P.Atk':'F.SAL','P.Def':'F.SAV','M.Atk':'B.SAL','M.Def':'B.SAV','strength':'güç','vitality':'dayanıklılık','intelligence':'zekâ','mind':'irade','agility':'çeviklik','dexterity':'beceri','speed':'hız','max HP':'Azami HP','max MP':'Azami MP'}

EXACT_DESC={
'Restores target’s HP and MP to full':'Hedefin HP ve MP’sini tamamen yeniler.',
'Restores the entire party’s HP and MP to full':'Tüm grubun HP ve MP’sini tamamen yeniler.',
'Cures a range of status ailments':'Çeşitli durum bozukluklarını giderir.',
'Raises a range of stats for the target':'Hedefin çeşitli statlarını artırır.',
'Doubles max HP and restores HP to full':'Azami HP’yi ikiye katlar ve HP’yi tamamen yeniler.',
'Lowers defense for 4 turns':'Savunmayı 4 tur düşürür.',
'Raises speed for 4 turns':'Hızı 4 tur artırır.',
'Boosts elemental attacks for 5 turns':'Element saldırılarını 5 tur güçlendirir.',
'Deals (your max HP - current HP) in damage':'Azami HP ile mevcut HP arasındaki fark kadar hasar verir.',
'Deals your current HP in damage to target':'Hedefe mevcut HP’n kadar hasar verir.',
'Nullifies a range of status ailments':'Çeşitli durum bozukluklarını geçersiz kılar.',
'A scroll that restores a few HP':'Az miktarda HP yenileyen bir parşömen.',
'A scroll that restores some HP':'Bir miktar HP yenileyen bir parşömen.',
'A scroll that restores a huge amount of HP':'Çok büyük miktarda HP yenileyen bir parşömen.',
'A scroll that restores a lot of HP':'Çok miktarda HP yenileyen bir parşömen.',
'A scroll for dungeon/battle escape':'Zindan veya savaştan kaçmayı sağlayan parşömen.',
'A tattered journal carried by Ringabel':'Ringabel’in taşıdığı yıpranmış günlük.',
'An hourglass received from an adventurer':'Bir maceracıdan alınan kum saati.',
'Thread needed to make the vestal garb':'Vestal giysisini yapmak için gereken iplik.',
'The pendant Agnès carries':'Agnès’in taşıdığı kolye.',
'Ceremonial garb for awakening crystals':'Kristalleri uyandırmak için gereken tören giysisi.',
'Profiteur’s oasis ambush orders':'Profiteur’ün vaha pususu emirleri.',
'Note to visit Grand Mill tower at night':'Gece Büyük Değirmen kulesine gitme notu.',
'A bikini from the sage’s collection':'Bilgenin koleksiyonundan bir bikini.',
'The orichalcum ore that Egil picked up':'Egil’in bulduğu orikalkum cevheri.',
'The baton of traveling bard Arca Pellar':'Gezgin ozan Arca Pellar’ın batonu.',
'A journal dropped by Alternis Dim':'Alternis Dim’in düşürdüğü günlük.',
'A key for opening locked chests':'Kilitli sandıkları açan anahtar.',
'The mark of an adventurer':'Bir maceracının işareti.',
}
JOB={'knight':'Şövalye','black mage':'Kara Büyücü','white mage':'Beyaz Büyücü','monk':'Keşiş','ranger':'Avcı','ninja':'Ninja','time mage':'Zaman Büyücüsü','spell fencer':'Büyü Kılıççısı','swordmaster':'Kılıç Ustası','pirate':'Korsan','dark knight':'Kara Şövalye','templar':'Tapınak Şövalyesi','vampire':'Vampir','arcanist':'Arkanist','summoner':'Çağırıcı','conjurer':'Büyü Ustası','valkyrie':'Valkür','spiritmaster':'Ruh Ustası','salve-maker':'İlaç Ustası','red mage':'Kızıl Büyücü','thief':'Hırsız','merchant':'Tüccar','performer':'Sanatçı'}

def translate_consumable_desc(s):
    if s in EXACT_DESC: return EXACT_DESC[s]
    m=re.fullmatch(r'A tonic that restores ([\d,]+) HP',s)
    if m:return f"{m.group(1)} HP yenileyen bir tonik."
    m=re.fullmatch(r'A tonic that restores ([\d,]+) MP',s)
    if m:return f"{m.group(1)} MP yenileyen bir tonik."
    if s=='A curative for poison':return 'Zehri gideren bir ilaç.'
    if s=='A mystical item that revives K.O.’d targets':return 'K.O. olmuş hedefleri dirilten mistik bir eşya.'
    if s=='Medicine that cures a range of status ailments':return 'Çeşitli durum bozukluklarını gideren ilaç.'
    if s=='A solution that cures blind':return 'Körlüğü gideren bir çözelti.'
    if s=='An herbal medicine that cures silence':return 'Susturmayı gideren bitkisel ilaç.'
    if s=='A bell that wakes the target from sleep':return 'Hedefi uykudan uyandıran bir çan.'
    if s=='An ointment that cures dread':return 'Dehşeti gideren bir merhem.'
    if s=='Ore that returns you to the dungeon entrance':return 'Seni zindan girişine döndüren bir cevher.'
    m=re.fullmatch(r'Deals (moderate|major) (fire|water|lightning|wind|earth) damage to party',s)
    if m:return f"Tüm gruba {'orta' if m.group(1)=='moderate' else 'yüksek'} {EL[m.group(2)]} hasarı verir."
    if s=='Applies stop effect to all in party':return 'Tüm gruba Stop etkisi uygular.'
    for eff,tr in [('comet','Comet'),('reflect','Reflect'),('aspir','Aspir'),('berserk','Çılgınlık'),('regen','Regen'),('reraise','Reraise')]:
        if s==f'Applies {eff} effect to target' or s==f'Applies {eff} to the target':return f'Hedefe {tr} etkisi uygular.'
    m=re.fullmatch(r'Material that raises (P\.Atk|P\.Def|M\.Atk|M\.Def)',s)
    if m:return f"{STAT[m.group(1)]} artıran malzeme."
    if s=='Material that boosts elemental vulnerability':return 'Element zayıflığını artıran malzeme.'
    if s=='Material that boosts elemental resistance':return 'Element direncini artıran malzeme.'
    if s=='Material that contains a dragon’s power':return 'Ejder gücü taşıyan malzeme.'
    m=re.fullmatch(r'Material imbued with the power of (fire|water|wind|lightning|earth|light|dark)',s)
    if m:return f"{EL[m.group(1)].capitalize()} gücü taşıyan malzeme."
    m=re.fullmatch(r'Cures (poison|blind|silence|sleep|dread) and restores 150 HP',s)
    if m:return f"{AIL[m.group(1)].capitalize()} etkisini giderir ve 150 HP yeniler."
    if s=='Revives target from K.O. and restores 5000 HP':return 'Hedefi K.O.’dan diriltir ve 5.000 HP yeniler.'
    if s=='Revives target from K.O. and restores HP/MP':return 'Hedefi K.O.’dan diriltir ve HP/MP yeniler.'
    if s=='Causes minor damage and taunts the target':return 'Az hasar verir ve hedefi tahrik eder.'
    m=re.fullmatch(r'Makes target immune to (poison|blind|silence|sleep|dread)',s)
    if m:return f"Hedefi {AIL[m.group(1)]} etkisine karşı bağışık kılar."
    m=re.fullmatch(r'Restores ([\d,]+) HP and ([\d,]+) MP',s)
    if m:return f"{m.group(1)} HP ve {m.group(2)} MP yeniler."
    m=re.fullmatch(r'Restores ([\d,]+) (HP|MP)',s)
    if m:return f"{m.group(1)} {m.group(2)} yeniler."
    m=re.fullmatch(r'Raises (P\.Atk|P\.Def|M\.Atk|M\.Def) by (\d+)% for (\d+) turns',s)
    if m:return f"{STAT[m.group(1)]} {m.group(3)} tur boyunca %{m.group(2)} artırır."
    m=re.fullmatch(r'Makes target vulnerable to (fire|water|wind|lightning|earth|light|dark)',s)
    if m:return f"Hedefi {EL[m.group(1)]} hasarına karşı zayıf kılar."
    m=re.fullmatch(r'Makes target immune to (fire|water|wind|lightning|earth|light|dark) damage',s)
    if m:return f"Hedefi {EL[m.group(1)]} hasarına karşı bağışık kılar."
    m=re.fullmatch(r'Deals ([\d,]+) (light|dark) damage to (all|target)',s)
    if m:return f"{'Tüm hedeflere' if m.group(3)=='all' else 'Hedefe'} {m.group(1)} {EL[m.group(2)]} hasarı verir."
    m=re.fullmatch(r'Raises target’s BP by (\d+); ([\d,]+) pg',s)
    if m:return f"{m.group(2)} pg karşılığında hedefin BP’sini {m.group(1)} artırır."
    m=re.fullmatch(r'Raises (max HP|max MP|strength|vitality|intelligence|mind|agility|dexterity)',s)
    if m:return f"{STAT[m.group(1)].capitalize()} değerini artırır."
    m=re.fullmatch(r'Deals ([\d,]+) (HP|MP) damage and poisons target',s)
    if m:return f"Hedefe {m.group(1)} {m.group(2)} hasarı verir ve zehirler."
    if s=='Deals major damage to HP/MP, poisons target':return 'Hedefin HP/MP’sine yüksek hasar verir ve zehirler.'
    if s=='Deals major damage to party’s HP/MP, poisons':return 'Grubun HP/MP’sine yüksek hasar verir ve zehirler.'
    if s=='Nullifies poison':return 'Zehri geçersiz kılar.'
    if s=='Nullifies death':return 'Ölümü geçersiz kılar.'
    for e,tr in AIL.items():
        if s==f'Nullifies {e}':return f'{tr.capitalize()} etkisini geçersiz kılar.'
    m=re.fullmatch(r'Restores ([\d,]+) HP; ([\d,]+) pg',s)
    if m:return f"{m.group(2)} pg karşılığında {m.group(1)} HP yeniler."
    m=re.fullmatch(r'Restores ([\d,]+) MP; ([\d,]+) pg',s)
    if m:return f"{m.group(2)} pg karşılığında {m.group(1)} MP yeniler."
    if s=='Revives from K.O.; 100 pg':return '100 pg karşılığında K.O.’dan diriltir.'
    if s=='Cures a range of status ailments; 500 pg':return '500 pg karşılığında çeşitli durum bozukluklarını giderir.'
    if s.startswith('A scroll that '):
        body=s[len('A scroll that '):]
        fixed={
        'cures poison':'Zehri gideren bir parşömen.','inflicts silence':'Susturma etkisi veren bir parşömen.','raises P.Def':'F.SAV’ı artıran bir parşömen.','deals minor wind damage':'Az rüzgâr hasarı veren bir parşömen.','revives target from K.O.':'Hedefi K.O.’dan dirilten bir parşömen.','dealing moderate wind damage':'Orta rüzgâr hasarı veren bir parşömen.','raises M.Def':'B.SAV’ı artıran bir parşömen.','cures a range of status ailments':'Çeşitli durum bozukluklarını gideren bir parşömen.','casts a magic-reflecting barrier':'Büyü yansıtan bariyer kuran bir parşömen.','deals major wind damage':'Yüksek rüzgâr hasarı veren bir parşömen.','revives from K.O. with full HP':'Tam HP ile K.O.’dan dirilten bir parşömen.','deals light damage':'Işık hasarı veren bir parşömen.','removes magic and support effects':'Büyü ve destek etkilerini kaldıran bir parşömen.','cures blind':'Körlüğü gideren bir parşömen.','cures the party’s status ailments':'Grubun durum bozukluklarını gideren bir parşömen.','deals minor fire damage':'Az ateş hasarı veren bir parşömen.','deals minor water damage':'Az su hasarı veren bir parşömen.','deals minor lightning damage':'Az yıldırım hasarı veren bir parşömen.','inflicts poison':'Zehir etkisi veren bir parşömen.','puts the target to sleep':'Hedefi uyutan bir parşömen.','deals minor earth damage':'Az toprak hasarı veren bir parşömen.','deals moderate fire damage':'Orta ateş hasarı veren bir parşömen.','deals moderate water damage':'Orta su hasarı veren bir parşömen.','deals moderate lightning damage':'Orta yıldırım hasarı veren bir parşömen.','absorbs the target’s HP':'Hedefin HP’sini emen bir parşömen.','inflicts dread':'Dehşet etkisi veren bir parşömen.','deals moderate earth damage':'Orta toprak hasarı veren bir parşömen.','deals major fire damage':'Yüksek ateş hasarı veren bir parşömen.','deals major water damage':'Yüksek su hasarı veren bir parşömen.','deals major lightning damage':'Yüksek yıldırım hasarı veren bir parşömen.','inflicts death':'Ölüm etkisi veren bir parşömen.','deals major earth damage':'Yüksek toprak hasarı veren bir parşömen.','absorbs the target’s MP':'Hedefin MP’sini emen bir parşömen.','deals major dark damage':'Yüksek karanlık hasarı veren bir parşömen.','wipes out weaker foes':'Zayıf düşmanları yok eden bir parşömen.','lowers the target’s speed':'Hedefin hızını düşüren bir parşömen.','gradually restores HP':'HP’yi zamanla yenileyen bir parşömen.','raises the target’s speed':'Hedefin hızını artıran bir parşömen.','deals half of max HP as damage':'Azami HP’nin yarısı kadar hasar veren bir parşömen.','raises evasion':'Kaçınmayı artıran bir parşömen.','lowers the party’s speed':'Grubun hızını düşüren bir parşömen.','raises the party’s speed':'Grubun hızını artıran bir parşömen.','raises the party’s evasion':'Grubun kaçınmasını artıran bir parşömen.','does random, non-elemental damage':'Rastgele elementsiz hasar veren bir parşömen.','raises hit count':'Vuruş sayısını artıran bir parşömen.','immobilizes target for a few turns':'Hedefi birkaç tur hareketsiz bırakan bir parşömen.','deals 3/4 of max HP as damage':'Azami HP’nin 3/4’ü kadar hasar veren bir parşömen.','auto-triggers raise after K.O.':'K.O. sonrası otomatik Raise yapan bir parşömen.','deals 4 random, non-elemental hits':'Rastgele 4 elementsiz vuruş yapan bir parşömen.'}
        if body in fixed:return fixed[body]
        if body.startswith('teaches '):return f"{body[8:]} öğreten bir parşömen."
    m=re.fullmatch(r'The asterisk for the (.+) job',s)
    if m and m.group(1) in JOB:return f"{JOB[m.group(1)]} mesleğinin asteriski."
    return None
# Late exacts kept separate so the source list remains easy to audit.
EXACT_DESC.update({
'Cures poison':'Zehri giderir.','Revives target from K.O.':'Hedefi K.O.’dan diriltir.','Cures blind':'Körlüğü giderir.','Cures silence':'Susturmayı giderir.','Cures sleep':'Uykuyu giderir.','Cures dread':'Dehşeti giderir.','Restores HP and MP to full':'HP ve MP’yi tamamen yeniler.','Restores party’s HP and MP to full':'Grubun HP ve MP’sini tamamen yeniler.','A scroll dealing moderate wind damage':'Orta rüzgâr hasarı veren bir parşömen.'
})
