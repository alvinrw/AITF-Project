/* ============================================================
   AITF — app.js  (Testing Website)
   CSV Upload → Text Builder → API /predict → Result Display
   ============================================================ */

'use strict';

// ── Config (persisted in localStorage) ──────────────────────────────────────

const DEFAULT_CONFIG = {
  apiUrl: 'http://localhost:8000',
  apiKey: '',
  maxNewTokens: 512,
};

function loadConfig() {
  try {
    const stored = localStorage.getItem('aitf_config');
    return stored ? { ...DEFAULT_CONFIG, ...JSON.parse(stored) } : { ...DEFAULT_CONFIG };
  } catch { return { ...DEFAULT_CONFIG }; }
}

function saveConfig(cfg) {
  localStorage.setItem('aitf_config', JSON.stringify(cfg));
}

let CFG = loadConfig();

// ── DOM refs ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const dropZone = $('dropZone');
const csvFileInput = $('csvFileInput');
const fileInfo = $('fileInfo');
const fileName = $('fileName');
const fileMeta = $('fileMeta');
const clearFileBtn = $('clearFile');
const tableCard = $('tableCard');
const tableHead = $('tableHead');
const tableBody = $('tableBody');
const rowCount = $('rowCount');
const analyzeAllBtn = $('analyzeAllBtn');
const resultsPanel = $('resultsPanel');
const resultsList = $('resultsList');
const clearResultsBtn = $('clearResultsBtn');
const loadingOverlay = $('loadingOverlay');
const loadingText = $('loadingText');
const loadingSub = $('loadingSub');
const statusDot = $('statusDot');
const statusText = $('statusText');
const toastContainer = $('toastContainer');
const settingsBtn = $('settingsBtn');
const settingsModal = $('settingsModal');
const closeSettings = $('closeSettings');
const cancelSettings = $('cancelSettings');
const saveSettings = $('saveSettings');
const apiUrlInput = $('apiUrlInput');
const apiKeyInput = $('apiKeyInput');
const maxTokensInput = $('maxTokensInput');
const downloadTemplate = $('downloadTemplate');

const manualInputBtn = $('manualInputBtn');
const manualModal = $('manualModal');
const closeManual = $('closeManual');
const cancelManual = $('cancelManual');
const submitManual = $('submitManual');
const manualForm = $('manualForm');

// ── State ────────────────────────────────────────────────────────────────────
let csvData = [];   // array of row objects
let csvHeaders = [];
let resultCount = 0;

// ── Konfigurasi Kolom CSV (Sesuai Dataset AITF) ──────────────────────────────
const CSV_COLUMNS = [
  'no', 'nama_PM', 'nik', 'prov_nama', 'kab_nama', 'kec_nama', 'kel_nama', 'rw', 'rt', 'alamat',
  'jumlah_art', 'status_pbi', 'bantuan_pemda', 'luas_lantai', 'jenis_lantai', 'jenis_dinding', 'jenis_atap',
  'sumber_air_minum', 'penerangan', 'daya_listrik', 'bahan_bakar_masak', 'fasilitas_bab',
  'jenis_kloset', 'pembuangan_tinja', 'punya_lahan_lain', 'punya_rumah_lain',
  'aset_tv', 'aset_hp', 'aset_laptop', 'aset_kulkas', 'aset_ac', 'aset_motor', 'aset_mobil',
  'ternak_sapi', 'ternak_kerbau', 'ternak_kambing', 'ternak_domba', 'ternak_babi', 'ternak_ayam', 'ternak_itik',
  'pekerjaan_kepala', 'pendapatan_rata_rata', 'pengeluaran_rata_rata'
];

