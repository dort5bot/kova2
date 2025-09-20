🔍telegram botta yapılması planlanan işler
Excel işleme + gruplama + mail gönderme işini hem modüler, hem de yüksek performanslı bir Telegram bot yapısı planlanıyor
iş için performans, CPU kullanımı, bellek tasarrufu ve genel verimlilik yüksek olacak


🔍Genel Mimari
handlers/ → Telegram komutlarını ve dosya yüklemeyi alır.
utils/ → Excel düzenleme, gruplama, mail gönderme fonksiyonları burada.
jobs/ → Arka plan görevleri (dosya işleme, mail atma gibi ağır işler için).
data/ → Geçici dosyalar, loglar, grup tanımları.


🔍Excel İşleme (Performans & Bellek)
Pandas yerine openpyxl veya xlsxwriter kullan:
işin “hesaplama” değil, “satır düzenleme + kopyalama”. Pandas büyük dosyalarda RAM’i şişirir. openpyxl satır-satır işleme yapabildiği için daha CPU ve bellek dostu.
Satırları chunk halinde işle (örneğin 500–1000 satır bir defada). Böylece büyük dosyalarda bellek tasarrufu olur.
“Grup eşleşmesi” için illeri set() yapısında tut → O(1) arama süresi → CPU’ya çok hafif yük.


🔍Dosya Ayırma & Kitap Oluşturma
Eşleşme sırasında dosya önceden açılmasın, satır bulununca ilgili kitaba yazılsın.
“Lazy create” mantığı: Eğer o grup için ilk kez satır gelirse, kitap açılır. (Sen zaten bunu yazmışsın → çok doğru, CPU tasarruflu).
En sonda bütün dosyalar tek seferde kaydedilir → I/O yazma yükü azalır.


🔍Dosya Adlandırma & Yönetim
Dosya isimlerini grup_name or grup_no + datetime.now().strftime("%m%d_%H%M") ile oluştur.
Gruplar klasör bazlı ayrılsın (/data/output/grup_1/...).
Bellek yükünü azaltmak için işlem bitince wb.close() ile dosya kapanmalı.

🔍Mail Gönderme
Dosyalar geçici dizine kaydedilsin,
Mail gönderiminde async SMTP veya queue sistemi kullan (ör. aiosmtplib veya celery + redis).
→ Böylece ana bot CPU yüklenmez, mail işi arka planda çözülür.


🔍Denetlemek için
Başlık Doğrulama:
Dosyada "TARİH" ve "İL" sütunlarının olup olmadığını kontrol et.
Yoksa işlem başlamadan hata mesajı ver → ❌ Dosyada TARİH veya İL sütunu bulunamadı.

Boş Satır / Sütun Kontrolü:
İlk satırda tüm sütun adları boş mu, satırlar eksik mi kontrol et.

Sütun Düzeni Doğrulama:
Düzenlenen dosyada "TARİH" mutlaka A sütunu, "İL" mutlaka B sütunu olmalı.
→ Kod içinde assert df.columns[0] == "TARİH" gibi kontrol eklenebilir.

Satır Taraması & Eşleşme:
Her satır tarandığında →
Hangi gruba yazıldığını (veya Grup_0’a düştüğünü) logla.

Çalışma Kitabı Kontrolü:
Kaç grup dosyası oluştu?
Kaç satır toplam işlendi?
Girdi satır sayısı = çıktı satırlarının toplamı mı?


🔍İŞLEM BİTTİĞİNDE ÖRNEK RAPOR
✅ Dosya işlendi.
Toplam satır: 500
Eşleşen satır: 480
Eşleşmeyen satır: 20

Oluşan dosyalar:
- NURHAN-0916_1621.xlsx (120 satır)
- MAHMUTBEY-0916_1621.xlsx (200 satır)
- Grup_0-0916_1621.xlsx (20 satır)

📧 Mail gönderildi: 3 alıcıya


🔍Mail Gönderim Kontrolü
Mail kuyruğu loglansın →
“Dosya X alıcı Y’ye gönderildi ✅”

SMTP hata dönerse →
Bot bunu Telegram’da admin’e bildirsin.


Hata Yönetimi
Try/except ile her aşamada hata yakalanmalı.
Hata logları ayrı bir dosyaya (/data/logs/errors.log) yazılmalı.




🔍Telegram Bot Çalışma Yöntemi
Webhook → Performans + düşük CPU.
Render, Railway, Fly.io gibi ortamlarda webhook önerilir çünkü idle modda CPU harcamaz.
webhook tercih edilecek
Polling → Geliştirme/test için kolay ama sürekli CPU tüketir (loop). (işlevsel değil)


