Katalog: 9101009.35

Analisis Isu Terkini

### Studi Pemanfaatan Big Data Tahun 2025

Volume 4, 2025

![](_page_0_Picture_4.jpeg)

![](_page_0_Picture_5.jpeg)

Katalog: 9101009.35

Analisis Isu Terkini

### Studi Pemanfaatan Big Data Tahun 2025

Volume 4, 2025

![](_page_2_Picture_4.jpeg)

### **ANALISIS ISU TERKINI STUDI PEMANFAATAN BIG DATA TAHUN 2025**

Volume 4, 2025

© **https://jatim.bps.go.id**

**https://jatim.bps.go.id**

### KATA PENGANTAR

<span id="page-6-0"></span>ig Data merupakan salah satu sumber data baru yang banyak digunakan saat ini. Seiring dengan kemajuan ilmu pengetahuan dan teknologi, kehadiran Big Data menjadi jawaban untuk mengungkap fenomena yang terjadi di masyarakat secara cepat dan up to date.

Penyusunan publikasi Analisis Isu Terkini Studi Pemanfaatan Big Data tahun 2025 ini bertujuan untuk menyediakan informasi mengenai pemanfaatan Big Data beserta analisisnya secara lengkap. Informasi yang akan dihasilkan dan diulas dengan memanfaatkan Big Data ini meliputi studi di bidang ekonomi dan ketenagakerjaan. Selanjutnya, informasi tersebut diharapkan bisa menjadi bahan kajian menuju evidence base of official statistics indikator sosial dan ekonomi Jawa Timur.

Secara khusus, kehadiran publikasi ini juga menjawab tantangan perkembangan pemanfaatan Big Data dengan mengulas beberapa aspeknya. Oleh karena itu, publikasi ini menjadi kajian awal penggunaan Big Data yang ke depan diperkirakan mampu menjadi pendekatan atau proxy dalam rangka estimasi cepat mengenai indikator-indikator statistik.

Semoga publikasi ini menjadi pioner yang baik untuk pengembangan metodologi statistik sekaligus memberi manfaat besar bagi seluruh pembaca. Terima kasih juga diucapkan kepada semua pihak yang telah memberi saran dan kritik membangun.

Surabaya, Desember 2025 Kepala Badan Pusat Statistik Provinsi Jawa Timur

Zulkipli

### **DAFTAR ISI**

### <span id="page-8-0"></span>ANALISIS ISU TERKINI STUDI PEMANFAATAN BIG DATA TAHUN 2025 Volume 5, 2025

| KATA PENGANTARv                                                                                                                   |
|-----------------------------------------------------------------------------------------------------------------------------------|
| DAFTAR ISIvii                                                                                                                     |
| DAFTAR TABELix                                                                                                                    |
| DAFTAR GAMBARxi                                                                                                                   |
| BAB 1 Analisis <i>Geo-semantic</i> untuk Pemetaan, Persebaran dan Perkembangan Program Makan Bergizi Gratis (MBG) di Jawa Timur13 |
| 1.1 Pendahuluan15                                                                                                                 |
| 1.2 Metode                                                                                                                        |
| 1.3 Pembahasan Hasil23                                                                                                            |
| 1.4 Kesimpulan32                                                                                                                  |
| BAB 2 Digital Morphogenesis of Metropolitan East Java: Big Data and The Next Decade of Urban Expansion33                          |
| 2.1 Pendahuluan35                                                                                                                 |
| 2.2 Metode38                                                                                                                      |
| 2.3 Pembahasan Hasil40                                                                                                            |
| 2.4 Kesimpulan47                                                                                                                  |
| DAFTAR PUSTAKA49                                                                                                                  |

<span id="page-10-0"></span>

| Tabel 1.1 | Data frame<br>hasil tagging<br>lokasi setiap berita    | 19 |
|-----------|--------------------------------------------------------|----|
| Tabel 1.2 | Topik Klasifikasi                                      | 20 |
| Tabel 1.3 | Data frame Hasil Pengelompokan Lapangan Usaha<br>      | 21 |
| Tabel 1.4 | Hasil Bridging<br>Nilai Sentimen dan PDRB per Tiruwlan | 22 |
| Tabel 1.5 | Lapangan Usaha Dominan per Triwulan                    | 25 |
| Tabel 1.6 | Lapangan Usaha Dominan setiap Media<br>                | 27 |

### **DAFTAR GAMBAR**

<span id="page-12-0"></span>

| Gambar 1.1 | Diagram Alur Metodologi                                                    | 17 |
|------------|----------------------------------------------------------------------------|----|
| Gambar 1.2 | Nilai Korelasi Sentimen dan Pertumbuhan Ekonomi                            | 23 |
| Gambar 1.3 | Tren Korelasi Sentimen dan Pertumbuhan Ekonomi per Triwulan                |    |
|            |                                                                            | 24 |
| Gambar 1.4 | Proporsi Sentimen pada Media                                               | 26 |
| Gambar 1.5 | Peta Persebaran Sentimen Wilayah Jawa Timur                                | 30 |
| Gambar 1.6 | Representasi Topik Dominan Setiap Wilayah Jawa Timur                       | 31 |
| Gambar 2.1 | Pemetaan Amatan K-Means Clustering                                         | 41 |
| Gambar 2.2 | Identifikasi Jumlah <i>Cluster</i> Optimal                                 | 42 |
| Gambar 2.3 | Pemetaan Aglomerasi <i>K-Means Clustering</i> menurut Kabupaten/Kota, 2024 | 43 |
| Gambar 2.4 | Hasil Aglomerasi <i>DBSCAN Clustering</i> menurut Kabupaten/Kota, 2024     | 45 |

![](_page_14_Figure_0.jpeg)

Analisis *Geo-semantic* untuk Pemetaan, Persebaran, dan Perkembangan Program Makan Bergizi Gratis (MBG) di Jawa Timur

- 1.1 Pendahuluan
- 1.2 Metode
- 1.3 Pembahasan Hasil
- 1.4 Kesimpulan

### 1.1 Pendahuluan

Program Makan Bergizi Gratis (MBG) merupakan salah satu kebijakan strategis Presiden Prabowo Subianto yang dirancang untuk mengatasi masalah gizi buruk, menekan angka *stunting*, sekaligus meningkatkan kualitas sumber daya manusia Indonesia. Program ini secara khusus menargetkan anak sekolah, balita, ibu hamil, dan ibu menyusui sebagai kelompok sasaran utama. Secara global, inisiatif seperti MBG sejalan dengan tujuan pembangunan berkelanjutan (*Sustainable Development Goals*/SDGs), khususnya SDG 2 *Zero Hunger* yang menargetkan penghapusan kelaparan dan peningkatan ketahanan pangan, serta mendukung SDG 3 *Good Health and Well-being* dan SDG 4 *Quality Education* yang berfokus pada peningkatan kualitas hidup dan pendidikan anak (Alemayehu Assefa, 2025).

Implementasi program MBG di tingkat daerah, khususnya di Provinsi Jawa Timur, menghadapi berbagai tantangan dalam hal pemerataan pelaksanaan dan efektivitas distribusi program. Variasi kondisi sosial, ekonomi, dan geografis antar wilayah menyebabkan adanya perbedaan tingkat partisipasi dan keberhasilan program. Oleh karena itu, diperlukan suatu pendekatan analitis yang mampu memetakan secara spasial bagaimana persebaran dan perkembangan program MBG berlangsung di berbagai kabupaten/kota. Pemetaan berbasis data tersebut penting sebagai dasar evaluasi kebijakan dan pengambilan keputusan yang lebih tepat sasaran.

Dalam beberapa tahun terakhir, analisis *geo-semantic* telah menjadi pendekatan yang semakin populer untuk mengidentifikasi pola spasial dan tematik dari data berbasis teks (Janowicz et al., 2020). Pendekatan ini menggabungkan analisis geografis dengan pemrosesan bahasa alami (*Natural Language Processing*/NLP) untuk mengekstraksi informasi spasial dari teks, seperti berita, media, sosial, dan laporan kebijakan (Liu et al., 2025). Dengan demikian, *geo-semantic* memungkinkan integrasi antar dimensi semantik (makna teks) dan dimensi geografis (lokasi), yang dapat menggambarkan persebaran isu atau program secara lebih kontekstual.

Namun, meskipun pendekatan *geo-semantic* menunjukkan potensi besar dalam pemetaan isu dan analisis berbasis teks, penelitian-penelitian terdahulu masih memiliki sejumlah keterbatasan yang memberikan ruang bagi kajian lebih lanjut. Sebagian besar studi sebelumnya lebih banyak diterapkan pada isu lingkungan, bencana, atau analisis opini publik di media sosial, sementara penerapannya pada konteks kebijakan sosial di

negara berkembang, khususnya Indonesia, masih sangat terbatas. Selain itu, banyak penelitian menggunakan data dari *platform* media sosial yang cenderung belum terstruktur dan bersifat dinamis, sehingga belum sepenuhnya memanfaatkan sumber informasi yang lebih stabil dan kaya konteks seperti berita daring. Berita daring dipandang sebagai sumber data yang potensial untuk menggambarkan perkembangan dan persebaran implementasi MBG. Berita mengandung informasi deskriptif, spasial, dan temporal yang dapat mencerminkan dinamika sosial serta persepsi publik terhadap program pemerintah (Hakim, Pasaribu, dan Fadiyah, 2023). Integrasi antara hasil analisis semantik dengan evaluasi implementasi kebijakan juga belum banyak dilakukan, sehingga pemetaan geospasial yang dihasilkan belum memberikan gambaran yang komprehensif terkait variasi keberhasilan program antardaerah.

Hingga kini, belum ditemukan penelitian yang secara spesifik menerapkan pendekatan *geo-semantic* untuk menganalisis implementasi Program Makan Bergizi Gratis (MBG), terutama pada level sub-nasional seperti kabupaten/kota di Provinsi Jawa Timur yang memiliki keragaman sosial dan geografis yang tinggi. Keterbatasan-keterbatasan tersebut menunjukkan adanya celah penelitian yang penting untuk diisi melalui kajian yang mengintegrasikan analisis semantik dan spasial dalam memahami persebaran informasi dan pelaksanaan program MBG secara lebih luas.

Penelitian ini bertujuan untuk menganalisis persebaran dan perkembangan Program Makan Bergizi Gratis (MBG) di Jawa Timur melalui pendekatan *geo-semantic* berbasis teks daring. Hasil analisis diharapkan dapat memberikan wawasan baru dalam pemetaan spasial kebijakan sosial berbasi data tekstual, serta mendukung upaya pemerintah dalam mengevaluasi efektivitas program MBG sebagai bagian dari pencapaian target SDGs di Indonesia.

