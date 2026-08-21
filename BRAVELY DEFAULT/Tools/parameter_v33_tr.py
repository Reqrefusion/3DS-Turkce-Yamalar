# -*- coding: utf-8 -*-
"""Conservative structured-table translator for v3.3.
Only returns a translation when the source matches a gameplay-description pattern or an exact curated string.
"""
import re, textwrap

ELEMENT={'fire':'ateş','water':'su','lightning':'yıldırım','wind':'rüzgâr','earth':'toprak','light':'ışık','dark':'karanlık'}
STAT={'strength':'gücünü','intelligence':'zekâsını','mind':'iradesini','agility':'çevikliğini','dexterity':'becerisini','P.Atk':'fiziksel saldırısını','P.Def':'fiziksel savunmasını','M.Atk':'büyü saldırısını','M.Def':'büyü savunmasını','Max HP':'Azami HP’sini','Max MP':'Azami MP’sini'}
MONSTER={'beast':'yaratık','aquatic':'sucul','undead':'ölümsüz','demonkind':'iblis','humanoid':'insansı','dragonkind':'ejder','flier':'uçan'}
AILMENT={'poison':'zehir','blind':'körlük','silence':'sessizlik','sleep':'uyku','paralyze':'felç','dread':'korku','confuse':'kafa karışıklığı','charm':'cazibe','berserk':'çılgınlık','death':'ölüm'}
JOB={'arcanist':'Arkanist','black mage':'Kara Büyücü','conjurer':'Büyü Ustası','knight':'Şövalye','merchant':'Tüccar','monk':'Keşiş','ninja':'Ninja','performer':'Sanatçı','pirate':'Korsan','ranger':'Avcı','red mage':'Kızıl Büyücü','salve-maker':'İlaç Ustası','spell fencer':'Büyü Kılıççısı','spiritmaster':'Ruh Ustası','summoner':'Çağırıcı','swordmaster':'Kılıç Ustası','templar':'Tapınak Şövalyesi','thief':'Hırsız','time mage':'Zaman Büyücüsü','valkyrie':'Valkür','vampire':'Vampir','white mage':'Beyaz Büyücü'}