Performans & CPU Değerlendirme
✅ CPU Dostu → Satır satır işleme, lazy create kitap mantığı, set() ile eşleşme.
✅ Bellek Tasarrufu → openpyxl + chunk işleme, pandas kullanmamak.
✅ Verimlilik → Dosyalar en sonda yazılır, mail arka planda atılır.
✅ Modülerlik → Geliştirmesi, bakımı kolay











telegram_bot_project/
│
├── main.py                 # Bot ana giriş (aiogram 3.x)
├── requirements.txt        # Bağımlılıklar
├── config.py               # Ortak ayarlar (token, mail, paths)
│
├── handlers/               # Telegram komut & mesaj işleyicileri
│   ├── __init__.py
│   ├── upload_handler.py   # Excel dosyası yükleme
│   ├── status_handler.py   # İşlem özeti & log raporu
│   ├── admin_handler.py    # Admin kontrolleri
│
├── utils/                  # İş mantığı (bağımsız modüller)
│   ├── __init__.py
│   ├── excel_cleaner.py    # Başlık doğrulama & sütun düzenleme
│   ├── excel_splitter.py   # Gruplara ayırma & lazy workbook
│   ├── file_namer.py       # Dosya isimlendirme (GrupName-0916_1621.xlsx)
│   ├── mailer.py           # Mail gönderim (async smtp)
│   ├── validator.py        # Girdi & çıktı doğrulama (satır sayısı, sütunlar)
│   ├── reporter.py         # İşlem sonrası rapor (Telegram’a özet)
│
├── jobs/                   # Ağır / arka plan görevleri
│   ├── __init__.py
│   ├── process_excel.py    # Büyük Excel dosyalarını chunk halinde işle
│   ├── send_reports.py     # Rapor mail jobları (queue bazlı)
│
├── data/                   # Çalışma alanı
│   ├── input/              # Kullanıcıdan gelen dosyalar
│   ├── output/             # İşlenen grup dosyaları
│   ├── groups/             # Grup tanım dosyaları (Excel/JSON)
│   ├── logs/               # İşlem ve hata logları
│   │   ├── bot.log
│   │   ├── errors.log
│   │   └── process.log
│
├── tests/                  # Otomatik testler
│   ├── test_excel_cleaner.py
│   ├── test_excel_splitter.py
│   ├── test_validator.py
│
└── docs/                   # Belgeleme
    ├── README.md           # Kurulum ve kullanım
    ├── WORKFLOW.md         # İş akışı şeması
    └── GROUPS_FORMAT.md    # Grup dosyası formatı








NOT:
gruplar  JSON formatında olacak
örnek:
{
  "groups": [
    {
      "group_id": "Grup_1",
      "group_name": "NURHAN",
      "cities": ["Afyon", "Aksaray", "Ankara", "Antalya", "Van"],
      "email_recipients": ["email1@example.com", "email2@example.com"]
    }
  ]
}










>>> BOTUN YAPMASI PLANLANAN İŞLEMLER <<<<
15.09.2025	MUĞLA	10829870746	BURHAN SELİM	ZABUN		5550375776	MİYALJİ		
15.09.2025	MUĞLA	10829870746	BURHAN SELİM	ZABUN		5550375776	MİYALJİ		



telegram bota excel dosyası yüklenecek
excel dosyasında başlık satırı olacak (1.satır)
başlık satırında önemli olan sutunlar "TARİH" / "tarih" ve "İL" / "il"

bot 
✅
- yüklenen excel dosyasında sutun duzenlemesi yapılacak
verilerden önce solda boş sutun varsa silinecek
"TARİH" sutunu A, "İL" sutunu B sutunu, diğer başlıklar C,D,E... şeklinde duzenlenecek


✅
- tek dosyayı tanımlı gruplara ayıracak
- ayırma işleminde referans "il" sutunu olacak
- yükelenen excelde her satır taranacak
- satır ile eşleşen tanımlı grup varsa bu gruba ait excel kitabı oluşturulacak
(“Gerektiğinde dosya oluşturmak” daha hızlı, verimli ve CPU dostu)
- eşlesen veri bu kitaba kaydedilecek


✅
- oluşan kitaba 
- eşleşen her satırdaki A:N yüklenen excelden kopyalanacak
- tanımlı ve eşleşen grupta B:O ya yapıştırılacak
Aynı il birden fazla grupta varsa, o ile ait satır her eşleşen gruba ayrı ayrı eklenecek.
- eşleşme olmaz ise Grup_0 dosyası açılıp buraya kaydedilecek

✅
- tüm tarama bittiğinde oluşan tüm excel kitapları kaydedilecek
Grup_no /Grup_name (opsiyonel bu bilgi varsa öncelik bu) ile kaydedilecek
örnek doysa adı: Grup_no-MonthDay_HourMinute.xlsx
grup_1	> grup_1-0916_1602.xlsx
grup_2 (grup_name: kemal)	> kemal-0916_1602.xlsx