### 1.2 Metode

Penelitian ini menggunakan pendekatan analisis *geo-semantic* untuk memahami persebaran dan perkembangan program Makan Bergizi Gratis (MBG) di Jawa Timur. Pendekatan ini mengintegrasikan analisis semantik teks berita daring dengan informasi geografis untuk memetakan dinamika wacana MBG secara spasiotemporal.

![](_page_18_Figure_0.jpeg)

**Gambar 1.1 Diagram Alur Metodologi** 

### **Langkah-Langkah Analisis**

### 1. Pengumpulan Data (Data Acquisition)

Data diperoleh melalui proses web scraping dari situs berita lokal yang memuat informasi mengenai pelaksanaan, kebijakan, maupun dampak program Makan Bergizi Gratis (MBG) di wilayah Jawa Timur. Data yang dikumpulkan mencakup judul berita, isi berita, tanggal publikasi, dan sumber atau link berita.

### 2. Proses Text Preprocessing

Pada tahap ini akan dilakukan transformasi data teks yang tidak terstruktur menjadi data teks yang terstruktur. Data teks tersebut akan diolah dengan menggunakan metode text mining untuk memperoleh informasi yang baik sehingga mudah untuk dianalisis lebih lanjut. Tahapan text preprocessing pada penelitian ini yaitu menghapus NAN, menghapus duplikat, filtering iklan, menghilangkan regex, stopword removal, stemming, mengganti format tanggal, mengambil lokasi yang akan digunakan untuk tagging, mengambil media, dan lower casing.

### 3. Pelabelan Metode Lexicon

Setelah data dibersihkan pada tahapan *text preprocessing*, dilakukan pelabelan menggunakan metode *lexicon*. Pelabelan dilakukan pada data teks berupa kalimat yang memiliki kata pada kamus *lexicon* yang terdiri dari kata negatif dan positif. Kata yang

teridentifikasi dalam kamus *lexicon* akan dihitung skornya sesuai dengan jumlah kata pada setiap teks atau kalimat.

$$S_{positive} \sum_{i \in t}^{n} positive \ score_{i}$$

$$S_{negative} \sum_{i=t}^{n} negative score_i$$

Spositive adalah bobot dari kalimat yang didapatkan melalui penjumlahan n skor polaritas kata opini positif dan Snegative adalah bobot dari kalimat yang didapatkan melalui penjumlahan n skor polaritas kata opini negatif. Dari persamaan nilai sentimen dalam satu kalimat maka diperoleh persamaan 3 untuk menentukan orientasi sentimen dengan perbandingan jumlah nilai positif, negatif dan netral.

$$Sentence_{sentiment} \left\{ \begin{matrix} positive \ if \ S_{positive} > S_{negative} \\ neutral \ if \ S_{positive} = S_{negative} \\ negative \ if \ S_{positive} < S_{negative} \end{matrix} \right\}$$

Jika dalam suatu teks memiliki kata positif lebih banyak dari kata negatif, maka dalam teks tersebut akan dilabeli sentimen positif. Jika dalam suatu teks memiliki jumlah kata positif lebih sedikit dari kata negatif, maka data teks tersebut akan dilabeli sentimen negatif. Jika dalam suatu teks memiliki jumlah kata positif sama dengan kata negatif, maka data teks tersebut akan dilabeli sentimen netral (Rachmadana Ismail et al., 2023).

### 4. Pelabelan Metode IndoBERT

Model bahasa berbasis *Transformer* yang telah dilatih secara khusus pada korpus Bahasa Indonesia. Model ini digunakan untuk mengklasifikasikan teks berita menjadi tiga kategori sentimen, yaitu positif, netral, dan negatif. Model IndoBERT yang telah di *finetune* untuk tugas klasifikasi sentimen diterapkan pada seluruh data berita. Hasil prediksi berupa probabilitas tiap kelas dan label akhir ditentukan berdasarkan nilai tertinggi (Setiawan, Utari Iswavigra, dan Anggiratih, 2025).

### 5. Tagging Lokasi

Tagging lokasi dilakukan dengan menghubungkan setiap berita dengan wilayah administratif yang disebutkan di dalam teks, sehingga dapat dianalisis sentimen dominan pada masing-masing lokasi. Proses ini dilakukan dengan membuat daftar referensi wilayah mencakup seluruh kabupaten/kota di Jawa Timur beserta variasi penulisannya.

Sistem kemudian melakukan pencocokan teks untuk menemukan kemunculan nama wilayah dalam isi berita. Setiap berita diberi label wilayah berdasarkan hasil pencocokan tersebut. Lalu, hasil dari setiap wilayah tersebut akan dipetakan dengan menggunakan titik dari *longitude* dan *latitude* masing-masing. Selanjutnya, data ini dikombinasi dengan hasil analisis sentimen (positif, negatif, netral) untuk menghitung proporsi dan menentukan jenis sentimen yang paling dominan pada tiap wilayah. Dengan cara ini, dapat diketahui persebaran opini publik yang cenderung positif atau negatif terhadap isu tertentu di berbagai daerah.

Tabel 1.1 Data Frame Hasil Tagging Lokasi setiap Berita

| Judul                                                                                               | Isi Berita                                                                                                                                                                                                                             | Lokasi  | Sentimen |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|----------|
| (1)                                                                                                 | (2)                                                                                                                                                                                                                                    | (3)     | (4)      |
| Menko PM<br>Muhaimin Iskandar<br>Tinjau Uji Coba<br>Makan Bergizi<br>Gratis di Pesantren<br>Jombang | Menko PM (Menteri Koordinator Pemberdayaan Masyarakat) Muhaimin Iskandar meninjau uji coba makan bergizi gratis Satu santri mendapatkan makanan satu kardus dengan menu lengkap.                                                       | Jombang | Positif  |
| Belasan Siswa di<br>Jember Dilarikan ke<br>Puskesmas Usai<br>Makan Menu MBG                         | Sebanyak 16 siswa di salah satu SD Negeri di Desa Sidomekar, Kecamatan Semboro, Jember dilarikan ke Puskesmas sebelum makanan diberikan kepada siswa, terlebih dahulu dicicipi guru," tandasnya.                                       | Jember  | Negatif  |
| Siapkan Dapur<br>Umum Program<br>Makan Bergizi<br>Gratis di Kompleks<br>Asrama Kodim                | MAGETAN, Jawa Pos Radar Madiun – Sejumlah pihak mulai melakukan mapping program makan bergizi gratis Nizhamul menilai pemerintah daerah (pemda) perlu ikut campur. Terlebih ada ketentuan yang mengatur itu saat menyusun R-APBD 2025. | Magetan | Netral   |

Sumber: penulis

### 6. Pengelompokan Lapangan Usaha

Dalam setiap berita umumnya tidak terindeks menurut topik yang unik sehingga perlu dikelompokkan terlebih dahulu. Pengelompokan topik berita dilakukan menggunakan *Latent Dirichlet Allocation* (LDA) berbasis pustaka Gensim untuk memetakan setiap berita ke dalam kategori lapangan usaha sesuai klasifikasi BPS "Laju Pertumbuhan PDRB Menurut Lapangan Usaha Triwulanan". Total ada 17 topik lapangan usaha yang menjadi kategori klasifikasi. Secara teoritis, LDA berasumsi bahwa setiap dokumen tersusun atas beberapa topik, dan setiap topik merupakan distribusi probabilistik dari kata-kata yang sering muncul bersama.

Tabel 1.2 Topik Klasifikasi

| Nomor | Topik Klasifikasi                                                              |
|-------|--------------------------------------------------------------------------------|
| (1)   | (2)                                                                            |
| 1     | Pertanian, Kehutanan dan Perikanan                                             |
| 2     | Pertambangan dan Penggalian                                                    |
| 3     | Industri Pengolahan                                                            |
| 4     | Pengadaan Listrik dan Gas                                                      |
| 5     | Pengadaan Air, Pengelolaan Sampah, Limbah, dan Daur Ulang                      |
| 6     | Konstruksi                                                                     |
| 7     | Perdagangan Besar dan Eceran; Reparasi dan Perawatan Mobil dan<br>Sepeda Motor |
| 8     | Transportasi dan Pergudangan                                                   |
| 9     | Penyediaan Akomodasi dan Makan Minum                                           |
| 10    | Informasi dan Komunikasi                                                       |
| 11    | Jasa Keuangan dan Asuransi                                                     |

| 12 | Real Estat                                                     |
|----|----------------------------------------------------------------|
| 13 | Jasa Perusahaan                                                |
| 14 | Administrasi Pemerintahan, Pertahanan dan Jaminan Sosial Wajib |
| 15 | Jasa Pendidikan                                                |
| 16 | Jasa Kesehatan dan Kegiatan Sosial                             |
| 17 | Jasa Lainnya                                                   |

Implementasi dilakukan melalui tahapan tokenization, stopword removal, dan pembentukan dictionary sebelum model LDA dilatih. Hasil evaluasi menunjukkan nilai coherence sebesar 0,453, yang menunjukkan tingkat koherensi topik yang cukup baik untuk korpus berita berbahasa Indonesia yang beragam. Nilai ini mencerminkan bahwa model berhasil membentuk kelompok kata yang relevan secara semantik, meskipun dengan variasi konteks yang tinggi pada teks berita ekonomi dan sosial daerah.

Tabel 1.3 Data Frame Hasil Pengelompokan Lapangan Usaha

| Judul                                                                                 | Isi Berita                                                                                                                                                                    | Topik<br>Dominan | Lapangan<br>Usaha               |
|---------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|---------------------------------|
| (1)                                                                                   | (2)                                                                                                                                                                           | (3)              | (4)                             |
| Pemkab Sidoarjo<br>Resmikan Dapur<br>SPPG Magersari,<br>Layani MBG di 6<br>Sekolah    | Pemerintah Kabupaten (Pemkab) Sidoarjo secara resmi meresmikan dapur Satuan Pelayanan Pemenuhan Gizi (SPPG) kontribusi positif terhadap kesehatan dan prestasi belajar siswa. | 14               | Jasa<br>Pendidikan              |
| Ahli Pangan Unej<br>Beberkan Penyebab<br>Keracunan Program<br>Makan Bergizi<br>Gratis | Kasus keracunan makanan yang menimpa sejumlah pelajar dalam Program Makan Bergizi Gratis (MBG) bawaan pangan seperti diare dan tipus," tegasnya.                              | 15               | Jasa<br>Kesehatan<br>dan Sosial |