// Contoh data untuk template download
// CATATAN: Model dilatih khusus untuk wilayah Malang, Jawa Timur
const TEMPLATE_ROWS = [
  // Desil 1 — Sangat miskin, tidak ada aset, tidak ada listrik
  ['1', 'Sutrisno', '3573010101800001', 'JAWA TIMUR', 'KOTA MALANG', 'KLOJEN', 'SAMAAN', '002', '005', 'Gg. Mawar No. 3', '6', 'PBI-JKN', 'Ya', '30', 'Tanah', 'Bambu', 'Jerami/ijuk/daun-daunan/rumbia', 'Mata air tak terlindung', 'Bukan listrik (lampu minyak/lilin/obor)', '0', 'Kayu bakar', 'Tidak ada', 'Cemplung/cubluk', 'Lubang tanah', 'Tidak', 'Tidak', 'Tidak', 'Tidak', 'Tidak', 'Tidak', 'Tidak', 'Tidak', 'Tidak', '0', '0', '0', '0', '0', '0', '0', 'Tidak bekerja', '0', '250000'],
  // Desil 2 — Sangat miskin, sedikit aset
  ['2', 'Suminah', '3573010101850002', 'JAWA TIMUR', 'KOTA MALANG', 'SUKUN', 'SUKUN', '003', '007', 'Jl. Cempaka No. 12', '5', 'PBI-JKN', 'Ya', '28', 'Semen', 'Kayu/Bambu', 'Asbes', 'Sumur tak terlindung', 'PLN', '450', 'Kayu bakar', 'Bersama', 'Cemplung/cubluk', 'Sungai/danau/laut', 'Tidak', 'Tidak', 'Ya', 'Tidak', 'Tidak', 'Tidak', 'Tidak', 'Tidak', 'Tidak', '0', '0', '0', '0', '0', '10', '0', 'Buruh tani', '400000', '450000'],
  // Desil 4 — Miskin, punya beberapa aset
  ['3', 'Wahyu Prasetyo', '3573010101900003', 'JAWA TIMUR', 'KOTA MALANG', 'BLIMBING', 'PURWODADI', '001', '003', 'Jl. Kenanga No. 7', '4', 'PBI-JKN', 'Tidak', '36', 'Semen', 'Tembok', 'Genteng', 'Sumur terlindung', 'PLN', '900', 'Gas LPG', 'Sendiri', 'Leher angsa', 'Septic tank', 'Tidak', 'Tidak', 'Ya', 'Ya', 'Tidak', 'Tidak', 'Tidak', 'Ya', 'Tidak', '0', '0', '3', '0', '0', '5', '0', 'Buruh harian lepas', '1200000', '1100000'],
  // Desil 6 — Rentan, pendapatan menengah bawah
  ['4', 'Endah Kusumawati', '3573010101920004', 'JAWA TIMUR', 'KOTA MALANG', 'LOWOKWARU', 'MOJOLANGU', '004', '002', 'Jl. Simpang Borobudur No. 21', '3', 'Non-PBI', 'Tidak', '45', 'Keramik', 'Tembok', 'Genteng', 'PDAM/air ledeng', 'PLN', '1300', 'Gas LPG', 'Sendiri', 'Leher angsa', 'Septic tank', 'Tidak', 'Tidak', 'Ya', 'Ya', 'Tidak', 'Ya', 'Tidak', 'Ya', 'Tidak', '0', '0', '0', '0', '0', '0', '0', 'Pedagang/wiraswasta', '2500000', '2200000'],
  // Desil 8 — Non-miskin, aset lengkap
  ['5', 'Rendra Wijaya', '3573010101880005', 'JAWA TIMUR', 'KOTA MALANG', 'KEDUNGKANDANG', 'ARJOWINANGUN', '006', '001', 'Jl. Mayjen Sungkono No. 15', '4', 'Non-PBI', 'Tidak', '72', 'Keramik', 'Tembok', 'Genteng', 'PDAM/air ledeng', 'PLN', '2200', 'Gas LPG', 'Sendiri', 'Leher angsa', 'Septic tank', 'Ya', 'Tidak', 'Ya', 'Ya', 'Ya', 'Ya', 'Tidak', 'Ya', 'Ya', '0', '0', '0', '0', '0', '0', '0', 'Karyawan swasta', '5000000', '4000000']
];

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info', duration = 3000) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  toastContainer.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(20px)'; t.style.transition = 'all 0.3s'; setTimeout(() => t.remove(), 320); }, duration);
}