✅
- oluşan her çalışma kitabı tanımlı mail adreslerine gönderecek
- işlem sonrası cache tezilenecek

ÖRNEK
1- yüklenen dosya

boş sutun	TC	ADI	SOYADI	PLAKA	İL	TARİH	ADRES	İLETİŞİM	DURUMU	veri1	veri2	veri3
	10287126164	HAMDİ	BOZKURT	68ES568	AKSARAY	14.09.2025	CUMHURİYET MAH. TOSUN KÜME EVLERİ  NO: 136  İÇ KAPI NO: 1 ESKİL / AKSARAY	KENDİSİ (90)(536)2384978, (90)(533)4116800		ATEŞ	19762866656	GÜNDÜZ
	38339190826	NECATİ	BELGEMEN	68ES568	AKSARAY	14.09.2025	MERKEZ MAH. KARAOĞLANOĞLU CAD. NO: 23  İÇ KAPI NO: 15 ESKİL / AKSARAY	KENDİSİ +90-532-7378775		KIRAT	10085188494	AKAY
	16945449484	MESUT	YAMAN	07UH844	ANTALYA	15.09.2025	İSTİKLAL MAH. RASİH KAPLAN 4 SK. NO: 24/1  İÇ KAPI NO: 3 GAZİPAŞA / ANTALYA	DENİZ YAMAN (KARDEŞİ) +90-532-7620879                                                         BÜLENT YAMAN (KARDEŞİ) +90-533-6006740	X	BOZYİĞİT		
	12859585676	MEVLÜT	GÖKMEN	07UL885	VAN	15.09.2025	HASDERE MAH. SABIK SK. NO: 14  İÇ KAPI NO: 2 GAZİPAŞA / ANTALYA	MURAT GÖKMEN (OĞLU) (546) 975-2687                                                             MUSTAFA GÖKMEN (KARDEŞİ) (90)(538)2949003	X			
	42665080584	GÜRDAL	UZUN	74AAT975	BARTIN	14.09.2025	AKÇALI KÖYÜ YUKARIKÖY MEVKİİ YUKARIKÖY KÜME EVLERİ  ABDULLAH UZUN NO: 2  İÇ KAPI NO: 2 MERKEZ / BARTIN	KENDİSİ 905425631174                                                                                          ABDULLAH UZUN (BABASI) +90-544-1634374	5 Y			



2- düzenleme sonrası
TARİH	İL	TC	ADI	SOYADI	PLAKA	ADRES	İLETİŞİM	DURUMU	veri1	veri2	veri3
14.09.2025	AKSARAY	10287126164	HAMDİ	BOZKURT	68ES568	CUMHURİYET MAH. TOSUN KÜME EVLERİ  NO: 136  İÇ KAPI NO: 1 ESKİL / AKSARAY	KENDİSİ (90)(536)2384978, (90)(533)4116800		ATEŞ	19762866656	GÜNDÜZ
14.09.2025	AKSARAY	38339190826	NECATİ	BELGEMEN	68ES568	MERKEZ MAH. KARAOĞLANOĞLU CAD. NO: 23  İÇ KAPI NO: 15 ESKİL / AKSARAY	KENDİSİ +90-532-7378775		KIRAT	10085188494	AKAY
15.09.2025	ANTALYA	16945449484	MESUT	YAMAN	07UH844	İSTİKLAL MAH. RASİH KAPLAN 4 SK. NO: 24/1  İÇ KAPI NO: 3 GAZİPAŞA / ANTALYA	DENİZ YAMAN (KARDEŞİ) +90-532-7620879                                                         BÜLENT YAMAN (KARDEŞİ) +90-533-6006740	X	BOZYİĞİT		
15.09.2025	VAN	12859585676	MEVLÜT	GÖKMEN	07UL885	HASDERE MAH. SABIK SK. NO: 14  İÇ KAPI NO: 2 GAZİPAŞA / ANTALYA	MURAT GÖKMEN (OĞLU) (546) 975-2687                                                             MUSTAFA GÖKMEN (KARDEŞİ) (90)(538)2949003	X			
14.09.2025	BARTIN	42665080584	GÜRDAL	UZUN	74AAT975	AKÇALI KÖYÜ YUKARIKÖY MEVKİİ YUKARIKÖY KÜME EVLERİ  ABDULLAH UZUN NO: 2  İÇ KAPI NO: 2 MERKEZ / BARTIN	KENDİSİ 905425631174                                                                                          ABDULLAH UZUN (BABASI) +90-544-1634374	5 Y			



3- tanımlı gruplar

