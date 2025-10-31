// CVSAir Edit Controls System
class EditControlsManager {
    constructor() {
        this.isEditMode = false;
        this.originalContent = {};
        this.newElements = [];
        this.init();
    }

    init() {
        this.createEditControls();
        this.setupEventListeners();
    }

    createEditControls() {
        const editControlsHTML = `
            <div id="edit-controls" class="fixed top-4 right-4 z-50 bg-white shadow-lg rounded-lg p-4 border">
                <div class="flex flex-col space-y-2">
                    <button id="edit-btn" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
                        Düzenle
                    </button>
                    <button id="save-btn" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors" style="display: none;">
                        Kaydet ve İndir
                    </button>
                    <button id="cancel-btn" class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors" style="display: none;">
                        İptal
                    </button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', editControlsHTML);
    }

    setupEventListeners() {
        document.getElementById('edit-btn').addEventListener('click', () => this.enableEditMode());
        document.getElementById('save-btn').addEventListener('click', () => this.saveAndDownload());
        document.getElementById('cancel-btn').addEventListener('click', () => this.disableEditMode());
    }

    enableEditMode() {
        this.isEditMode = true;
        document.body.classList.add('edit-mode');
        
        // Show/hide buttons
        document.getElementById('edit-btn').style.display = 'none';
        document.getElementById('save-btn').style.display = 'block';
        document.getElementById('cancel-btn').style.display = 'block';
        
        // Make elements with data-i18n editable
        document.querySelectorAll('[data-i18n]').forEach(element => {
            if (!this.originalContent[element.getAttribute('data-i18n')]) {
                this.originalContent[element.getAttribute('data-i18n')] = element.textContent;
            }
            element.contentEditable = true;
            element.classList.add('editable-element');
        });
        
        // Add "Ekle" buttons to sections
        this.addSectionButtons();
    }

    disableEditMode() {
        this.isEditMode = false;
        document.body.classList.remove('edit-mode');
        
        // Show/hide buttons
        document.getElementById('edit-btn').style.display = 'block';
        document.getElementById('save-btn').style.display = 'none';
        document.getElementById('cancel-btn').style.display = 'none';
        
        // Restore original content and disable editing
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (this.originalContent[key]) {
                element.textContent = this.originalContent[key];
            }
            element.contentEditable = false;
            element.classList.remove('editable-element');
        });
        
        // Remove new elements and add buttons
        this.removeNewElements();
        this.removeAddButtons();
        
        // Clear stored data
        this.originalContent = {};
        this.newElements = [];
    }

    addSectionButtons() {
        const sections = [
            '.grid.grid-cols-1.md\\:grid-cols-2.gap-6', // Technical specs section
            '.space-y-6', // Various sections
            '.grid.grid-cols-1.md\\:grid-cols-3.gap-6' // Three-column sections
        ];
        
        sections.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                if (!element.querySelector('.add-controls')) {
                    this.addControlsToElement(element);
                }
            });
        });
    }

    addControlsToElement(element) {
        const addControlsHTML = `
            <div class="add-controls mt-4 p-3 border-2 border-dashed border-blue-300 rounded-lg bg-blue-50">
                <div class="flex flex-wrap gap-2">
                    <button class="add-card-btn px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600">
                        Kart Ekle
                    </button>
                    <button class="add-list-btn px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600">
                        Liste Ekle
                    </button>
                    <button class="add-text-btn px-3 py-1 bg-purple-500 text-white text-sm rounded hover:bg-purple-600">
                        Metin Ekle
                    </button>
                </div>
            </div>
        `;
        
        element.insertAdjacentHTML('beforeend', addControlsHTML);
        
        // Add event listeners
        const addCardBtn = element.querySelector('.add-card-btn');
        const addListBtn = element.querySelector('.add-list-btn');
        const addTextBtn = element.querySelector('.add-text-btn');
        
        addCardBtn.addEventListener('click', () => this.addNewCard(element));
        addListBtn.addEventListener('click', () => this.addNewList(element));
        addTextBtn.addEventListener('click', () => this.addNewText(element));
    }

    addNewCard(container) {
        const cardId = `new-card-${Date.now()}`;
        const cardHTML = `
            <div class="new-content bg-yellow-50 border-2 border-yellow-300 rounded-lg p-6" data-new-element="${cardId}">
                <h3 class="text-lg font-semibold mb-3 editable-element" contenteditable="true" data-i18n="${cardId}-title">
                    Yeni Kart Başlığı
                </h3>
                <p class="text-gray-600 editable-element" contenteditable="true" data-i18n="${cardId}-content">
                    Yeni kart içeriği buraya yazılacak. Bu alanı düzenleyebilirsiniz.
                </p>
            </div>
        `;
        
        const addControls = container.querySelector('.add-controls');
        addControls.insertAdjacentHTML('beforebegin', cardHTML);
        
        this.newElements.push(cardId);
    }

    addNewList(container) {
        const listId = `new-list-${Date.now()}`;
        const listHTML = `
            <div class="new-content bg-green-50 border-2 border-green-300 rounded-lg p-6" data-new-element="${listId}">
                <h3 class="text-lg font-semibold mb-3 editable-element" contenteditable="true" data-i18n="${listId}-title">
                    Yeni Liste Başlığı
                </h3>
                <ul class="space-y-2">
                    <li class="flex items-start">
                        <span class="text-blue-600 mr-2">•</span>
                        <span class="editable-element" contenteditable="true" data-i18n="${listId}-item1">Liste öğesi 1</span>
                    </li>
                    <li class="flex items-start">
                        <span class="text-blue-600 mr-2">•</span>
                        <span class="editable-element" contenteditable="true" data-i18n="${listId}-item2">Liste öğesi 2</span>
                    </li>
                    <li class="flex items-start">
                        <span class="text-blue-600 mr-2">•</span>
                        <span class="editable-element" contenteditable="true" data-i18n="${listId}-item3">Liste öğesi 3</span>
                    </li>
                </ul>
            </div>
        `;
        
        const addControls = container.querySelector('.add-controls');
        addControls.insertAdjacentHTML('beforebegin', listHTML);
        
        this.newElements.push(listId);
    }

    addNewText(container) {
        const textId = `new-text-${Date.now()}`;
        const textHTML = `
            <div class="new-content bg-purple-50 border-2 border-purple-300 rounded-lg p-6" data-new-element="${textId}">
                <p class="text-gray-700 editable-element" contenteditable="true" data-i18n="${textId}-content">
                    Yeni metin içeriği buraya yazılacak. Bu alanı düzenleyebilirsiniz.
                </p>
            </div>
        `;
        
        const addControls = container.querySelector('.add-controls');
        addControls.insertAdjacentHTML('beforebegin', textHTML);
        
        this.newElements.push(textId);
    }

    removeNewElements() {
        document.querySelectorAll('.new-content').forEach(element => {
            element.remove();
        });
    }

    removeAddButtons() {
        document.querySelectorAll('.add-controls').forEach(element => {
            element.remove();
        });
    }

    saveAndDownload() {
        // Update translations with new content
        const updatedTranslations = { ...translations };
        
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const content = element.textContent.trim();
            
            if (content) {
                // Update both languages with the same content for new elements
                if (this.newElements.some(id => key.includes(id))) {
                    updatedTranslations.en[key] = content;
                    updatedTranslations.tr[key] = content;
                } else {
                    // Update current language
                    updatedTranslations[currentLanguage][key] = content;
                }
            }
        });
        
        // Get current HTML
        let htmlContent = document.documentElement.outerHTML;
        
        // Update the translations object in the HTML
        const translationsRegex = /const translations = \{[\s\S]*?\};/;
        const newTranslationsString = `const translations = ${JSON.stringify(updatedTranslations, null, 4)};`;
        htmlContent = htmlContent.replace(translationsRegex, newTranslationsString);
        
        // Remove edit controls and new content styling from the HTML
        htmlContent = htmlContent.replace(/<div id="edit-controls"[\s\S]*?<\/div>/g, '');
        htmlContent = htmlContent.replace(/class="[^"]*edit-mode[^"]*"/g, 'class=""');
        htmlContent = htmlContent.replace(/class="[^"]*editable-element[^"]*"/g, 'class=""');
        htmlContent = htmlContent.replace(/contenteditable="true"/g, '');
        htmlContent = htmlContent.replace(/<div class="add-controls"[\s\S]*?<\/div>/g, '');
        htmlContent = htmlContent.replace(/class="[^"]*new-content[^"]*"/g, 'class=""');
        htmlContent = htmlContent.replace(/data-new-element="[^"]*"/g, '');
        
        // Create and download file
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cvsair-updated-${new Date().toISOString().split('T')[0]}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        alert('Dosya başarıyla indirildi!');
        this.disableEditMode();
    }
}

// Initialize edit controls when DOM is loaded
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        new EditControlsManager();
    });
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EditControlsManager;
}