// ── Server Health Check ───────────────────────────────────────────────────────
async function checkHealth() {
  statusDot.className = 'status-dot loading';
  statusText.textContent = 'Memeriksa...';
  try {
    const headers = {};
    if (CFG.apiKey) headers['X-API-Key'] = CFG.apiKey;
    const r = await fetch(`${CFG.apiUrl}/health`, {
      headers,
      signal: AbortSignal.timeout(5000),
      credentials: 'include' // Penting buat lintas-node AI Hub
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    if (data.model_loaded) {
      statusDot.className = 'status-dot online';
      statusText.textContent = `Online · ${data.device?.toUpperCase() || '?'} · ${data.gpu_name || 'CPU'}`;
    } else {
      statusDot.className = 'status-dot loading';
      statusText.textContent = 'Server aktif – Model loading...';
    }
  } catch (e) {
    statusDot.className = 'status-dot offline';
    statusText.textContent = 'Server tidak terhubung';
  }
}

// ── Settings Modal ────────────────────────────────────────────────────────────
settingsBtn.onclick = () => {
  apiUrlInput.value = CFG.apiUrl;
  apiKeyInput.value = CFG.apiKey;
  maxTokensInput.value = CFG.maxNewTokens;
  settingsModal.classList.add('open');
};

function closeModal() { settingsModal.classList.remove('open'); }
closeSettings.onclick = closeModal;
cancelSettings.onclick = closeModal;
settingsModal.onclick = (e) => { if (e.target === settingsModal) closeSettings.click(); };

// ── Manual Input Modal ────────────────────────────────────────────────────────
manualInputBtn.onclick = () => {
  manualModal.classList.add('open');
};

function closeManualModal() {
  manualModal.classList.remove('open');
  manualForm.reset();
}
closeManual.onclick = closeManualModal;
cancelManual.onclick = closeManualModal;
manualModal.onclick = (e) => { if (e.target === manualModal) closeManualModal(); };

submitManual.onclick = async () => {
  if (!manualForm.reportValidity()) return;

  const formData = new FormData(manualForm);
  const data = {};

  // Convert formData to object (handle checkboxes)
  formData.forEach((value, key) => {
    data[key] = value;
  });

  // Handle checkboxes properly (FormData only includes checked ones)
  const checkboxes = manualForm.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => {
    data[cb.name] = cb.checked ? 'Ya' : 'Tidak';
  });

  const profileText = buildProfileText(data);
  const nama = data['nama_pm'] || 'Data Manual';

  closeManualModal();
  showLoading(`Menganalisis: ${nama}`, 'Memproses data input manual...');

  try {
    const result = await callPredict(profileText);
    hideLoading();
    renderResult(999, data, profileText, result); // Gunakan idx dummy 999
    showToast(`Analisis manual selesai: ${nama}`, 'success');
  } catch (err) {
    hideLoading();
    showToast(`Gagal: ${err.message}`, 'error');
  }
};

saveSettings.onclick = async () => {
  CFG.apiUrl = apiUrlInput.value.trim().replace(/\/$/, '');
  CFG.apiKey = apiKeyInput.value.trim();
  CFG.maxNewTokens = parseInt(maxTokensInput.value) || 512;
  saveConfig(CFG);
  closeModal();
  showToast('Pengaturan disimpan!', 'success');
  await checkHealth();
};

// ── Template Download ─────────────────────────────────────────────────────────
downloadTemplate.onclick = () => {
  const header = CSV_COLUMNS.join(',');
  const rows = TEMPLATE_ROWS.map(r => r.map(v => `"${v}"`).join(','));
  const csv = [header, ...rows].join('\n');

  // Tambahkan BOM (\ufeff) supaya Excel langsung deteksi csv-nya punya kolom (ga gabung)
  const blob = new Blob(["\ufeff" + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = 'template_aitf_profil_keluarga.csv';

  document.body.appendChild(a);
  a.click();

  // Cleanup
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 100);

  showToast('Template CSV berhasil diunduh!', 'success');
};

// ── CSV Parsing ───────────────────────────────────────────────────────────────
function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) throw new Error('CSV minimal harus 2 baris (header + data)');

  // Parse headers
  const headers = splitCSVLine(lines[0]);
  const rows = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const vals = splitCSVLine(line);
    const obj = {};
    headers.forEach((h, idx) => { obj[h.trim().toLowerCase()] = (vals[idx] || '').trim(); });
    rows.push(obj);
  }
  return { headers, rows };
}