Grup_1	Grup_2	Grup_3	Grup_4	Grup_5
NURHAN	MAHMUTBEY	
Afyon	Adana	Afyon	Balıkesir	BALIKESİR
Aksaray	Adıyaman	Aydın	Bursa	ÇANAKKALE
Ankara	Batman	Burdur	Çanakkale	
Antalya	Bingöl	Isparta	Düzce	
Van	Bitlis	İzmir	Kocaeli	
Çankırı	Diyarbakır	ÇANAKKALE	Sakarya	
Isparta	Van	Manisa	Tekirdağ	


1.satır grup noları
2.satır grup_name (varsa)
3.satır ve sonraki satırlar gruba ait iller

örnek:

Grup_1
NURHAN_hanm
Afyon
Aksaray
Ankara
Antalya
Burdur
Çankırı
Isparta
Karaman
Kayseri
Kırıkkale

grup_no: Grup_1
grup_name: NURHAN
il (city) :
Afyon, Aksaray, Ankara, Antalya, VAN, Çankırı, Isparta, ...



4- satır tarama eşleştirme, kitap oluşturma
dosya adı: NURHAN-0916_1621.xlsx
TARİH	İL	TC	ADI	SOYADI	PLAKA	ADRES	İLETİŞİM	DURUMU	veri1	veri2	veri3
14.09.2025	AKSARAY	10287126164	HAMDİ	BOZKURT	68ES568	CUMHURİYET MAH. TOSUN KÜME EVLERİ  NO: 136  İÇ KAPI NO: 1 ESKİL / AKSARAY	KENDİSİ (90)(536)2384978, (90)(533)4116800		ATEŞ	19762866656	GÜNDÜZ
14.09.2025	AKSARAY	38339190826	NECATİ	BELGEMEN	68ES568	MERKEZ MAH. KARAOĞLANOĞLU CAD. NO: 23  İÇ KAPI NO: 15 ESKİL / AKSARAY	KENDİSİ +90-532-7378775		KIRAT	10085188494	AKAY
15.09.2025	ANTALYA	16945449484	MESUT	YAMAN	07UH844	İSTİKLAL MAH. RASİH KAPLAN 4 SK. NO: 24/1  İÇ KAPI NO: 3 GAZİPAŞA / ANTALYA	DENİZ YAMAN (KARDEŞİ) +90-532-7620879                                                         BÜLENT YAMAN (KARDEŞİ) +90-533-6006740	X	BOZYİĞİT		
15.09.2025	VAN	12859585676	MEVLÜT	GÖKMEN	07UL885	HASDERE MAH. SABIK SK. NO: 14  İÇ KAPI NO: 2 GAZİPAŞA / ANTALYA	MURAT GÖKMEN (OĞLU) (546) 975-2687                                                             MUSTAFA GÖKMEN (KARDEŞİ) (90)(538)2949003	X			


dosya adı: MAHMUTBEY-0916_1621.xlsx
TARİH	İL	TC	ADI	SOYADI	PLAKA	ADRES	İLETİŞİM	DURUMU	veri1	veri2	veri3
15.09.2025	VAN	12859585676	MEVLÜT	GÖKMEN	07UL885	HASDERE MAH. SABIK SK. NO: 14  İÇ KAPI NO: 2 GAZİPAŞA / ANTALYA	MURAT GÖKMEN (OĞLU) (546) 975-2687                                                             MUSTAFA GÖKMEN (KARDEŞİ) (90)(538)2949003	X			


dosya adı: Grup_0-0916_1621.xlsx (eşleşen grup yok)
TARİH	İL	TC	ADI	SOYADI	PLAKA	ADRES	İLETİŞİM	DURUMU	veri1	veri2	veri3
14.09.2025	BARTIN	42665080584	GÜRDAL	UZUN	74AAT975	AKÇALI KÖYÜ YUKARIKÖY MEVKİİ YUKARIKÖY KÜME EVLERİ  ABDULLAH UZUN NO: 2  İÇ KAPI NO: 2 MERKEZ / BARTIN	KENDİSİ 905425631174                                                                                          ABDULLAH UZUN (BABASI) +90-544-1634374	5 Y			




# config.py - Geliştirilmiş versiyon
#BOT_TOKEN yerine TELEGRAM_TOKEN KULLANILACAK
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    TELEGRAM_TOKEN: str
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    ADMIN_CHAT_IDS: list[int]
    
    # Path'ler
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    INPUT_DIR = DATA_DIR / "input"
    OUTPUT_DIR = DATA_DIR / "output"
    LOGS_DIR = DATA_DIR / "logs"
    
    def __post_init__(self):
        # Dizinleri oluştur
        for directory in [self.INPUT_DIR, self.OUTPUT_DIR, self.LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
			
			
			
