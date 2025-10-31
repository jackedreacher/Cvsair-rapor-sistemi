const chokidar = require('chokidar');
const path = require('path');
const fs = require('fs');
const { convertExcelToCsv, findExcelFile } = require('./excel-to-csv');

// Excel dosyası pattern'i
// Simplified pattern - just check for .xlsx files containing 'ALINAN'
function isTargetExcelFile(filename) {
  return filename.endsWith('.xlsx') && filename.includes('ALINAN');
}
const OUTPUT_CSV = 'orders.csv';

function startWatching() {
  console.log('📁 Dosya izleyici başlatılıyor...');
  console.log('🔍 Excel dosyası değişiklikleri izleniyor...');
  
  // Mevcut dizini izle
  const watcher = chokidar.watch(__dirname, {
    ignored: /(^|[\/\\])\../, // gizli dosyaları yoksay
    persistent: true,
    ignoreInitial: false
  });
  
  // Başlangıçta mevcut dosyaları kontrol et
   const files = fs.readdirSync(__dirname);
   const existingExcelFile = files.find(file => isTargetExcelFile(file));
 
   if (existingExcelFile) {
     console.log(`📁 Mevcut Excel dosyası bulundu: ${existingExcelFile}`);
     const excelPath = path.join(__dirname, existingExcelFile);
     const csvPath = path.join(__dirname, OUTPUT_CSV);
     convertExcelToCsv(excelPath, csvPath);
   } else {
     console.log('⚠️ Henüz Excel dosyası bulunamadı. Dosya eklenmesi bekleniyor...');
   }
  
  // Dosya değişikliklerini izle
  watcher
    .on('add', filePath => {
      const fileName = path.basename(filePath);
      if (isTargetExcelFile(fileName)) {
        console.log(`➕ Yeni Excel dosyası eklendi: ${fileName}`);
        const csvPath = path.join(__dirname, OUTPUT_CSV);
        convertExcelToCsv(filePath, csvPath);
      }
    })
    .on('change', filePath => {
      const fileName = path.basename(filePath);
      if (isTargetExcelFile(fileName)) {
        console.log(`🔄 Excel dosyası güncellendi: ${fileName}`);
        const csvPath = path.join(__dirname, OUTPUT_CSV);
        convertExcelToCsv(filePath, csvPath);
      }
    })
    .on('unlink', filePath => {
      const fileName = path.basename(filePath);
      if (isTargetExcelFile(fileName)) {
        console.log(`🗑️ Excel dosyası silindi: ${fileName}`);
      }
    })
    .on('error', error => {
      console.error('❌ Dosya izleyici hatası:', error);
    });
  
  console.log('✅ Dosya izleyici aktif!');
  console.log('💡 Excel dosyanızı güncelleyin, otomatik olarak CSV\'ye dönüştürülecek.');
  console.log('⏹️ Durdurmak için Ctrl+C tuşlayın.');
  
  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n🛑 Dosya izleyici durduruluyor...');
    watcher.close();
    process.exit(0);
  });
}

// Eğer bu dosya doğrudan çalıştırılıyorsa
if (require.main === module) {
  startWatching();
}

module.exports = { startWatching };