function splitCSVLine(line) {
  // Handle quoted fields
  const result = [];
  let cur = '';
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') { inQuote = !inQuote; }
    else if (ch === ',' && !inQuote) { result.push(cur); cur = ''; }
    else { cur += ch; }
  }
  result.push(cur);
  return result;
}

// ── Build Text Profil (format SFT — harus SAMA persis dengan data training) ────
function buildProfileText(row) {
  const g = key => (row[key.toLowerCase()] || '').trim();
  const has = v => v && v.toLowerCase() !== 'tidak' && v !== '0' && v !== '-';
  const num = v => { const n = parseInt(v); return isNaN(n) ? 0 : n; };

  // Fungsi normalisasi agar nilai sesuai dengan kosakata (vocabulary) training
  const norm = (val, map = {}) => {
    if (!val) return 'lainnya';
    const low = val.toLowerCase().trim();
    if (map[low]) return map[low];
    return low;
  };

  // ── [Demografi & Lokasi] ──────────────────────────────────────────────────
  const kel = g('kel_nama') || 'Mergosono';
  const kec = g('kec_nama') || 'Kedungkandang';
  const kab = g('kab_nama') || 'Kota Malang';
  const prov = g('prov_nama') || 'Jawa Timur';

  let seksi1 = `Keluarga ini berlokasi di Kelurahan ${kel}, Kecamatan ${kec}, ${kab}, Provinsi ${prov}. `;
  seksi1 += `Keluarga terdiri dari ${g('jumlah_art') || '4'} orang anggota. `;

  const pbi = g('status_pbi').toLowerCase();
  const isPbi = pbi.includes('pbi') && !pbi.includes('non');

  if (isPbi) {
    seksi1 += `Keluarga ini tercatat sebagai penerima Bantuan Iuran Jaminan Kesehatan Nasional (PBI-JKN).`;
  } else {
    seksi1 += `Keluarga ini tidak tercatat sebagai penerima bantuan iuran (non-PBI).`;
  }

  // ── [Kondisi Perumahan] ───────────────────────────────────────────────────
  const luas = g('luas_lantai') || '36';

  // Mapping kosakata khusus SFT
  const mapLantai = { 'keramik': 'keramik', 'tanah': 'tanah', 'semen': 'semen/bata merah', 'ubin': 'semen/bata merah', 'papan': 'kayu/papan' };
  const mapDinding = { 'tembok': 'tembok', 'batako': 'tembok', 'bambu': 'bambu', 'gedek': 'anyaman bambu', 'kayu': 'kayu/papan/gypsum/GRC/calciboard' };
  const mapAtap = { 'genteng': 'genteng', 'asbes': 'asbes', 'seng': 'seng', 'daun': 'jerami/ijuk/daun-daunan/rumbia', 'jerami': 'jerami/ijuk/daun-daunan/rumbia' };
  const mapAir = { 'pdam': 'leding/PDAM', 'ledeng': 'leding/PDAM', 'sumur': 'sumur terlindung', 'isi ulang': 'air isi ulang' };
  const mapTinja = { 'septic tank': 'tangki septik', 'septictank': 'tangki septik', 'sungai': 'kolam/sawah/sungai/danau/laut', 'kebun': 'pantai/tanah lapang/kebun' };

  let seksi2 = `Mereka menempati rumah berstatus milik sendiri dengan luas lantai ${luas} meter persegi. `;
  seksi2 += `Jenis lantai: ${norm(g('jenis_lantai'), mapLantai)}; dinding: ${norm(g('jenis_dinding'), mapDinding)}; atap: ${norm(g('jenis_atap'), mapAtap)}. `;
  seksi2 += `Sumber air minum utama dari ${norm(g('sumber_air_minum'), mapAir)}. `;

  // Penerangan — model dilatih dengan kalimat spesifik
  const peneranganRaw = g('penerangan').toLowerCase();
  if (peneranganRaw.includes('bukan listrik') || peneranganRaw.includes('minyak') || peneranganRaw.includes('lilin')) {
    seksi2 += `Penerangan utama bukan listrik (bukan listrik (lampu minyak/lilin/obor)). `;
  } else {
    const daya = g('daya_listrik') || '900';
    seksi2 += `Penerangan utama menggunakan listrik PLN dengan meteran dengan daya terpasang ${daya} watt. `;
  }

  seksi2 += `Bahan bakar utama untuk memasak adalah ${g('bahan_bakar_masak').toLowerCase() || 'gas elpiji 3 kg'}. `;

  // Sanitasi
  const fasBAB = g('fasilitas_bab').toLowerCase();
  const hasFas = fasBAB.includes('ada') || fasBAB.includes('ya') || fasBAB.includes('sendiri');
  if (hasFas) {
    seksi2 += `Fasilitas BAB: ada, digunakan sendiri oleh anggota keluarga, dengan jenis kloset ${g('jenis_kloset').toLowerCase() || 'leher angsa'} dan pembuangan akhir tinja ke ${norm(g('pembuangan_tinja'), mapTinja)}.`;
  } else {
    seksi2 += `Fasilitas BAB: tidak ada fasilitas BAB, dengan jenis kloset ${g('jenis_kloset').toLowerCase() || 'cemplung/cubluk'} dan pembuangan akhir tinja ke ${norm(g('pembuangan_tinja'), mapTinja)}.`;
  }

  // ── [Kepemilikan Aset & Ternak] ───────────────────────────────────────────
  const asetList = [];
  if (has(g('aset_tv'))) asetList.push('televisi datar');
  if (has(g('aset_hp'))) asetList.push('smartphone');
  if (has(g('aset_laptop'))) asetList.push('komputer/laptop/tablet');
  if (has(g('aset_kulkas'))) asetList.push('lemari es/kulkas');
  if (has(g('aset_ac'))) asetList.push('AC (air conditioner)');
  if (has(g('aset_motor'))) asetList.push('sepeda motor');
  if (has(g('aset_mobil'))) asetList.push('mobil');

  let seksi3 = asetList.length > 0
    ? `Aset bergerak yang dimiliki: ${asetList.join(', ')}. `
    : `Tidak memiliki aset bergerak yang tercatat. `;

  if (has(g('punya_lahan_lain')) || has(g('punya_rumah_lain'))) {
    const r = [];
    if (has(g('punya_lahan_lain'))) r.push('lahan lain selain yang dihuni');
    if (has(g('punya_rumah_lain'))) r.push('rumah lain selain yang dihuni');
    seksi3 += `Memiliki aset tidak bergerak berupa: ${r.join(', ')}. `;
  } else {
    seksi3 += `Tidak memiliki lahan atau rumah lain selain yang dihuni. `;
  }

  // Ternak
  const ternak = [];
  if (num(g('ternak_sapi'))) ternak.push(`${g('ternak_sapi')} ekor sapi`);
  if (num(g('ternak_kambing'))) ternak.push(`${g('ternak_kambing')} ekor kambing/domba`);
  if (num(g('ternak_ayam'))) ternak.push(`${g('ternak_ayam')} ekor ayam`);

  seksi3 += ternak.length > 0
    ? `Hewan ternak yang dimiliki: ${ternak.join(', ')}.`
    : `Tidak memiliki hewan ternak.`;

  // ── Gabungkan ─────────────────────────────────────────────────────────────
  return `Profil Keluarga:\n\n[Demografi & Lokasi]\n${seksi1}\n\n[Kondisi Perumahan]\n${seksi2}\n\n[Kepemilikan Aset & Ternak]\n${seksi3}`.trim();
}