| Per Minggu, Pasok<br>45 Kilogram Tauge<br>untuk MBG di<br>Kepanjen Malang | Program Makan Bergizi Gratis (MBG) di Kepanjen mendongkrak perekonomian masyarakat, termasuk petani tauge tersebut dicuci bersih menggunakan air mengalir dan direndam. | 2 | Industri<br>Pengolahan |
|---------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---|------------------------|
|---------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---|------------------------|

### 7. Bridging Data

Dilakukan penggabungan antara dua sumber data yang berbeda, yaitu data hasil analisis sentimen berita dan data BPS "Laju Pertumbuhan PDRB Menurut Lapangan Usaha Triwulanan". Proses dimulai dengan membaca dan menyiapkan data BPS, di mana kolom tahunan dihapus agar fokus pada data per triwulan. Kemudian, data diubah dari format wide menjadi long menggunakan pivot agar setiap kombinasi antara lapangan usaha dan triwulan dapat direpresentasikan sebagai satu baris.

Selanjutnya, dari data sentimen berita dihitung rata-rata nilai compound score per triwulan dan lapangan usaha yang mencerminkan kecenderungan sentimen publik terhadap sektor ekonomi tertentu pada periode waktu tertentu. Setelah kedua data siap, dilakukan proses merging atau penggabungan berdasarkan kesamaan lapangan usaha dan quarter. Hasil akhir berupa tabel bridging yang memuat kolaborasi antara indikator pertumbuhan ekonomi sektoral dan rata-rata sentimen publik (Kaczmarek et al., 2025). Melalui hasil ini, dapat dianalisis sejauh mana hubungan atau korelasi antara sentimen terhadap sektor tertentu dengan pertumbuhan ekonomi sektoral pada periode triwulan yang sama.

Tabel 1.4 Hasil *Bridging* Nilai Sentimen dan PDRB per Triwulan

| Triwulan | Lapangan Usaha                       | Rata-rata<br>Sentimen | Pertumbuhan<br>Ekonomi<br>(PDRB) |
|----------|--------------------------------------|-----------------------|----------------------------------|
| (1)      | (2)                                  | (3)                   | (4)                              |
| 2024Q1   | Pertanian, kehutanan, dan perikanan. | 1,414                 | 2,13                             |
| 2024Q2   | Industri Pengolahan                  | 1,000                 | 0,23                             |

| 2025Q2 | Transportasi dan<br>Pergudangan | 1,134 | 0,60 |
|--------|---------------------------------|-------|------|
|--------|---------------------------------|-------|------|

### 1.3 Pembahasan Hasil

### 1.3.1 Analisis Hubungan Sentimen dan Pertumbuhan Ekonomi

![](_page_24_Figure_4.jpeg)

Sumber: Penulis, Hasil Pengolahan dari Phyton versi 3.12.6

Gambar 1.2 Nilai Korelasi Sentimen dan Pertumbuhan Ekonomi

Gambar 1.2 menunjukkan nilai korelasi antara sentimen publik terhadap program Makan Bergizi Gratis (MBG) dengan tingkat pertumbuhan ekonomi pada berbagai lapangan usaha di Jawa Timur. Hasil analisis memperlihatkan variasi korelasi yang signifikan antar lapangan usaha, dengan nilai berkisar antara -1,00 hingga 1,00.

Lapangan usaha dengan korelasi tertinggi adalah jasa pendidikan (1,00) dan jasa perusahaan (0,97). Hal ini menunjukkan bahwa meningkatnya sentimen positif terhadap MBG beriringan dengan pertumbuhan ekonomi di sektor pendidikan dan layanan profesional. Hal ini logis karena program MBG berfokus pada pemenuhan gizi peserta didik yang mendorong aktivitas pendidikan serta rantai pasok penyediaan pangan.

Sektor penyediaan akomodasi dan makan minum (0,68) serta pertanian, kehutanan, dan perikanan (0,59) juga menunjukkan korelasi positif yang cukup kuat, menandakan adanya efek ekonomi dari peningkatan bahan pangan lokal akibat implementasi program.

Sebaliknya, beberapa sektor di antaranya real estat (-1,00), konstruksi (-0,94), dan industri pengolahan (-0,59) menunjukkan korelasi negatif, menandakan bahwa persepsi

publik terhadap MBG tidak berbanding lurus dengan kinerja ekonomi di sektor-sektor tersebut, yang lebih dipengaruhi oleh faktor investasi makro.

Secara keseluruhan, hasil ini menunjukkan bahwa program MBG memiliki dampak ekonomi terbesar pada sektor sosial dan konsumsi masyarakat, terutama pendidikan dan pangan. Analisis ini mendukung pencapaian SDGs, khususnya tujuan ke-2 (*Zero Hunger*) dan ke-8 (*Decent Work and Economic Growth*).

![](_page_25_Figure_2.jpeg)

Sumber: Penulis, Hasil Pengolahan dari Phyton versi 3.12.6

Gambar 1.3 Tren Korelasi Sentimen dan Pertumbuhan Ekonomi per Triwulan

Gambar 1.3 menunjukkan bahwa hubungan antara sentimen publik dan pertumbuhan ekonomi bersifat fluktuatif sepanjang periode Triwulan I-2024 s.d. Triwulan II-2025. Pada awal 2024, korelasi tinggi dan positif menandakan bahwa optimisme publik sejalan dengan kinerja ekonomi, kemungkinan dipicu oleh aktivitas ekonomi pasca-libur dan kebijakan fiskal awal tahun yang menumbuhkan kepercayaan masyarakat.

Namun, pada Triwulan II-2024 s.d. Triwulan III-2024 terjadi penurunan tajam pada korelasi dan rata-rata sentimen, bahkan berubah menjadi negatif. Kondisi ini mengindikasikan ketidaksinkronan antara persepsi publik dan kondisi ekonomi riil, yang mungkin disebabkan oleh tekanan inflasi atau isu sosial-ekonomi yang menurunkan kepercayaan meski indikator makro belum melemah.

Memasuki Triwulan IV-2024 s.d. Triwulan I-2025, tren kembali positif, menunjukkan pemulihan kepercayaan publik seiring stabilitas ekonomi dan meningkatnya konsumsi akhir tahun. Penurunan kecil di Triwulan II-2025 mencerminkan kewaspadaan terhadap ketidakpastian global. Secara keseluruhan, hasil ini menegaskan bahwa

sentimen publik bersifat reaktif terhadap dinamika ekonomi jangka pendek dan dapat menjadi sinyal awal perubahan arah pertumbuhan ekonomi.

**Tabel 1.5 Lapangan Usaha Dominan per Triwulan** 

| Triwulan | Lapangan Usaha Dominan                                                         | Jumlah<br>Berita |
|----------|--------------------------------------------------------------------------------|------------------|
| (1)      | (2)                                                                            | (3)              |
| 2024Q1   | Jasa Kesehatan dan Kegiatan Sosial                                             | 1                |
| 2024Q2   | Pertanian, Kehutanan dan Perikanan                                             | 7                |
| 2024Q3   | Perdagangan Besar dan Eceran; Reparasi dan Perawatan<br>Mobil dan Sepeda Motor | 6                |
| 2024Q4   | Pertambangan dan Penggalian                                                    | 36               |
| 2025Q1   | Penyediaan Akomodasi dan Makan Minum                                           | 58               |
| 2025Q2   | Pengadaan Listrik dan Gas                                                      | 25               |
| 2025Q3   | Jasa Perusahaan                                                                | 66               |
| 2025Q4   | Real Estat                                                                     | 168              |

Sumber: Penulis

Tabel 1.5 menunjukkan pola perubahan topik pemberitaan terkait Program MBG berdasarkan sektor lapangan usaha pada periode Triwulan I-2024 s.d. Triwulan IV-2025. Pada tahap awal Triwulan I-2024, topik yang muncul masih terbatas dan didominasi oleh sektor Jasa Kesehatan dan Kegiatan Sosial, menunjukkan bahwa pandangan publik masih berfokus pada aspek kesehatan dan isu sosial sebelum program masuk tahap operasional. Memasuki Triwulan II-2024 s.d. Triwulan III-2024, dominasi topik bergeser ke sektor Pertanian dan Perdagangan, yang mengindikasikan meningkatnya perhatian terhadap pemasukan pangan, distribusi bahan makanan, serta harga komoditas sebagai bagian dari persiapan awal implementasi MBG.

Pada Triwulan IV-2024 terlihat lonjakan pemberitaan pada sektor Pertambangan dan Penggalian, yang kemungkinan terkait dengan isu fiskal, pendanaan, atau kebijakan

ekonomi nasional yang berdampak tidak langsung pada pelaksanaan program di daerah. Tren kemudian berubah cukup signifikan pada Triwulan I-2025 s.d. Triwulan III-2025, ketika sektor yang dominan justru berkaitan erat dengan operasional layanan makan, seperti Penyediaan Akomodasi dan Makan Minum serta Jasa Perusahaan. Fase ini menunjukkan bahwa media mulai banyak menyoroti penyedia jasa boga, mekanisme distribusi makanan, hingga peran vendor dan pelaku usaha dalam mendukung program.

Dominasi terbesar muncul pada Triwulan IV-2025, ketika sektor Real Estat menjadi topik yang paling menonjol. Hal ini dapat menggambarkan meningkatnya isu terkait fasilitas seperti gedung sekolah, dapur, atau infrastruktur pendukung lainnya. Secara keseluruhan, pola ini menunjukkan bahwa perhatian media dan publik terhadap MBG bergerak secara bertahap mengikuti perkembangan implementasi program mulai dari isu kesehatan dan sosial, kesiapan logistik, keterlibatan pelaku usaha, hingga aspek infrastruktur fisik.

![](_page_27_Figure_2.jpeg)

1.3.2 Analisis Sentimen dan Pertumbuhan Ekonomi pada Sumber Berita

Sumber: Penulis, Hasil Pengolahan dari Phyton versi 3.12.6

Gambar 1.4 Proporsi Sentimen pada Media

Gambar 1.4 menggambarkan proporsi sentimen dari sumber berita yang digunakan. Penelitian ini menganalisis total 24 media daring yang memberitakan isu terkait pertumbuhan ekonomi selama periode penelitian. Namun, pada bagian ini hanya ditampilkan tiga media (media 5, media 9, dan media 20) sebagai representasi karena ketiganya menunjukkan pola distribusi sentimen yang paling kontras dibandingkan media lainnya. Pemilihan ini bertujuan untuk menyoroti variasi framing dan gaya peliputan antar media yang dapat mempengaruhi persepsi publik.