def _wrap_like(src,tr):
    if '\n' not in src: return tr
    src_lines=src.split('\n'); n=len(src_lines)
    # Preserve intentional paragraph breaks for the few long descriptions.
    if '' in src_lines:
        paras=tr.split('\n\n')
        if len(paras)>1:
            return '\n\n'.join(_wrap_like('X\nX',p) for p in paras)
    width=max(18,max(len(x) for x in src_lines))
    words=tr.split()
    if not words: return tr
    lines=[]; cur=''
    for w in words:
        cand=w if not cur else cur+' '+w
        if len(cand)<=width or not cur:
            cur=cand
        else:
            lines.append(cur); cur=w
    if cur: lines.append(cur)
    # If wrapping creates too many lines, rebalance to the original line count using a wider cap.
    if len(lines)>n:
        target=max(width, (len(tr)+n-1)//n + 4)
        lines=[]; cur=''
        for w in words:
            cand=w if not cur else cur+' '+w
            if len(cand)<=target or not cur: cur=cand
            else: lines.append(cur); cur=w
        if cur: lines.append(cur)
    return '\n'.join(lines)

def _clean(s): return ' '.join(s.replace('\n',' ').split())

def _finish(src,tr): return _wrap_like(src,tr)

EXACT={
'A blade given to Edea by her master for her first campaign.':'Edea’ya ilk seferi için ustası tarafından verilen bir kılıç.',
'A journal dropped by Alternis Dim.':'Alternis Dim’in düşürdüğü bir günlük.',
'A key for opening locked chests.':'Kilitli sandıkları açan bir anahtar.',
'A note with instructions to visit the Grand Mill tower at night.':'Gece Büyük Değirmen kulesine gitme talimatlarını içeren bir not.',
'A tattered journal carried by Ringabel.':'Ringabel’in taşıdığı yıpranmış bir günlük.',
'Orders written by Chairman Profiteur to ambush visitors to the oasis.':'Başkan Profiteur’ün vahaya gelenlere pusu kurma emri.',
'Rainbow-colored thread needed to make the vestal garb.':'Vestal cübbesini yapmak için gereken gökkuşağı renkli iplik.',
'The baton of traveling bard Arca Pellar.':'Gezgin ozan Arca Pellar’ın batonu.',
'The ceremonial garb needed to awaken a crystal.':'Bir kristali uyandırmak için gereken tören cübbesi.',
'The mark of an adventurer.':'Bir maceracının işareti.',
'The orichalcum ore that Egil picked up.':'Egil’in bulduğu orikalkum cevheri.',
'The pendant Agnès carries.':'Agnès’in taşıdığı kolye.',
'Returns you to the dungeon entrance.':'Seni zindanın girişine döndürür.',
'Raises a range of stats for the target.':'Hedefin çeşitli statlarını artırır.',
'Reflect is cast upon wearer at the start of battle.':'Savaş başında kuşanana Reflect uygulanır.',
'Wearer’s chance of being targeted by enemies remains constant.':'Kuşananın düşmanlarca hedef alınma olasılığı sabit kalır.',
'Doubles the wearer’s chance to succeed at thievery.':'Kuşananın hırsızlıkta başarılı olma şansını ikiye katlar.',
'Gives the wearer 1 extra BP at the start of battle.':'Savaş başında kuşanana fazladan 1 BP verir.',
'Lowers the wearer’s MP consumption by 25%.':'Kuşananın MP tüketimini %25 azaltır.',
'Lowers the chance of encountering enemies. Effect does not stack.':'Düşmanla karşılaşma olasılığını azaltır. Etki birikmez.',
'Doubles the chance of encountering enemies. Effects from the same item do not stack.':'Düşmanla karşılaşma olasılığını ikiye katlar. Aynı eşyadan gelen etkiler birikmez.',
'Doubles EXP and JP received. No pg will be received.':'Kazanılan EXP ve JP’yi ikiye katlar. pg kazanılmaz.',
'Doubles pg received. No EXP or JP will be received.':'Kazanılan pg’yi ikiye katlar. EXP veya JP kazanılmaz.',
'Doubles the chance to be targeted by enemies (the factor affected by the wearer’s actions).':'Düşmanlarca hedef alınma olasılığını ikiye katlar (kuşananın eylemlerinden etkilenen değer).',
'Does double damage when attacking multiple enemies at once.':'Birden fazla düşmana aynı anda saldırırken iki kat hasar verir.',
'Special clothing that allows the wearer to retain the freelancer’s look while taking on a job.':'Bir mesleğe geçerken Serbest Savaşçı görünümünü korumayı sağlayan özel kıyafet.',
'Casts random black magic when used as an item.':'Eşya olarak kullanıldığında rastgele Kara Büyü yapar.',
'Casts quick when used as an item.':'Eşya olarak kullanıldığında Quick yapar.',
'Applies comet effect to target.':'Hedefe Comet etkisi uygular.',
'Applies reflect effect to target.':'Hedefe Reflect etkisi uygular.',
'Applies aspir effect to target.':'Hedefe Aspir etkisi uygular.',
}

SCROLL={
'restores a few HP to the target':'hedefin az miktarda HP’sini yeniler',
'restores some HP to the target':'hedefin bir miktar HP’sini yeniler',
'restores a lot of HP to the target':'hedefin çok miktarda HP’sini yeniler',
'restores a huge amount of HP to the target':'hedefin çok büyük miktarda HP’sini yeniler',
'cures the target of poison':'hedefin zehrini giderir',
'cures the target of blind':'hedefin körlüğünü giderir',
'cures the target of a range of ailments':'hedefin çeşitli durum bozukluklarını giderir',
'inflicts Silence upon the target':'hedefe Sessizlik uygular',
'inflicts poison upon the target':'hedefe zehir uygular',
'puts the target to sleep':'hedefi uyutur',
'inflicts dread upon the target':'hedefe korku uygular',
'inflicts death upon the target':'hedefe ölüm etkisi uygular',
'wipes out weaker foes':'zayıf düşmanları yok eder',
'lets you escape from a dungeon or battle':'zindandan veya savaştan kaçmanı sağlar',
'lowers the Speed of an entire party':'tüm grubun Hızını düşürür',
'raises the Speed of an entire party':'tüm grubun Hızını artırır',
'raises party Evasion':'grubun Kaçınmasını artırır',
'raises the Hit Count of the target':'hedefin İsabet Sayısını artırır',
'immobilizes the target for a few turns':'hedefi birkaç tur hareketsiz bırakır',
'casts Raise automatically after a K.O.':'K.O. sonrası otomatik Raise yapar',
'inflicts 4 non-elemental attacks on random targets':'rastgele hedeflere 4 elementsiz saldırı yapar',
'revives the target from K.O.':'hedefi K.O.’dan diriltir',
'revives the target from K.O. and restores all HP':'hedefi K.O.’dan diriltir ve tüm HP’sini yeniler',
'casts a magic-reflecting barrier around the target':'hedefin çevresine büyü yansıtan bir bariyer kurar',
'removes various magic and support effects from the target':'hedeften çeşitli büyü ve destek etkilerini kaldırır',
'cures the party of status ailments':'grubun durum bozukluklarını giderir',
}

def translate_parameter_text(src):
    s=_clean(src)
    if s in EXACT: return _finish(src,EXACT[s])
    m=re.fullmatch(r'The asterisk for the (.+) job\.',s)
    if m and m.group(1) in JOB: return _finish(src,f"{JOB[m.group(1)]} mesleğinin asteriski.")
    m=re.fullmatch(r'Weapon attacks deal (fire|water|lightning|wind|earth|light|dark) damage\.',s)
    if m: return _finish(src,f"Silah saldırıları {ELEMENT[m.group(1)]} hasarı verir.")
    m=re.fullmatch(r'(?:Does|Deals) (\d+)% more damage to (beast|aquatic|undead|demonkind|humanoid|dragonkind|flier) monsters\.',s)
    if m: return _finish(src,f"{MONSTER[m.group(2)].capitalize()} türü canavarlara %{m.group(1)} daha fazla hasar verir.")
    m=re.fullmatch(r'(?:Does|Deals) (\d+)% more damage when jumping\.',s)
    if m: return _finish(src,f"Zıplama saldırılarında %{m.group(1)} daha fazla hasar verir.")
    m=re.fullmatch(r'Raises the (wielder|wearer)’s (Max HP|Max MP|P\.Atk|P\.Def|M\.Atk|M\.Def|strength|intelligence|mind|agility|dexterity) by (\d+)\.',s)
    if m:
        who='Kullananın' if m.group(1)=='wielder' else 'Kuşananın'
        return _finish(src,f"{who} {STAT[m.group(2)]} {m.group(3)} artırır.")
    m=re.fullmatch(r'Makes the wearer immune to (poison|blind|silence|sleep|paralyze|dread|confuse|charm)\.',s)
    if m: return _finish(src,f"Kuşananı {AILMENT[m.group(1)]} etkisine karşı bağışık kılar.")
    m=re.fullmatch(r'Makes the wearer immune to (fire|water|lightning|wind|earth|light|dark) damage\.',s)
    if m: return _finish(src,f"Kuşananı {ELEMENT[m.group(1)]} hasarına karşı bağışık kılar.")
    m=re.fullmatch(r'Protects the (wearer|wielder) by reducing (fire|water|lightning|wind|earth|light|dark) damage by half\.',s)
    if m: return _finish(src,f"{ELEMENT[m.group(2)].capitalize()} hasarını yarıya indirerek {'kuşananı' if m.group(1)=='wearer' else 'kullananı'} korur.")
    m=re.fullmatch(r'Enhances the (wearer|wielder)’s (fire|water|lightning|wind|earth|light|dark) attacks to do (\d+)% more damage\.',s)
    if m: return _finish(src,f"{'Kuşananın' if m.group(1)=='wearer' else 'Kullananın'} {ELEMENT[m.group(2)]} saldırılarının hasarını %{m.group(3)} artırır.")
    m=re.fullmatch(r'Triggers the ([A-Za-z -]+) effect when used as an item\.',s,re.I)
    if m: return _finish(src,f"Eşya olarak kullanıldığında {m.group(1).strip()} etkisini tetikler.")
    m=re.fullmatch(r'Has a (\d+)% chance to poison the attack target\.',s)
    if m: return _finish(src,f"Saldırı hedefini %{m.group(1)} olasılıkla zehirler.")
    m=re.fullmatch(r'Has a (\d+)% chance to inflict blind on the attack target\.',s)
    if m: return _finish(src,f"Saldırı hedefine %{m.group(1)} olasılıkla körlük uygular.")
    m=re.fullmatch(r'Has a (\d+)% chance to (charm|confuse|paralyze|silence) the attack target\.',s)
    if m:
        act={'charm':'büyüler','confuse':'şaşırtır','paralyze':'felç eder','silence':'susturur'}[m.group(2)]
        return _finish(src,f"Saldırı hedefini %{m.group(1)} olasılıkla {act}.")
    m=re.fullmatch(r'Has a (\d+)% chance to put the attack target to sleep\.',s)
    if m: return _finish(src,f"Saldırı hedefini %{m.group(1)} olasılıkla uyutur.")
    m=re.fullmatch(r'Has a (\d+)% chance to instill dread in the attack target\.',s)
    if m: return _finish(src,f"Saldırı hedefine %{m.group(1)} olasılıkla korku salar.")
    m=re.fullmatch(r'Has a (\d+)% chance to drive the attack target berserk\.',s)
    if m: return _finish(src,f"Saldırı hedefini %{m.group(1)} olasılıkla çılgına çevirir.")
    m=re.fullmatch(r'Has a (\d+)% chance to inflict death on the attack target\.',s)
    if m: return _finish(src,f"Saldırı hedefine %{m.group(1)} olasılıkla ölüm etkisi uygular.")
    m=re.fullmatch(r'Material imbued with the power of (fire|water|lightning|wind|earth|light|dark)\. Can be used for compounding\.',s)
    if m: return _finish(src,f"{ELEMENT[m.group(1)].capitalize()} gücüyle yüklü malzeme. Bileşimde kullanılabilir.")
    m=re.fullmatch(r'Material that raises (P\.Atk|P\.Def|M\.Atk|M\.Def)\. Can be used for compounding\.',s)
    if m:
        nm={'P.Atk':'F.Sal','P.Def':'F.Sav','M.Atk':'B.Sal','M.Def':'B.Sav'}[m.group(1)]
        return _finish(src,f"{nm} artıran malzeme. Bileşimde kullanılabilir.")
    if s=='Material that increases vulnerability to elemental attacks. Can be used for compounding.': return _finish(src,'Element saldırılarına karşı zayıflığı artıran malzeme. Bileşimde kullanılabilir.')
    if s=='Material that increases resistance to elemental attacks. Can be used for compounding.': return _finish(src,'Element saldırılarına direnci artıran malzeme. Bileşimde kullanılabilir.')
    if s=='Material that is the source of a dragon’s great power. Can be used for compounding.': return _finish(src,'Bir ejderhanın büyük gücünün kaynağı olan malzeme. Bileşimde kullanılabilir.')
    m=re.fullmatch(r'A scroll that (.+)\.',s)
    if m:
        body=m.group(1)
        if body in SCROLL: return _finish(src,'Hedefe kullanılan bir parşömen; '+SCROLL[body]+'.')
        if body.startswith('teaches '): return _finish(src,body[8:]+' öğreten bir parşömen.')
    m=re.fullmatch(r'Attacks an entire party with (fire|water|lightning|wind|earth), dealing (\d+) damage each\.',s)
    if m: return _finish(src,f"Tüm gruba {ELEMENT[m.group(1)]} saldırısı yapar; her birine {m.group(2)} hasar verir.")
    m=re.fullmatch(r'Cures the target of (poison|blind|silence|sleep|dread)\.',s)
    if m: return _finish(src,f"Hedefin {AILMENT[m.group(1)]} durumunu giderir.")
    if s=='Cures the target of poison, blind, silence, sleep, paralyze, dread, berserk, confuse, and charm.': return _finish(src,'Hedefin zehir, körlük, sessizlik, uyku, felç, korku, çılgınlık, kafa karışıklığı ve cazibe durumlarını giderir.')
    m=re.fullmatch(r'Restores (\d+) HP to the target\. Deals the same amount of damage when used on undead enemies\.',s)
    if m: return _finish(src,f"Hedefe {m.group(1)} HP yeniler. Ölümsüz düşmanlara kullanıldığında aynı miktarda hasar verir.")
    m=re.fullmatch(r'Restores (\d+) MP to the target\. Reduces MP by an equal amount when used on undead enemies\.',s)
    if m: return _finish(src,f"Hedefe {m.group(1)} MP yeniler. Ölümsüz düşmanlarda aynı miktarda MP azaltır.")
    if s=='Revives K.O. targets. Has a 70% chance to cause death when used on undead enemies.': return _finish(src,'K.O. hedefleri diriltir. Ölümsüz düşmanlarda %70 olasılıkla ölüm etkisi oluşturur.')
    m=re.fullmatch(r'Can only be worn by (Tiz|Ringabel|Edea)\. The appearance of this special outfit changes over time\.',s)
    if m: return _finish(src,f"Yalnızca {m.group(1)} kuşanabilir. Bu özel kıyafetin görünümü zamanla değişir.")
    if s=='Makes the wearer immune to fire and water damage.': return _finish(src,'Kuşananı ateş ve su hasarına karşı bağışık kılar.')
    if s=='Makes the wearer immune to poison, blind, silence, sleep, paralyze, dread, confuse, charm, and death.': return _finish(src,'Kuşananı zehir, körlük, sessizlik, uyku, felç, korku, kafa karışıklığı, cazibe ve ölüm etkilerine karşı bağışık kılar.')
    if s=='Raises the wearer’s strength by 5. Raises the wearer’s agility by 5.': return _finish(src,'Kuşananın gücünü 5, çevikliğini 5 artırır.')
    if s=='Raises the wearer’s strength by 10. Lowers the wearer’s dexterity by 50.': return _finish(src,'Kuşananın gücünü 10 artırır, becerisini 50 azaltır.')
    if s=='Raises allies’ chance of getting the first strike by 10%.': return _finish(src,'Müttefiklerin ilk saldırıyı yapma şansını %10 artırır.')
    if s=='Lowers the enemy’s chance of getting the first strike by 10%.': return _finish(src,'Düşmanın ilk saldırıyı yapma şansını %10 azaltır.')
    if s=='Raises the Brave Attack rate of allies by 10%.': return _finish(src,'Müttefiklerin Brave Attack oranını %10 artırır.')
    if s=='Lowers the Brave Attack rate of enemies by 10%.': return _finish(src,'Düşmanların Brave Attack oranını %10 azaltır.')
    return None

# Multi-effect and long descriptions that are clearer as curated exact translations.
EXACT.update({
'Does 50% more damage to aquatic monsters. Also does 25% more damage when attacking multiple enemies at once.':'Sucul canavarlara %50, birden fazla düşmana aynı anda saldırırken ayrıca %25 daha fazla hasar verir.',
'Does 50% more damage to undead monsters. Also does 25% more damage when attacking multiple enemies at once.':'Ölümsüz canavarlara %50, birden fazla düşmana aynı anda saldırırken ayrıca %25 daha fazla hasar verir.',
'Deals 50% more damage to demonkind and flier monsters.':'İblis ve uçan türü canavarlara %50 daha fazla hasar verir.',
'Has a 100% chance to apply the berserk effect to target.':'Hedefe %100 olasılıkla çılgınlık etkisi uygular.',
'Has a 25% chance to charm the attack target. Deals 50% more damage to flier monsters.':'Saldırı hedefini %25 olasılıkla büyüler. Uçan canavarlara %50 daha fazla hasar verir.',
'Has a 25% chance to confuse the attack target. Deals 50% more damage to flier monsters.':'Saldırı hedefini %25 olasılıkla şaşırtır. Uçan canavarlara %50 daha fazla hasar verir.',
'Has a 25% chance to inflict death on the attack target. Deals 50% more damage to flier monsters.':'Saldırı hedefine %25 olasılıkla ölüm etkisi uygular. Uçan canavarlara %50 daha fazla hasar verir.',
'Has a 25% chance to paralyze the attack target. Deals 50% more damage to flier monsters.':'Saldırı hedefini %25 olasılıkla felç eder. Uçan canavarlara %50 daha fazla hasar verir.',
'Has a 25% chance to silence the attack target. Deals 50% more damage to flier monsters.':'Saldırı hedefini %25 olasılıkla susturur. Uçan canavarlara %50 daha fazla hasar verir.',
'Has a 30% chance to poison the attack target. Deals 50% more damage to flier monsters.':'Saldırı hedefini %30 olasılıkla zehirler. Uçan canavarlara %50 daha fazla hasar verir.',
'Has a 75% chance to apply the stop effect to each member of a party.':'Bir grubun her üyesine %75 olasılıkla Stop etkisi uygular.',
'Makes the wearer immune to death effects.':'Kuşananı ölüm etkilerine karşı bağışık kılar.',
'Raises the wielder’s M.Def by 19. Does 25% more damage when attacking multiple enemies at once.':'Kullananın büyü savunmasını 19 artırır. Birden fazla düşmana aynı anda saldırırken %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 1. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 1 artırır. Birden fazla düşmana aynı anda saldırırken %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 2. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 2 artırır. Birden fazla düşmana aynı anda saldırırken %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 3. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 3 artırır. Birden fazla düşmana aynı anda saldırırken %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 4. Triggers the raise effect when used as an item. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 4 artırır. Eşya olarak kullanıldığında Raise tetikler. Çoklu hedeflere %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 5. Triggers the cure effect when used as an item. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 5 artırır. Eşya olarak kullanıldığında Cure tetikler. Çoklu hedeflere %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 6. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 6 artırır. Birden fazla düşmana aynı anda saldırırken %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 6. Enhances the wielder’s wind attacks to do 20% more damage. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 6 artırır, rüzgâr hasarını %20 güçlendirir. Çoklu hedeflere %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 7. Triggers the esuna effect when used as an item. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 7 artırır. Eşya olarak kullanıldığında Esuna tetikler. Çoklu hedeflere %25 daha fazla hasar verir.',
'Raises the wielder’s mind by 8. Weapon attacks deal dark damage. Does 25% more damage when attacking multiple enemies at once.':'Kullananın iradesini 8 artırır. Silah saldırıları karanlık hasarı verir. Çoklu hedeflere %25 daha fazla hasar verir.',
'Restores the HP and MP of all allies to full. Restores up to 9999 HP and 999 MP when not using Bravely Second.':'Tüm müttefiklerin HP ve MP’sini tamamen yeniler. Bravely Second kullanılmıyorsa en fazla 9999 HP ve 999 MP yeniler.',
'Restores the HP and MP of the target to full. Reduces HP and MP by the same amount when used on undead enemies. Restores up to 9999 HP and 999 MP when not using Bravely Second.':'Hedefin HP ve MP’sini tamamen yeniler. Ölümsüz düşmanlarda aynı miktarda HP ve MP azaltır. Bravely Second yokken en fazla 9999 HP ve 999 MP yeniler.',
'Triggers the haste effect when used as an item. Deals 50% more damage to flier monsters.':'Eşya olarak kullanıldığında Haste tetikler. Uçan canavarlara %50 daha fazla hasar verir.',
'Triggers the sword magic drain when used as an item.':'Eşya olarak kullanıldığında kılıç büyüsü Drain tetikler.',
'Weapon attacks deal light damage. Does 25% more damage when attacking multiple enemies at once.':'Silah saldırıları ışık hasarı verir. Birden fazla düşmana aynı anda saldırırken %25 daha fazla hasar verir.',
'Weapon attacks deal lightning damage. Does 25% more damage when attacking multiple enemies at once.':'Silah saldırıları yıldırım hasarı verir. Birden fazla düşmana aynı anda saldırırken %25 daha fazla hasar verir.',
'Weapon attacks deal lightning damage. Makes the wielder immune to lightning damage.':'Silah saldırıları yıldırım hasarı verir ve kullananı yıldırım hasarına karşı bağışık kılar.',
'A scroll that casts Raise automatically after a K.O.':'K.O. sonrası otomatik Raise yapan bir parşömen.',
'A scroll that revives the target from K.O.':'Hedefi K.O.’dan dirilten bir parşömen.',
})