// ── File drop & select ────────────────────────────────────────────────────────
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});
dropZone.addEventListener('click', () => csvFileInput.click());
csvFileInput.addEventListener('change', () => {
  if (csvFileInput.files[0]) handleFile(csvFileInput.files[0]);
});

clearFileBtn.addEventListener('click', () => {
  csvData = []; csvHeaders = [];
  fileInfo.style.display = 'none';
  tableCard.style.display = 'none';
  csvFileInput.value = '';
  showToast('File dihapus', 'info');
});

function handleFile(file) {
  if (!file.name.endsWith('.csv')) {
    showToast('Hanya file .csv yang diterima', 'error');
    return;
  }
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const { headers, rows } = parseCSV(e.target.result);
      csvHeaders = headers;
      csvData = rows;

      // Show file info
      fileInfo.style.display = 'flex';
      fileName.textContent = file.name;
      fileMeta.textContent = `${rows.length} baris  ·  ${headers.length} kolom  ·  ${(file.size / 1024).toFixed(1)} KB`;

      renderTable();
      showToast(`CSV berhasil dimuat: ${rows.length} baris data`, 'success');
    } catch (err) {
      showToast(`Error parsing CSV: ${err.message}`, 'error');
    }
  };
  reader.readAsText(file);
}

// ── Render Table ──────────────────────────────────────────────────────────────
// Kolom penting untuk preview (ambil maks 8 kolom pertama + aksi)
// Kolom yang ditampilkan di tabel preview — sesuai kolom yang relevan dengan model
const PREVIEW_COLS_PRIORITY = [
  'no', 'nama_PM', 'kec_nama', 'kel_nama',
  'jumlah_art', 'status_pbi', 'jenis_lantai', 'jenis_dinding',
];