Pada Media 5, distribusi sentimen menunjukkan komposisi yang relatif seimbang antara positif (36,1%) dan negatif (36,6%), dengan netral sebesar 27,3%. Pola ini mengindikasikan bahwa Media 5 cenderung menampilkan pemberitaan yang berimbang, meskipun terdapat sedikit dominasi nada negatif. Kecenderungan ini dapat disebabkan oleh strategi redaksi yang lebih menekankan sisi kritis, seperti menyoroti tantangan atau dampak kebijakan ekonomi, guna memperkuat fungsi kontrol sosial terhadap pemerintah. Sebaliknya, Media 9 memperlihatkan pembagian yang sama antara sentimen positif dan netral (masing-masing 50,0%). Pola ini menunjukkan pendekatan yang lebih berhati-hati dan moderat, dengan upaya menjaga keseimbangan narasi antara optimisme dan objektivitas. Media ini tampaknya menghindari penggunaan bahasa yang terlalu emosional, baik dalam konteks dukungan maupun kritik, sehingga pemberitaannya terkesan netral dan informatif.

Sementara itu, Media 20 menunjukkan 100,0% sentimen netral, yang menandakan pendekatan peliputan yang sangat deskriptif dan berbasis data. Tidak adanya sentimen positif maupun negatif mengindikasikan bahwa media ini kemungkinan berfokus pada penyampaian fakta empiris tanpa interpretasi subjektif. Karakteristik ini lazim ditemukan pada media atau portal informasi yang berorientasi pada publikasi statistik ekonomi atau laporan resmi.

Secara keseluruhan, perbedaan proporsi sentimen di antara media mencerminkan variasi gaya editorial dan *framing* berita. Media yang menonjolkan sentimen negatif cenderung menekankan aspek problematis dari kebijakan ekonomi, sedangkan media yang dominan netral berupaya mempertahankan objektivitas dan kredibilitas informasi. Temuan ini menegaskan bahwa pola pemberitaan ekonomi di Indonesia tidak homogen, melainkan dipengaruhi oleh kebijakan redaksi, segmentasi pembaca, serta peran yang diambil masing-masing media dalam membentuk persepsi publik terhadap pertumbuhan ekonomi.

Tabel 1.6 Lapangan Usaha Dominan Setiap Media

| Media       | Lapangan Usaha Dominan    | Jumlah Berita |
|-------------|---------------------------|---------------|
| (1)         | (2)                       | (3)           |
| Beritajatim | Pengadaan Listrik dan Gas | 84            |

| Detik            | Pertambangan dan Penggalian             | 48 |
|------------------|-----------------------------------------|----|
| jatim.antaranews | Jasa Perusahaan                         | 5  |
| Jatimnow         | Pengadaan Listrik dan Gas               | 7  |
| Jatimtimes       | Jasa Perusahaan                         | 35 |
| Kabarjatim       | Jasa Keuangan dan Asuransi              | 2  |
| Kabarnganjuk     | Transportasi dan Pergudangan            | 6  |
| Klikjatim        | Informasi dan Komunikasi                | 10 |
| Lensamagetan     | Jasa Kesehatan dan Kegiatan Sosial      | 2  |
| Radarbanyuwangi  | Real Estat                              | 13 |
| Radarbojonegoro  | Jasa Pendidikan                         | 11 |
| Radarbromo       | Industri Pengolahan                     | 9  |
| Radargresik      | Industri Pengolahan                     | 4  |
| Radarjember      | Jasa Perusahaan                         | 18 |
| Radarkediri      | Real Estat                              | 14 |
| Radarmadiun      | Real Estat                              | 34 |
| Radarmadura      | Pengadaan Listrik dan Gas               | 12 |
| Radarmalang      | Real Estat                              | 19 |
| Radarmojokerto   | Real Estat                              | 60 |
| Radarsitubondo   | Jasa Perusahaan                         | 1  |
| Radarsurabaya    | Jasa Perusahaan                         | 11 |
| Radartulungagung | Pengadaan Listrik dan Gas               | 8  |
| Sidoarjonews     | Penyediaan Akomodasi dan Makan<br>Minum | 4  |
| Surabayatoday    | Informasi dan Komunikasi                | 10 |

Tabel 1.6 memperlihatkan distribusi topik dominan berdasarkan sumber berita dalam mengenai Program Makan Bergizi Gratis (MBG). Media seperti beritajatim dan beberapa media jaringan Radar banyak menyoroti sektor Pengadaan Listrik dan Gas serta Real Estat. Hal ini menunjukkan bahwa pemberitaan mereka lebih sering mengangkat aspek infrastruktur pendukung, fasilitas sekolah, hingga kesiapan sarana yang berkaitan dengan implementasi program.

Media nasional seperti Detik cenderung menyoroti isu makro, terlihat dari dominannya sektor Pertambangan dan Penggalian, yang kemungkinan terkait dengan pembahasan anggaran, kebijakan energi, dan isu fiskal pendanaan program. Sebaliknya, media lokal tertentu seperti Kabarnganjuk atau Sidoarjonews lebih fokus pada sektor yang berkaitan dengan aktivitas layanan masyarakat di daerah, seperti Transportasi dan Pergudangan atau Pengadaan Akomodasi dan Makan Minum, menunjukkan penekanan pada logistik distribusi makanan dan kegiatan eksternal.

Beberapa media lainnya seperti Radarbanyuwangi, Radarmalang, Radarmojokerto, dan Radarmadiun memiliki topik dominan Real Estat, menunjukkan banyaknya isu terkait kondisi fisik sekolah, atau kebutuhan fasilitas pendukung di wilayah masing-masing. Sementara itu, media seperti Radarbojonegoro yang dominan pada Jasa Pendidikan menunjukkan bahwa daerah tersebut lebih banyak menyoroti aspek implementasi di sekolah, seperti guru, siswa, atau teknis pelaksanaan program.

Secara keseluruhan, pola ini menggambarkan bahwa media cenderung memberi sorotan berdasarkan isu yang paling relevan di wilayah liputannya, sehingga memberikan gambaran yang beragam mengenai dinamika dan tantangan implementasi MBG di berbagai daerah. Variasi sektor dominan ini memberikan informasi bahwa komunikasi publik terkait program masih tersebar menurut kebutuhan lokal, bukan terpusat pada satu jenis isu saja.

### 1.3.3 Analisis Sentimen dan Pertumbuhan Ekonomi pada Wilayah Jawa Timur

![](_page_31_Figure_1.jpeg)

Sumber: Penulis, Hasil Pengolahan dari Phyton versi 3.12.6

Gambar 1.5 Peta Persebaran Sentimen Wilayah Jawa Timur

Gambar 1.5 menampilkan hasil pemetaan sentimen dalam bentuk peta interaktif Jawa Timur. Titik berwarna hijau menandakan dominasi sentimen positif, kuning menunjukkan sentimen netral, dan merah merepresentasikan sentimen negatif. Dari visualisasi tersebut, terlihat bahwa wilayah selatan dan timur seperti Banyuwangi, Jember, dan Malang cenderung memiliki sentimen positif yang lebih banyak, pemberitaan didominasi pembahasan tentang kemajuan ekonomi daerah, kegiatan masyarakat, serta inovasi pemerintah daerah.

Sebaliknya, beberapa daerah di bagian utara dan barat seperti Surabaya, Bojonegoro, dan Tuban memperlihatkan proporsi sentimen negatif yang lebih tinggi. Hal ini dapat dikaitkan dengan intensitas pemberitaan isi-isu publik seperti kemacetan, kebijakan pemerintah daerah, serta *problem* lingkungan dan industri. Sementara itu, wilayah tengah, seperti Mojokerto dan Pasuruan relatif stabil dengan dominasi sentimen netral yang menandakan pemberitaan lebih berimbang.

Secara keseluruhan, hasil pemetaan ini memperlihatkan variasi persepsi publik antar wilayah dapat menjadi dasar untuk memahami fokus isu dan respons sosial-ekonomi daerah di Jawa Timur. Analisis ini juga membantu mengidentifikasi wilayah yang memerlukan peningkatan komunikasi publik atau upaya memperbaiki citra melalui media.

![](_page_32_Figure_0.jpeg)

Sumber: Penulis, Hasil Pengolahan dari Phyton versi 3.12.6

Gambar 1.6 Representasi Topik Dominan Setiap Wilayah Jawa Timur

Gambar 1.6 memperlihatkan bahwa tiap kabupaten/kota memiliki fokus topik yang berbeda. Kota Surabaya menempati posisi tertinggi dengan jumlah berita terbanyak dan topik dominan Jasa Lainnya, sejalan dengan posisinya sebagai pusat ekonomi, jasa, dan perdagangan di Jawa Timur. Hal ini menunjukkan bahwa media di wilayah metropolitan lebih banyak menyoroti isu sektor tersier dan aktivitas layanan publik.

Sementara itu, Kota Malang, Jember, dan Kediri lebih menonjol pada topik Jasa Pendidikan dan Jasa Perusahaan, menggambarkan karakteristik daerah sebagai pusat pendidikan dan bisnis kreatif. Di sisi lain, Bojonegoro dan Lamongan cenderung memiliki topik dominan "Pertambangan dan Penggalian" serta "Industri Pengolahan" yang sesuai dengan basis ekonomi daerah di sektor ekstraktif dan manufaktur.

Secara keseluruhan, hasil ini menunjukkan bahwa media cenderung menyoroti topik dengan potensi ekonomi utama daerah, baik sektor jasa, industri, maupun sumber daya alam. hal ini menegaskan bahwa analisis topik berbasis berita dapat merefleksikan peta semantik aktivitas ekonomi daerah, sekaligus memberikan gambaran mengenai persebaran fokus pembangunan di Jawa Timur.

### 1.4 Kesimpulan

