const XLSX = require('xlsx');
const fs = require('fs-extra');
const path = require('path');

// Excel dosyasının yolu
const EXCEL_FILE_PATTERN = /ALINAN.*S[İI]PAR[İI][ŞS].*LER.*\.xlsx$/i;
const OUTPUT_CSV = 'orders.csv';

function findExcelFile() {
  const files = fs.readdirSync(__dirname);
  const xlsxFiles = files.filter(f => f.endsWith('.xlsx') && f.includes('ALINAN'));
  return xlsxFiles.length > 0 ? xlsxFiles[0] : null;
}

function convertExcelToCSV(excelFilePath, csvFilePath) {
  try {
    console.log(`Excel dosyası okunuyor: ${excelFilePath}`);
    
    // Excel dosyasını oku
    const workbook = XLSX.readFile(excelFilePath);
    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];
    
    // CSV formatına çevir
    const csvData = XLSX.utils.sheet_to_csv(worksheet);
    
    // CSV dosyasını kaydet
    fs.writeFileSync(csvFilePath, csvData, 'utf8');
    
    console.log(`CSV dosyası oluşturuldu: ${csvFilePath}`);
    console.log(`Dönüştürme tamamlandı: ${new Date().toLocaleString('tr-TR')}`);
    
    return true;
  } catch (error) {
    console.error('Dönüştürme hatası:', error.message);
    return false;
  }
}

function main() {
  const excelFile = findExcelFile();
  
  if (!excelFile) {
    console.error('Excel dosyası bulunamadı! Dosya adı "ALINAN SİPARİŞ" içermeli ve .xlsx uzantılı olmalı.');
    process.exit(1);
  }
  
  const excelPath = path.join(__dirname, excelFile);
  const csvPath = path.join(__dirname, OUTPUT_CSV);
  
  console.log(`Bulunan Excel dosyası: ${excelFile}`);
  
  const success = convertExcelToCSV(excelPath, csvPath);
  
  if (success) {
    console.log('✅ Dönüştürme başarılı!');
  } else {
    console.log('❌ Dönüştürme başarısız!');
    process.exit(1);
  }
}

// Export functions for use in other modules
module.exports = {
  convertExcelToCsv: convertExcelToCSV,
  findExcelFile
};

// Run main function if this file is executed directly
if (require.main === module) {
  main()
    .then(() => {
      console.log('✅ Dönüştürme başarılı!');
    })
    .catch((error) => {
      console.error('❌ Hata:', error.message);
      process.exit(1);
    });
}