function renderTable() {
  // Pick preview columns
  const allLower = csvHeaders.map(h => h.toLowerCase());
  const previewCols = [];

  for (const pc of PREVIEW_COLS_PRIORITY) {
    const idx = allLower.indexOf(pc);
    if (idx !== -1) previewCols.push(csvHeaders[idx]);
  }

  // Fill up to 7 cols if we have extras
  for (const h of csvHeaders) {
    if (previewCols.length >= 7) break;
    if (!previewCols.includes(h)) previewCols.push(h);
  }

  // Head
  tableHead.innerHTML = '<tr>' +
    '<th>#</th>' +
    previewCols.map(h => `<th>${h}</th>`).join('') +
    '<th>Aksi</th>' +
    '</tr>';

  // Body
  tableBody.innerHTML = csvData.map((row, i) => {
    const cells = previewCols.map(h => `<td>${escHtml(row[h.toLowerCase()] || '')}</td>`).join('');
    return `<tr id="row-${i}">
      <td><span class="row-num">${i + 1}</span></td>
      ${cells}
      <td class="cell-action">
        <button class="btn btn-success btn-sm" onclick="handleAnalyze(${i})" id="btn-analyze-${i}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Analisis
        </button>
        <button class="btn btn-outline btn-sm" onclick="handlePreviewText(${i})" id="btn-preview-${i}" title="Preview teks profil">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      </td>
    </tr>`;
  }).join('');

  rowCount.textContent = `${csvData.length} baris`;
  tableCard.style.display = 'block';
}

function renderResult(idx, row, profileText, apiResult) {
  resultCount++;
  resultsPanel.style.display = 'block';

  const rawText = apiResult.result || '';
  const elapsed = apiResult.elapsed_seconds;
  const nama = row['nama_pm'] || row['no'] || `Baris ${idx + 1}`;
  const lokasi = [row['kel_nama'], row['kec_nama'], row['kab_nama']].filter(Boolean).join(', ') || '-';

  const parsed = parseModelOutput(rawText);
  const cardId = `result-card-${resultCount}`;
  const div = document.createElement('div');
  div.className = 'result-card';
  div.id = cardId;

  const skorDisplay = parsed.skor !== null ? parsed.skor : '—';
  const desilDisplay = parsed.desil !== null ? parsed.desil : '—';

div.innerHTML = `
    <div class="result-card-header">
      <div class="result-meta">
        <span class="result-label">📋 ${escHtml(nama)} &nbsp;·&nbsp; <span style="color:var(--text-muted);font-weight:400;font-size:12px">${escHtml(lokasi)}</span></span>
        <div style="display:flex;gap:8px;margin-top:4px;flex-wrap:wrap">
          <span class="elapsed-badge">⏱ ${elapsed}s</span>
          <span class="elapsed-badge">📄 ${apiResult.input_length} karakter input</span>
          <span class="elapsed-badge">Baris #${idx + 1}</span>
        </div>
      </div>
      <div class="result-scores">
        <div class="score-chip skor">
          <span class="score-chip-label">Skor</span>
          <span class="score-chip-value">${skorDisplay}</span>
        </div>
        <div class="score-chip desil">
          <span class="score-chip-label">Desil</span>
          <span class="score-chip-value">${desilDisplay}</span>
        </div>
      </div>
    </div>

    <!-- Toggle input -->
    <button class="result-input-toggle" onclick="toggleInputPreview('input-${cardId}', this)">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
      </svg>
      Lihat teks profil yang dikirim ke API
    </button>
    <div class="result-input-preview" id="input-${cardId}">
      <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: var(--font-mono); font-size: 13px;">${escHtml(profileText)}</pre>
    </div>

    <!-- Analysis -->
    <div class="result-analysis">
      ${renderParsedSections(parsed, rawText)}
    </div>
  `;

// Prepend so newest is at top
resultsList.prepend(div);

}