Analisis *geo-semantic* terhadap pemberitaan program Makan Bergizi Gratis (MBG di Jawa Timur menunjukkan keterkaitan yang erat antara persepsi publik dan dinamika ekonomi daerah. Sentimen positif publik cenderung meningkat di wilayah dan sektor yang secara langsung merasakan dampak program, seperti pendidikan dan jasa perusahaan. Hal ini mengindikasikan bahwa pelaksanaan MBG tidak hanya berperan dalam peningkatan gizi peserta didik, tetapi juga mendorong pergerakan ekonomi di sektorsektor penunjang, mulai dari penyediaan bahan pangan hingga jasa pendukung pendidikan.

Sebaliknya, sektor seperti *real estate*, konstruksi, dan industri pengolahan memperlihatkan hubungan yang berlawanan arah. Hal ini diperkuat dengan dinamika pemberitaan triwulanan yang didominasi oleh sektor-sektor makro pada periode akhir seperti real estat dan jasa perusahaan, yang menandakan bahwa persepsi publik terhadap MBG tidak banyak berpengaruh pada aktivitas ekonomi yang bersifat makro dan berorientasi investasi. Secara temporal, fluktuasi sentimen publik memperlihatkan bahwa kepercayaan masyarakat terhadap program pemerintah sangat reaktif terhadap kondisi sosial-ekonomi yang berkembang, mencerminkan dinamika adaptif dalam persepsi publik terhadap kebijakan daerah.

Dari sisi spasial, wilayah selatan dan timur Jawa Timur seperti Banyuwangi, Jember, dan Malang menunjukkan dominasi sentimen positif, menggambarkan efektivitas implementasi program dan dukungan sosial yang lebih kuat. sementara itu, daerah utara seperti Surabaya dan Bojonegoro cenderung memperlihatkan sentimen negatif, yang dapat dikaitkan dengan tingginya eksposur isu publik, kepadatan aktivitas ekonomi, serta tekanan sosial perkotaan.

### DAFTAR PUSTAKA

- Alemayehu Assefa, E. (2025). How Do School Feeding Programs Support the United Nations 2030 Agenda and the African Union's 2063 Goals?
- Hakim, N. A. T. U., Pasaribu, D., & Fadiyah, D. (2023). Analisis Persepsi Publik Terhadap

  Kebijakan Makassar Recover. Journal of Political Issues, 5(1), 80–94.

  https://doi.org/10.33019/jpi.v5i1.130
- Janowicz, K., Gao, S., McKenzie, G., Hu, Y., & Bhaduri, B. (2020). GeoAl: spatially explicit artificial intelligence techniques for geographic knowledge discovery and beyond. In International Journal of Geographical Information Science (Vol. 34, Issue 4, pp. 625–636). Taylor and Francis Ltd. https://doi.org/10.1080/13658816.2019.1684500
- Kaczmarek, I., Iwaniak, A., Chrobak, G., & Kazak, J. K. (2025). Integrating media sentiment with traditional economic indicators: a study on PMI, CCI, and employment during COVID-19 period in Poland. Journal of Computational Social Science, 8(2). https://doi.org/10.1007/s42001-025-00375-x
- Liu, Y., Ren, Z., Wang, K., Tian, Q., Kuai, X., & Li, S. (2025). A Textual Semantic Analysis

  Framework Integrating Geographic Metaphors and GIS-Based Spatial Analysis

  Methods. Symmetry, 17(7). https://doi.org/10.3390/sym17071064
- Rachmadana Ismail, A., Bagus, R., Hakim, F., & Artikel, R. (2023). Implementasi Lexicon

  Based Untuk Analisis Sentimen Dalam Mengetahui Trend Wisata Pantai Di DI

  Yogyakarta Berdasarkan Data Twitter P-ISSN E-ISSN. In Emerging Statistics and

  Data Science Journal (Vol. 1, Issue 1).
- Setiawan, D., Utari Iswavigra, D., & Anggiratih, E. (2025). Implementation of IndoBERT for Sentiment Analysis of the Constitutional Court's Decision Regarding the Minimum Age of Vice Presidential Candidates. Scientific Journal of Informatics, 12(3). https://doi.org/10.15294/sji.v12i3.26360

hites: Iliatim. bps. 90.io

![](_page_36_Figure_0.jpeg)

## Digital Morphogenesis of Metropolitan East Java: Big Data and The Next Decade of Urban Expansion

- 2.1 Pendahuluan
- 2.2 Metode
- 2.3 Pembahasan Hasil
- 2.4 Kesimpulan

### 2.1 Pendahuluan

Pemetaan wilayah metropolitan dan non-metropolitan di Jawa Timur semakin menarik perhatian di tengah cepatnya arus urbanisasi, meningkatnya mobilitas penduduk, serta kesenjangan pembangunan antarwilayah yang masih tinggi. Kendati demikian, provinsi ini masih menghadapi tantangan khas urbanisasi di negara berkembang, yakni pertumbuhan kota yang cepat dan tekanan terhadap infrastruktur, serta ketimpangan antara pusat-pusat ekonomi besar seperti Surabaya dan wilayah sekitarnya yang masih berkarakter semi-*urban* atau *rural*. Dalam konteks ini, pemahaman yang tepat tentang batas fungsional dan karakteristik wilayah metropolitan menjadi krusial agar *urban planning* dapat lebih adaptif dan *evidence based*.

Secara teoritis, definisi wilayah metropolitan tidak dapat hanya didasarkan pada batas administratif kota atau kabupaten. Pendekatan terkini mengedepankan konsep wilayah fungsional, yakni satuan ruang yang terbentuk dari intensitas interaksi sosialekonomi, konektivitas fisik, dan pola mobilitas harian (functional urban areas) (Moreno-Monroy, Schindler, & Battersby, 2021). Pendekatan ini juga diadopsi dalam berbagai studi kebijakan di Indonesia, di mana Bank Dunia menekankan pentingnya pengukuran wilayah metropolitan berbasis data komuter, konektivitas infrastruktur, dan aktivitas ekonomi lintas batas administratif (World Bank, 2021). Dengan demikian, klasifikasi wilayah metropolitan tidak lagi hanya bergantung pada status administratif, melainkan juga mencakup analisis kuantitatif dan spasial yang mengukur keterhubungan dan fungsi ekonomi antarwilayah.

Dalam praktiknya, penggunaan metode klasterisasi berbasis data spasial menjadi pendekatan yang sangat relevan. Teknik seperti *K-Means, Hierarchical Clustering*, atau *K-Medoids* memungkinkan pengelompokan kabupaten/kota berdasarkan kesamaan karakteristik sosial, ekonomi, dan demografi. Beberapa penelitian lokal telah menerapkan pendekatan ini, misalnya pengelompokan kabupaten/kota berdasarkan indikator kesejahteraan seperti tingkat kemiskinan, kepadatan penduduk, atau PDRB per kapita untuk menentukan prioritas pembangunan (Jatipaningrum, dkk., 2022). Pendekatan berbasis klaster ini membantu mengidentifikasi daerah dengan kondisi sosial-ekonomi serupa sehingga dapat menjadi dasar untuk kebijakan pembangunan yang lebih terarah.

Namun, pendekatan berbasis statistik resmi semata memiliki keterbatasan temporal dan spasial. Data resmi seperti IPM, PDRB, atau ketimpangan pendapatan

umumnya diperbarui setiap tahun atau dua tahun sekali, sehingga sering kali tidak cukup responsif terhadap perubahan cepat akibat ekspansi perkotaan dan dinamika mobilitas. Karena itu, penelitian terkini banyak mengintegrasikannya *big data*, seperti citra satelit *Nighttime Light* (NTL) dan data mobilitas manusia, sebagai sumber informasi dinamis yang dapat menangkap perubahan aktual di lapangan. Intensitas cahaya malam telah terbukti berhubungan erat dengan tingkat aktivitas ekonomi dan kepadatan penduduk di wilayah perkotaan (McAvoy et al., 2024).

Analisis temporal terhadap cahaya malam dapat menunjukkan pola ekspansi kota dan munculnya kawasan transisi dari non-metropolitan menuju metropolitan. Selain itu, Zhang et al. (2024) memperkenalkan algoritma *De-Difference Smoothing* yang menghasilkan produk NTL tahunan dengan akurasi spasial yang lebih tinggi, memungkinkan peneliti mendeteksi perubahan intensitas cahaya di area perkotaan secara lebih presisi. Pengembangan dataset global seperti *High-Quality Daily Nighttime Light* (HDNTL) oleh Pei et al. (2025) juga membuka peluang untuk menganalisis dinamika urban harian dan perubahan fungsional suatu wilayah secara *real-time*. Data semacam ini dapat membantu mengidentifikasi wilayah di Jawa Timur yang mungkin belum berstatus metropolitan secara administratif, tetapi menunjukkan peningkatan signifikan dalam aktivitas ekonomi malam hari atau kepadatan cahaya, yang mencerminkan fungsi metropolitan secara *de facto*.

Aspek lain yang tak kalah penting adalah mobilitas penduduk antarwilayah. Studistudi mutakhir menggunakan data posisi ponsel atau media sosial untuk memperkirakan pola komuter harian dan konektivitas antarwilayah. Misalnya, *UN Global Pulse* (2023) berhasil memperkirakan statistik komuter di wilayah Metropolitan Jakarta menggunakan data mobilitas digital yang teragregasi, memberikan gambaran rinci tentang pergerakan harian penduduk antar kota dan kabupaten. Studi lanjutan menunjukkan bahwa pendekatan serupa dapat diterapkan di wilayah lain, termasuk di Jawa Timur, untuk memetakan hubungan fungsional antarwilayah melalui pergerakan manusia (*Measuring Commuting Statistics in Indonesia Using Mobile Positioning Data*, 2022). Studi kasus di Medan yang dilakukan oleh *MobiliseYourCity* (2023) juga menunjukkan bagaimana data ponsel digunakan untuk mendukung perencanaan transportasi metropolitan dan menilai efisiensi jaringan mobilitas regional.

Dalam konteks kebijakan pembangunan wilayah, penggunaan data mobilitas dan NTL secara terpadu dapat memperkaya pemetaan wilayah metropolitan di Jawa Timur. Sebagai contoh, wilayah Gerbangkertosusila (Gresik, Bangkalan, Mojokerto, Surabaya, Sidoarjo, Lamongan) secara konsisten muncul sebagai inti kawasan metropolitan karena intensitas mobilitas harian dan aktivitas ekonominya yang tinggi. Namun, pendekatan berbasis data fungsional dapat mengungkap klasifikasi wilayah metropolitan belum dimanfaatkan secara administratif. Padahal, analisis integratif berbasis statistik resmi dan big data dapat membantu mendeteksi klasifikasi wilayah ini melalui perspektif berbeda.

Di samping itu, sebagian besar penelitian masih berfokus pada data sektoral dan regulasi administratif dalam menentukan wilayah metropolitan. Belum banyak kajian yang menggabungkan sumber data statistik resmi (official statistics) dan big data sebagai sumber data baru (the new data resource) dalam pengklasifikasian metropolitan di tingkat kabupaten kota. Akibatnya, banyak wilayah yang secara fungsional telah menunjukkan ciri metropolitan, misalnya tingginya mobilitas, kepadatan infrastruktur, dan aktivitas ekonomi malam, namun belum masuk kategori metropolitan pada konteks perencanaan pembangunan. Kondisi ini berpotensi menimbulkan ketidaksesuaian kebijakan. Daerah dengan pertumbuhan pesat justru belum tersentuh pembangunan infrastruktur dan layanan publik yang sepadan seiring dinamika perkembangannya.

Penelitian terbaru oleh Nanda et al. (2022) tentang hubungan antara mobilitas masyarakat dan dinamika COVID-19 di Jakarta memperlihatkan betapa pentingnya data mobilitas *real-time* dalam memahami perilaku penduduk dan interaksi spasial di wilayah perkotaan. Pendekatan serupa dapat diterapkan dalam konteks pembangunan wilayah, untuk mengidentifikasi keterhubungan antar kabupaten dan memetakan pergerakan fungsional yang menentukan status metropolitan suatu wilayah.

Dari sejumlah penelitian terdahulu tersebut, belum adanya studi untuk mengklasifikasikan wilayah metropolitan dan non-metropolitan di Jawa Timur dengan mengintegrasikan data statistik resmi dan *big data* menarik untuk diangkat di tengah era *data science* saat ini. Apalagi, pengklasifikasin dengan integrasi dua sumber data tersebut berpeluang menciptakan model klasifikasi wilayah yang lebih sensitif terhadap perubahan spasial dan temporal.

Kajian ini diharapkan mampu mengisi celah tersebut melalui pendekatan model klasifikasi wilayah yang tidak hanya mendeskripsikan status wilayah saat ini, tetapi juga mendeteksi potensi transisi menuju metropolitanisasi. Model klasifikasi wilayah metropolitan dalam kajian ini menggunakan beberapa data, yaitu Indeks Pembangunan Manusia (IPM), Nighttime Light Index (NTL) citra satelit Sentinel, dan sejumlah big data citra satelit lainnya guna menghasilkan klaster fungsional wilayah di Jawa Timur. Hasil kajian ini diharapkan bermanfaat membuka insight baru dalam pengambilan kebijakan berbasis wilayah, misalnya dalam menentukan prioritas pembangunan infrastruktur, perencanaan transportasi, pengendalian urban sprawl, dan peningkatan efisiensi pelayanan publik.

Klasifikasi integratif berbasis *official statistics* dan *big data* ini juga menjadi langkah penting menuju perencanaan wilayah yang lebih cerdas dan berkelanjutan di Jawa Timur. Selain memberikan dasar analisis dari aspek baru bagi pemerintah daerah, pendekatan ini juga mampu memproyeksikan arah transformasi urbanisasi di masa depan dalam mendeteksi lebih dini wilayah berpotensi tumbuh menjadi metropolitan, serta merancang kebijakan pembangunan yang adaptif, berbasis bukti (*evidence based*), dan berorientasi pemerataan.

### 2.2 Metode

### Sumber dan Karakteristik Data

Penelitian ini menggunakan data spasial kabupaten/kota di Provinsi Jawa Timur yang direpresentasikan dalam *format shapefile* (*sf object*) bernama jatim dan jatim\_full. Setiap unit wilayah memuat atribut indikator sosial, ekonomi, infrastruktur, serta lingkungan. Variabel inti yang dianalisis meliputi:

- a. Indikator sosial: Indeks Pembangunan Manusia (IPM);
- b. Indikator fasilitas publik (POI): jumlah fasilitas kesehatan (jml\_ksh), jumlah sekolah (jml\_skl), jumlah fasilitas penunjang ekonomi/komersial (jml\_knm);
- c. **Indikator infrastruktur jaringan**: panjang jaringan listrik PLN (ln\_pwr\_), panjang rel kereta api (ln\_rl\_k), panjang jalan (len\_road\_km);
- d. **Indikator** *remote sensing*: *nighttime light* (ntl), indeks vegetasi NDVI (ndvi), polusi udara NO<sub>2</sub> (no2);

Seluruh indikator kemudian diekstraksi menjadi data tabular melalui fungsi  $st\_drop\_geometry()$ , sehingga hanya atribut non-spasial yang digunakan dalam proses clustering. Data yang hilang (missing values) diimputasi menggunakan rata-rata variabel (mean imputation).

### Normalisasi (Standardisasi Z Score)

Untuk menghindari dominasi variabel yang memiliki skala besar, seluruh variabel numerik dinormalisasi menggunakan transformasi *Z-score* melalui fungsi *scale*(). Secara matematis, normalisasi dilakukan dengan:

$$z_{ij} = \frac{x_{ij} - \mu_j}{\sigma_i}$$

Dengan:

 $x_{ij}$  merupakan nilai variabel ke-j pada wilayah ke-i

 $\mu_i$  merupakan mean variabel ke-j

 $\sigma_i$  merupakan standar deviasi variabel ke-j

### Penerapan Bobot

Kajian ini menerapkan pembobot tematik pada variabel-variabel terpilih menggunakan fungsi *sweep*(). Pembobotan dilakukan berdasarkan relevansi relatif variabel terhadap tingkat aglomerasi wilayah, misalnya: fasilitas publik (kesehatan, pendidikan); infrastruktur jaringan (listrik, rel kereta); dan indikator lingkungan perkotaan (NO<sub>2</sub>, NTL). Secara matematis, pembobotan dilakukan dengan formulasi berikut:

$$x'_{ij} = \omega_i . z_{ij}$$

 $\omega_{j}$  merupakan pembobot variabel. Pembobotan memungkinkan model menekankan aspek-aspek tertentu, misalnya infrastruktur perkotaan lebih baik daripada infrastruktur perdesaan sehingga peluang masuk kategori wilayah metropolitan lebih besar.

Penentuan Jumlah Cluster Optimal

Jumlah klaster optimal ditentukan menggunakan metode *Within-Cluster Sum of Squares* (WSS) atau *Elbow Method*, yang dihitung melalui fungsi *fviz\_nbclust*(). Nilai WSS dihitung dengan formulasi berikut:

$$WSS(k) = \sum_{i=1}^{k} \sum_{x \in C_i}^{\square} ||x - \mu_i||^2$$

di mana: k adalah jumlah *cluster*;  $C_i$  adalah *cluster* ke-i;  $\mu_i$ adalah *centroid cluster* ke-i. Pemilihan jumlah *cluster* dilakukan pada titik ketika penurunan WSS mulai melemah (*elbow point*).

### K-Means Clusterina

Dalam proses pengklasifikasian wilayah dalam wilayah metropolitan, potensi, dan non-metropolitan, kajian ini menggunakan metode *K-Means Clustering*. Prinsip dari

metode ini adalah mengelompokkan data dengan meminimalkan total jarak kuadrat dari setiap data terhadap *centroid* klasternya. Adapun fungsi obyektif yang digunakan sebagai berikut:

$$\sum_{i=1}^{k} \sum_{x \in C_i} \|x - \mu_i\|^2$$

Algoritma ini secara praktis berjalan dua tahap, yaitu tahapan *assignment step* dan *update step*. Pada tahapan *assignment step*, setiap observasi dikelompokkan ke *centroid* terdekat berdasarkan jarak *Euclidian*:

$$\in C_i$$
 jika  $||x - \mu_i|| \le ||x - \mu_i||, \forall j$ 

Sedangkan pada tahapan *update step*, setiap *centroid* klaster diperbaruhi menggunakan rata-rata yang baru dengan formula berikut:

$$\mu_i = \frac{1}{|C_i|} \sum_{x \in C_i}^{\square} x$$

### **DBSCAN Clustering**

Pemanfaatan tenik *Density Based Spatial Clustering of Application with Noise* (DBSCAN) telah umum digunakan pada pengelompokan data menurut kondisi spasial. Teknik ini menggunakan aspek kepadatan sebagai *value* sebagai hasil pengelompokan titik geografis dengan dua parameter, yaitu *epsilon* ( $\epsilon$ ) yang menunjukkan radius kedekatan dan *minPts* atau jumlah minimum titik pembuatan klaster kepadatan. Adapun kategori pengelompokan teknik ini meliputi tiga jenis, yaitu *core point*  $|N_{\epsilon}(p)| \geq minPts$ , *border point*  $|N_{\epsilon}(p)| < minPts$  dengan q adalah *core point*, dan *noise* atau *outlier*  $|N_{\epsilon}(p)| < minPts$  (tidak ada *core point* di dekat amatan). Setelah tahapan klastering selesai, proses akhir dari pengelompokan wilayah dengan memberi identitas wilayah metropolitan, semi/potensi metropolitan, dan non-metropolitan.

### 2.3 Pembahasan Hasil

### **K-Means Clustering**

Hasil *K-Means* pada analisis aglomerasi Jawa Timur menghasilkan narasi perkembangan wilayah yang kaya nuansa: ia tidak sekadar mengelompokkan unit administratif berdasarkan kemiripan vektor indikator, tetapi juga merefleksikan fase kehidupan perkotaan yang berbeda-beda. Dalam keluaran tersebut, Surabaya yang selama ini dipandang sebagai pusat metropolitan utama justru terklasifikasi sebagai potensi metropolitan. Pernyataan ini harus dibaca bukan sebagai penilaian nilai absolut

terhadap kapasitas atau fungsi Surabaya, melainkan sebagai sinyal posisi relatifnya terhadap pola pertumbuhan regional.

*K-Means*, dengan kecenderungan menangkap struktur rata-rata dan momentum pertumbuhan, menempatkan wilayah yang sedang memperlihatkan lonjakan indikator, seperti peningkatan jumlah fasilitas kesehatan, sekolah, jaringan infrastruktur, dan intensitas pencahayaan malam, ke dalam klaster yang secara statistik tampak "lebih metropolitan". Karena Surabaya telah memasuki fase kematangan di mana banyak indikator fungsionalnya stabil atau bertumbuh secara kualitatif ketimbang kuantitatif, kota ini tidak tampil sebagai *outlier* numerik yang mendominasi lagi; sebaliknya, ia berada pada kelas yang menunjukkan kapasitas metropolitan namun tanpa lonjakan kuantitatif yang membedakannya secara tajam dari beberapa kawasan penyangga yang sedang tumbuh cepat.

![](_page_44_Figure_2.jpeg)

Sumber: Penulis, Hasil Pengolahan dari R versi 4.4.0

**Gambar 2.1 Pemetaan Amatan** *K-Means Clustering*

Pendekatan interpretatif yang lebih tajam melihat fenomena ini sebagai manifestasi dari pergeseran struktur metropolitan dari tahap eksplosif ke tahap transformasi. Wilayah perkotaan cenderung mengalami transisi dari akumulasi infrastruktur ke intensifikasi fungsi layanan. Artinya, pertumbuhan tidak lagi diukur oleh penambahan pipa, jalan, atau lampu jalan, melainkan oleh kedalaman dan kualitas jaringan jasa profesional, akses modal, kegiatan R&D, konsentrasi tenaga kerja berpendidikan tinggi, dan hubungan antar-pelaku ekonomi yang bersifat non-fisik. Karena variabel yang dimasukkan dalam klasterisasi Anda lebih merefleksikan kapasitas fisik dan indikator lingkungan (NTL, NDVI, NO<sub>2</sub>) serta jumlah fasilitas dasar, *K-Means* membaca momentum pertumbuhan fisik dan ketersediaan fasilitas, bukan kualitas layanan jasa. Dengan demikian, label potensi metropolitan bagi Surabaya lebih tepat diartikan sebagai tanda bahwa kota telah mencapai titik di mana aspek-aspek yang sebelumnya mendorong lonjakan kuantitatif telah mereda, sementara nilai strategis kota terletak pada transformasi sektoral yang memerlukan indikator lain untuk tertangkap secara kuantitatif.

![](_page_45_Figure_1.jpeg)

Sumber: Penulis, Hasil Pengolahan dari R versi 4.4.0

Gambar 2.2 Identifikasi Jumlah Cluster Optimal

Implikasi kebijakan dari pembacaan ini sangat penting. Posisi Surabaya dalam klaster potensi mengindikasikan ruang kebijakan untuk memperjelas dan menguatkan peran kota sebagai pusat jasa bernilai tambah tinggi agar tercermin pula dalam indikator terukur. Intervensi strategis yang bersifat kualitas, seperti peningkatan kapasitas institusi pendidikan tinggi, pengembangan pusat inkubasi dan *coworking*, fasilitas layanan kesehatan spesialis, penyediaan regulasi dan insentif untuk menarik investasi jasa skala menengah-atas, serta peningkatan kualitas pelayanan publik digital, bukan hanya akan memperkuat posisi fungsional Surabaya tetapi juga mengubah profil kuantitatifnya dalam analisis selanjutnya jika indikator jasa dimasukkan ke dalam model. Selain itu, readaptasi tata ruang yang mendukung ruang kerja kolaboratif dan aksesibilitas multimoda penting

untuk memastikan bahwa Surabaya dapat memusatkan aktivitas jasa tanpa menambah tekanan perluasan lahan yang selama ini menggerus ruang hijau dan menurunkan NDVI di pusat kota.

Secara regional, hasil *K-Means* mengonfirmasi adanya proses difusi urban, di mana tekanan pengembangan dan kebutuhan lahan di pusat memicu ekspansi di pinggiran dan penumbuhan klaster-klaster baru. Kota-kota seperti Sidoarjo dan Gresik menunjukkan indikator kuantitatif yang naik cepat, yang menandakan bahwa fungsi metropolitan sedang terdistribusi ke jaringan kota satelit. Pola ini membuka peluang pengembangan tata pemerintahan wilayah yang lebih integratif, misalnya pengelolaan transportasi komuter, alokasi lahan industri, dan pembangunan infrastruktur layanan dasar secara koordinatif, agar pertumbuhan wilayah satelit tidak berkembang secara fragmentaris. Jika tidak dikelola, ekspansi ini berisiko menghasilkan *sprawl* yang tidak terkendali, menurunkan efisiensi jaringan transportasi, dan menimbulkan disparitas pelayanan antara koridor pertumbuhan dan wilayah *hinterland*.

![](_page_46_Figure_2.jpeg)

Sumber: Penulis, Hasil Pengolahan dari R versi 4.4.0

Gambar 2.3 Pemetaan Aglomerasi K-Means Clustering menurut Kabupatan/Kota, 2024

Kritikal terhadap interpretasi *K-Means* adalah sensitivitasnya terhadap komposisi variabel dan bobot. Posisi Surabaya yang tampak "potensial" mungkin berubah jika variabel jasa, struktur pekerjaan, atau indikator kualitas hidup dimasukkan dan diberi bobot lebih besar. Oleh karena itu, untuk mengaitkan hasil klasterisasi dengan keputusan

penetapan wilayah metropolitan atau kebijakan perkotaan, diperlukan analisis *cluster* yang lebih sensitif terhadap aspek spasial untuk menimbang ulang *cluster* yang terbentuk dan memastikan kestabilan klasifikasi. Alternatif pendekatan seperti *fuzzy clustering* juga relevan untuk menangkap ambiguitas transisi (misalnya kota yang berada di batas antara metropolitan dan semi-metropolitan), serta analisis panel waktu untuk melihat dinamika historis, apakah Surabaya berada dalam tren relatif stagnan kuantitatif atau sedang mengalami transformasi struktural di sektor jasa.

Secara ringkas, *K-Means* pada data saat ini menyajikan cerita perkembangan berbasis momentum fisik: Surabaya adalah kota matang yang sedang menjalani metamorfosis fungsi, sementara wilayah penyangga menampilkan lonjakan kuantitatif yang menempatkannya lebih menonjol dalam analisis berbasis variabel fisik. Pembacaan ini menuntut respons kebijakan yang menyeimbangkan konsolidasi fungsi jasa berkualitas di pusat dengan pengelolaan ekspansi di pinggiran, agar metropolitanisasi regional mengarah ke integrasi fungsional yang berkelanjutan dan inklusif.

### Hasil Klastering dengan DBSCAN

Reaktivasi jalur kereta api yang direncanakan oleh KAI memiliki potensi untuk menjadi pemicu transformasi spasial yang nyata di Jawa Timur. Rencana intervensi infrastruktur ini tidak hanya memperpendek jarak fisik antarwilayah, tetapi juga meredefinisi pola kepadatan ekonomi dan sosial yang terdeteksi oleh DBSCAN. Jika DBSCAN saat ini menampilkan jaringan koridor dan simpul kepadatan yang terbentuk secara "organik" dari konsentrasi fasilitas, infrastruktur, dan aktivitas ekonomi, maka pengaktifan kembali jalur-jalur mati akan menambah dimensi aksesibilitas yang kuat pada peta tersebut. Aksesibilitas ini, dalam perspektif teori ruang-ekonomi, berfungsi sebagai katalisator, seperti menurunkan biaya transportasi orang dan barang, meningkatkan keterjangkauan area stasiun, serta menciptakan titik-titik baru yang berpotensi berkembang menjadi inti-klaster bila didukung oleh kebijakan tata ruang dan investasi pendukung.

Dalam skenario dekade ke depan, dampak terkuat diperkirakan muncul pada koridor-koridor yang sudah menunjukkan tanda-tanda kepadatan atau berada di jalur reaktivasi. Poros Surabaya-Sidoarjo-Gresik diperkirakan akan mengalami penguatan fungsi metropolitan yang relatif cepat. Integrasi rel penumpang dan barang di koridor ini

akan memperkuat hubungan fungsional antara pusat layanan di Surabaya dan basis industri serta permukiman di Sidoarjo dan Gresik.

Dengan akses rel yang andal, area-area di sekitar stasiun berpotensi mengalami akumulasi POI jasa, *mixed-use development*, dan peningkatan aktivitas malam hari yang terukur melalui indikator seperti NTL. Dalam peta DBSCAN, koridor ini berisiko melihat pergeseran unit-unit yang saat ini berlabel "Potensi Metropolitan" menuju kategori "Metropolitan" karena densitas fungsi dan keterkaitan spasial yang baru muncul akan memenuhi ambang kepadatan lokal yang menentukan pembentukan klaster inti.

Kawasan Malang Raya, yang telah diidentifikasi sebagai simpul metropolitan sekunder, akan mendapat manfaat ganda dari reaktivasi jalur yang menghubungkannya lebih baik ke Surabaya maupun ke koridor selatan-timur. Akses rel yang lebih baik akan menegaskan peran Kawasan Malang Raya sebagai pusat jasa regional dan pendidikan tinggi, sekaligus mempermudah mobilitas mahasiswa, pekerja jasa, dan arus barang. Dalam 10 tahun ke depan, Malang Raya berpotensi memperkuat statusnya sebagai klaster otonom yang semakin kurang bergantung pada Surabaya untuk beberapa fungsi layanan, khususnya dalam bidang pendidikan, kesehatan spesialistik, dan pariwisata kota Batu. Dengan demikian, hasil DBSCAN menunjukkan klaster yang lebih tebal di kawasan ini, menggambarkan maturitas metropolitan yang semakin jelas.

![](_page_48_Figure_3.jpeg)

Sumber: Penulis, Hasil Pengolahan dari R versi 4.4.0

Gambar 2.4 Hasil Aglomerasi DBSCAN Clustering menurut Kabupatan/Kota, 2024

Untuk wilayah timur, koridor yang menghubungkan Pasuruan-Probolinggo-Banyuwangi dan koridor selatan yang menyambung dari Malang ke Lumajang-Jember-Banyuwangi juga berpeluang mengalami akselerasi. Reaktivasi jalur yang menambah kapasitas logistik dan penumpang menjadikan wilayah, seperti Kota Probolinggo, Probolinggo, Jember, dan Banyuwangi lebih menarik sebagai *node* komersial dan jasa regional. Untuk Jember, peran sebagai pusat pendidikan dan pelayanan kesehatan akan semakin mengikat wilayah sekitarnya dalam satu klaster kepadatan; bagi Banyuwangi, peningkatan konektivitas dapat memperkuat peran pelabuhan dan pariwisata sebagai penggerak ekonomi lokal yang berdampak pada kepadatan aktivitas. Dalam istilah DBSCAN, titik-titik berkepadatan sedang di sepanjang koridor ini berpeluang terkonsolidasi menjadi klaster-klaster yang lebih kohesif, mengubah batasan antara "potensi" dan "metropolitan" dalam peta spasial.

Madura menjadi kasus yang patut mendapat perhatian khusus. Meskipun Bangkalan dan Pamekasan saat ini diklasifikasikan sebagai "Potensi Metropolitan" karena keterbatasan kepadatan fungsional, reaktivasi jalur yang mengintegrasikan rute-rute rel di Madura dengan jaringan utama Jawa Timur dapat menutup gap antara kedekatan fisik (misalnya Jembatan Suramadu) dan keterhubungan fungsional. Dengan strategi *Transit-Oriented Development* (TOD) yang fokus pada *node-node* stasiun, peningkatan frekuensi layanan, dan penguatan *feeder* angkutan lokal, Madura berpeluang mengalami percepatan urbanisasi terstruktur dalam 10 tahun mendatang. Namun pencapaian ini bersyarat pada pengembangan lapangan kerja lokal yang memadai dan kebijakan lahan yang mencegah spekulasi tanpa peningkatan kualitas kehidupan lokal.

Skenario transformasi metropolitan yang paling transformatif akan terjadi jika reaktivasi jalur dipadukan dengan kebijakan penataan ruang yang proaktif: zonasi di sekitar stasiun untuk fasilitas lain (misalnya taman, kafe), insentif bagi investasi jasa dan logistik di koridor rel, pengembangan sistem *feeder* dan *last-mile* yang andal, serta regulasi yang mengarahkan relokasi industri padat lahan ke kawasan rel. Jika langkahlangkah ini dilaksanakan secara sinergis, pengaruh pada peta DBSCAN akan bersifat multiplikatif, bukan hanya mengenjot satu atau dua *node*, tetapi memperkuat kontinuitas kepadatan sepanjang koridor sehingga batas antara klaster inti dan wilayah penyangga menjadi lebih kabur akibat konsolidasi fungsional. Dalam konteks 10 tahun, ini bermakna peralihan sejumlah kabupaten dari kategori "Potensi Metropolitan" menjadi

"Metropolitan", khususnya di sepanjang koridor Surabaya-Gresik-Sidoarjo dan Surabaya-Pasuruan-Probolinggo, serta peningkatan otonomi klaster di Malang Raya dan koridor selatan-timur.

Risiko terpenting terhadap kemungkinan ini berasal dari implementasi yang parsial atau tidak sinkron. Jika reaktivasi jalur hanya mengandalkan aspek fisik tanpa integrasi layanan publik lainnya, atau jika pengaktifan jalur hanya untuk angkutan barang tanpa layanan penumpang teratur, maka dampaknya terhadap kepadatan fungsional akan terbatas. Potensi munculnya *sprawl* di sekitar stasiun tanpa perencanaan tata ruang yang baik juga dapat menciptakan pola pertumbuhan yang rapuh, terlihat pada kenaikan NTL namun tanpa peningkatan kualitas layanan atau lapangan kerja yang berkelanjutan. Oleh karena itu, pemetaan hasil DBSCAN satu dekade ke depan akan sangat dipengaruhi oleh kualitas kebijakan pendukung yang menyertai reaktivasi: arah investasi, desain stasiun, integrasi moda serta mekanisme pengelolaan lahan.

Dalam perspektif pasar tenaga kerja dan ekonomi, pengaktifan jalur rel akan mendorong integrasi regional yang lebih kuat, dengan distribusi fungsi yang lebih jelas antara pusat dan satelit. Surabaya diperkirakan akan mempertahankan dominasi pada jasa tingkat tinggi dan fungsi admistratif, sementara koridor-koridor rel yang baru akan memfasilitasi konsentrasi manufaktur ringan, logistik, dan layanan permukiman komuter di wilayah penyangga. Dampak ini akan membentuk pola *commuting* yang lebih terstruktur, arus harian akan bergeser dari dominasi jalan raya ke kombinasi rel dan *feeder*, yang pada gilirannya memperkuat kepadatan di *node-node* stasiun. Dari perspektif hasil DBSCAN, arus komuter yang meningkat dan stabil akan meningkatkan kepadatan lingkungan sekitar (*neighborhood density*) stasiun, sehingga menciptakan kondisi untuk transformasi klaster.

### 2.4 Kesimpulan

Kajian ini menunjukkan bahwa pemetaan metropolitan Jawa Timur berbasis integrasi statistik resmi dan *big data* menghadirkan pemahaman baru mengenai dinamika aglomerasi dan transformasi spasial yang tidak selalu tercermin dalam batas administratif maupun indikator konvensional. Hasil *K-Means* memperlihatkan bahwa struktur metropolitan Jawa Timur saat ini berada pada fase transisi, di mana kota-kota besar yang telah matang seperti Surabaya tidak lagi menonjol secara kuantitatif karena indikator fisik

dan fasilitas dasarnya telah mencapai titik jenuh. Label "potensi metropolitan" yang dilekatkan pada Surabaya dalam hasil klasterisasi bukan mengindikasikan degradasi fungsional, melainkan mencerminkan pergeseran orientasi kota menuju ekonomi jasa bernilai tambah tinggi yang tidak sepenuhnya tertangkap oleh indikator fisik yang digunakan. Sebaliknya, wilayah penyangga seperti Sidoarjo, Gresik, ataupun koridor urban lain di sekeliling Surabaya tampil sebagai pusat pertumbuhan baru karena momentum ekspansi fisik dan peningkatan fasilitas mereka terdeteksi kuat oleh algoritma berbasis jarak dan variabilitas linier tersebut.

Berbeda dengan *K-Means*, hasil DBSCAN memberi gambaran tentang struktur kepadatan spasial yang mengungkap pola keterhubungan fungsional antarwilayah secara lebih organik. DBSCAN menunjukkan bahwa aglomerasi metropolitan di Jawa Timur terbentuk melalui jaringan koridor dan titik simpul kepadatan yang muncul dari kombinasi fasilitas publik, intensitas aktivitas ekonomi, jaringan infrastruktur, dan kedekatan fungsional antar kabupaten/kota.

Dibanding *K-Means* yang menonjolkan keserupaan nilai rata-rata suatu wilayah dengan pusat klaster, DBSCAN justru menekankan kontinuitas kepadatan lokal, sehingga lebih peka terhadap konsentrasi aktivitas yang menjelma secara linier dan tidak simetris, seperti koridor Surabaya-Sidoarjo-Gresik, Malang Raya, dan jalur selatan-timur. Pendekatan berbasis kepadatan ini menegaskan bahwa metropolitanisasi di Jawa Timur bukan sekadar fenomena titik, melainkan fenomena jaringan yang tumbuh mengikuti alur keterhubungan ekonomi dan mobilitas penduduk.

Rencana reaktivasi jalur kereta api KAI menambah dimensi futuristik terhadap pembacaan kedua hasil klasterisasi tersebut. Reaktivasi jalur bertindak sebagai katalis ruang-ekonomi yang memperkuat *node* dan koridor yang sudah padat dalam peta DBSCAN, sekaligus berpotensi mengubah konfigurasi klaster *K-Means* pada dekade berikutnya. Dengan meningkatnya aksesibilitas dan penurunan biaya transportasi, kawasan-kawasan yang saat ini berada pada kategori "potensi metropolitan", misalnya Bangkalan, Pamekasan, Probolinggo, Jember, hingga Banyuwangi mempunyai peluang naik kelas menjadi pusat metropolitan baru ketika kepadatan jasa, aktivitas malam hari, dan konektivitas petanya meningkat secara konsisten.

Koridor rel yang terintegrasi dengan pusat-pusat pertumbuhan akan memperluas radius pengaruh Surabaya dan Malang, menciptakan struktur metropolitan multi-inti

(*polycentric*) yang lebih matang dan terdistribusi. Namun manfaat ini sangat bergantung pada kebijakan tata ruang, kualitas layanan transportasi, serta pengembangan ekonomi lokal yang menyertai reaktivasi jalur; tanpa itu, peningkatan kepadatan dapat tidak menghasilkan transformasi fungsional yang berkelanjutan.

### **DAFTAR PUSTAKA**

- Didan, K., & Vermote, E. (2015). MOD13Q1 MODIS vegetation indices 16-day L3 global 250m [Data set]. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD13Q1.006
- Elvidge, C. D., Baugh, K. E., Kihn, E. A., Kroehl, H. W., Davis, E. R., & Davis, C. W. (1997).

  Satellite inventory of human settlements using nocturnal radiation emissions:

  A contribution for the global urban data base. Photogrammetric Engineering & Remote Sensing, 63(6), 727–734. https://doi.org/10.14358/PERS.63.6.727
- Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017).

  Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote

  Sensing of Environment, 202, 18–27. https://doi.org/10.1016/j.rse.2017.06.031