function toggleInputPreview(id, btn) {
  const el = document.getElementById(id);
  const isOpen = el.classList.toggle('open');
  btn.style.color = isOpen ? 'var(--indigo-light)' : '';
}

function parseModelOutput(text) {
  const parsed = { analisis: null, reasoning: null, skor: null, desil: null };

  // Analisis Kondisi
  const analisisM = text.match(/Analisis Kondisi[:\s]+([\s\S]*?)(?=Reasoning:|$)/i);
  if (analisisM) parsed.analisis = analisisM[1].trim();

  // Reasoning
  const reasoningM = text.match(/Reasoning[:\s]+([\s\S]*?)(?=Skor Evaluasi:|Desil Nasional:|$)/i);
  if (reasoningM) parsed.reasoning = reasoningM[1].trim();

  // Skor Evaluasi
  const skorM = text.match(/Skor Evaluasi[:\s]*([\d.]+)/i);
  if (skorM) parsed.skor = parseFloat(skorM[1]).toFixed(1);

  // Desil Nasional
  const desilM = text.match(/Desil Nasional[:\s]*(\d+)/i);
  if (desilM) parsed.desil = parseInt(desilM[1]);

  return parsed;
}

function renderParsedSections(parsed, rawText) {
  const hasAny = parsed.analisis || parsed.reasoning || parsed.skor !== null || parsed.desil !== null;

  if (!hasAny) {
    return `
      <div class="result-analysis-section">
        <h4 class="section-raw">Output Mentah Model</h4>
        <pre class="result-raw" style="white-space: pre-wrap; word-wrap: break-word; font-size: 13px;">${escHtml(rawText)}</pre>
      </div>`;
  }

  let html = '';

  if (parsed.analisis) {
    html += `
      <div class="result-analysis-section">
        <h4 class="section-analisis">🔍 Analisis Kondisi</h4>
        <p>${escHtml(parsed.analisis).replace(/\n/g, '<br>')}</p>
      </div>`;
  }

  if (parsed.reasoning) {
    html += `
      <div class="result-analysis-section">
        <h4 class="section-reasoning">💡 Reasoning</h4>
        <p>${escHtml(parsed.reasoning).replace(/\n/g, '<br>')}</p>
      </div>`;
  }

  if (parsed.skor !== null || parsed.desil !== null) {
    html += `
      <div class="result-analysis-section" style="display:flex;gap:16px;align-items:center">`;
    if (parsed.skor !== null) {
      html += `<div>
        <h4 class="section-skor" style="margin-bottom:2px">📊 Skor Evaluasi</h4>
        <p style="font-size:24px;font-weight:800;color:var(--indigo-light);font-family:var(--font-mono)">${parsed.skor}</p>
      </div>`;
    }
    if (parsed.desil !== null) {
      html += `<div>
        <h4 class="section-desil" style="margin-bottom:2px">📈 Desil Nasional</h4>
        <p style="font-size:24px;font-weight:800;color:var(--purple);font-family:var(--font-mono)">${parsed.desil}<span style="font-size:14px;font-weight:400;color:var(--text-muted)">/10</span></p>
      </div>
      <div style="flex:1">
        ${renderDesilBar(parsed.desil)}
      </div>`;
    }
    html += `</div>`;
  }

  return html;
}

function renderDesilBar(desil) {
  const pct = (desil / 10) * 100;
  const color = desil <= 3 ? '#ef4444' : desil <= 6 ? '#f59e0b' : '#10b981';
  const label = desil <= 3 ? 'Sangat Miskin / Miskin' : desil <= 6 ? 'Rentan' : 'Non-Miskin';
  return `
    <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">${label}</div>
    <div class="progress-bar-wrap">
      <div class="progress-bar" style="width:${pct}%;background:${color}"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-top:4px">
      <span>Desil 1</span><span>Desil 10</span>
    </div>`;
}