- Jatipaningrum, M. T., Azhari, S. E., & Suryowati, K. (2022). Pengelompokan kabupaten dan kota di provinsi jawa timur berdasarkan tingkat kesejahteraan dengan metode k-means dan density-based spatial clustering of applications with noise. Jurnal Derivat: Jurnal Matematika Dan Pendidikan Matematika, 9(1), 70–81. https://journal.upy.ac.id/index.php/derivat/article/download/2832/2111/853
- McAvoy, G., & Vadrevu, K. P. (2024). Nighttime Lights and Population Variations in Cities of South/Southeast Asia: Distance-Decay Effect and Implications. Remote Sensing, 16(23), 4458. https://doi.org/10.3390/rs16234458
- MobiliseYourCity. (2021). How the Medan Metropolitan Area (Indonesia) uses mobile phone data to shape mobility. https://www.mobiliseyourcity.net/how-medan-metropolitan-area-indonesia-uses-mobile-phone-data-shape-mobility
- Moreno-Monroy, A. I., Schindler, S., & Battersby, J. (2021). Metropolitan areas in the world. Delineation and population trends. Journal of Urban Economics, 125, 103411. https://doi.org/10.1016/j.jue.2021.103411
- Nanda, R. O., Nursetyo, A. A., Ramadona, A. L., Imron, M. A., Fuad, A., Setyawan, A., & Ahmad, R. A. (2022). Community mobility and COVID-19 dynamics in Jakarta,