// ── Clear results ─────────────────────────────────────────────────────────────
clearResultsBtn.addEventListener('click', () => {
  resultsList.innerHTML = '';
  resultsPanel.style.display = 'none';
  resultCount = 0;
  showToast('Semua hasil dihapus', 'info');
});

// ── Loading ───────────────────────────────────────────────────────────────────
function showLoading(text, sub) {
  loadingText.textContent = text || 'Memproses...';
  loadingSub.textContent = sub || '';
  loadingOverlay.style.display = 'flex';
}

function hideLoading() {
  loadingOverlay.style.display = 'none';
}

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  apiUrlInput.value = CFG.apiUrl;
  apiKeyInput.value = CFG.apiKey;
  maxTokensInput.value = CFG.maxNewTokens;

  checkHealth();
  // Recheck health every 30s
  setInterval(checkHealth, 30000);
});

// ── Utilities ─────────────────────────────────────────────────────────────────
function escHtml(unsafe) {
  if (!unsafe) return '';
  return String(unsafe)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ── API Calling ───────────────────────────────────────────────────────────────
async function callPredict(text) {
  const headers = { 'Content-Type': 'application/json' };
  if (CFG.apiKey) headers['X-API-Key'] = CFG.apiKey;

  const res = await fetch(`${CFG.apiUrl}/predict`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      text: text,
      max_new_tokens: CFG.maxNewTokens
    })
  });

  if (!res.ok) {
    let msg = `Error HTTP ${res.status}`;
    try {
      const errData = await res.json();
      if (errData.detail) msg += `: ${errData.detail}`;
    } catch(e) {}
    throw new Error(msg);
  }

  return await res.json();
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function handleAnalyze(idx) {
  const row = csvData[idx];
  if (!row) return;

  const btn = document.getElementById(`btn-analyze-${idx}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = 'Proses...';
  }

  const profileText = buildProfileText(row);
  const nama = row['nama_pm'] || row['no'] || `Baris ${idx + 1}`;

  showLoading(`Menganalisis: ${nama}`, 'Menghubungi API model...');

  try {
    const result = await callPredict(profileText);
    renderResult(idx, row, profileText, result);
    showToast(`Analisis baris ${idx + 1} selesai`, 'success');
  } catch (err) {
    showToast(`Gagal pada baris ${idx + 1}: ${err.message}`, 'error');
  } finally {
    hideLoading();
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Analisis';
    }
  }
}

function handlePreviewText(idx) {
  const row = csvData[idx];
  if (!row) return;
  const profileText = buildProfileText(row);
  alert("Pratinjau Topik Profil yang dikirim ke API:\n\n" + profileText);
}

if (analyzeAllBtn) {
  analyzeAllBtn.addEventListener('click', async () => {
    if (!csvData.length) {
        showToast('Tidak ada data CSV', 'error');
        return;
    }
    const limit = prompt("Berapa baris yang ingin dianalisis otomatis? (Mulai dari baris pertama)", "5");
    if (limit === null) return;
    
    const count = parseInt(limit);
    if (isNaN(count) || count <= 0) return;

    for (let i = 0; i < Math.min(count, csvData.length); i++) {
        showLoading(`Proses Batch (${i+1}/${count})`, `Analisis data: ${csvData[i].nama_pm || 'Baris '+ (i+1)}`);
        try {
            const profileText = buildProfileText(csvData[i]);
            const result = await callPredict(profileText);
            renderResult(i, csvData[i], profileText, result);
            showToast(`Selesai [${i+1}/${count}]`, 'success', 1500);
            
            // Beri jeda sedikit agar UI responsif dan API tidak terlalu tertekan
            await new Promise(r => setTimeout(r, 500));
        } catch(err) {
            showToast(`Gagal baris ${i+1}: ${err.message}`, 'error');
        }
    }
    hideLoading();
    showToast(`Analisis Batch Selesai!`, 'success');
  });
}

// Expose to inline handlers
window.handleAnalyze = handleAnalyze;
window.handlePreviewText = handlePreviewText;
window.toggleInputPreview = toggleInputPreview;