- Indonesia. International Journal of Environmental Research and Public Health, 19(11), 6671. https://doi.org/10.3390/ijerph19116671
- Padgham, M., Rudis, B., Downie, T., & Sumner, M. (2023). osmdata: Import

  OpenStreetMap data (R package version X.X). https://CRAN.R
  project.org/package=osmdata
- Pei, Z., Zhu, X., Hu, Y., Chen, J., & Tan, X. (2025). A high-quality daily nighttime light (HDNTL) dataset for global 600+ cities (2012–2024). Earth System Science Data, 17, 5675–5691. https://doi.org/10.5194/essd-17-5675-2025
- Putra, A. P., Setyadi, I. A., Esko, S., & Lestari, T. K. (2022). Measuring commuting statistics in Indonesia using mobile positioning data [Conference paper]. Asia-Pacific Economic Statistics Week. https://www.researchgate.net/publication/358343691\_Measuring\_Commutin g\_Statistics\_in\_Indonesia\_Using\_Mobile\_Positioning\_Data
- The World Bank. (2021). Indonesia Mass Transit Project (P169548) Project Information

  Document / Integrated Safeguards Data Sheet. Jakarta: The World Bank.

  https://documents1.worldbank.org/curated/en/099040101302231080/pdf/Bandung0BRT0Perliminary0ESIA0final.pdf
- UN Global Pulse / Pulse Lab Jakarta. (2023). Inferring commuting statistics in Greater

  Jakarta from social media locational information from mobile devices.

  https://www.unglobalpulse.org/document/inferring-commuting-statisticsfrom-social-media-in-greater-jakarta/
- Zhang, S., Ma, Y., Zhang, X., Li, X., & Chen, X. (2024). Production of annual nighttime light based on De-Difference Smoothing algorithm. Remote Sensing, 16(16), 3013. https://doi.org/10.3390/rs16163013

![](_page_56_Picture_0.jpeg)

![](_page_56_Picture_1.jpeg)

# **https://jatim.bps.go.id**

![](_page_56_Picture_3.jpeg)