// Получаем элементы
const openModalBtn = document.getElementById('openFolderModalBtn');
const modal = document.getElementById('folderModal');
const closeModal = document.querySelector('.modal .close');
const browseBtn = document.getElementById('browseFolderBtn');
const folderInput = document.getElementById('folderPath');
const saveBtn = document.getElementById('saveFolderBtn');
const selectedFolderLabel = document.getElementById('selectedFolderLabel');

// Переменная для хранения выбранного пути
let selectedFolderPath = "";

// Открытие модального окна
openModalBtn.addEventListener('click', () => {
    modal.style.display = 'block';
});

// Закрытие модального окна по крестику
closeModal.addEventListener('click', () => {
    modal.style.display = 'none';
});

// Закрытие при клике вне окна
window.addEventListener('click', (event) => {
    if (event.target == modal) {
        modal.style.display = 'none';
    }
});

// Кнопка "Обзор"
browseBtn.addEventListener('click', async () => {
    // В Electron можно использовать диалог выбора папки
    const { ipcRenderer } = require('electron');
    const folderPath = await ipcRenderer.invoke('open-folder-dialog');
    if (folderPath) {
        folderInput.value = folderPath;
    }
});

// Кнопка "Сохранить выбор"
saveBtn.addEventListener('click', () => {
    if (folderInput.value.trim() !== "") {
        selectedFolderPath = folderInput.value;
        selectedFolderLabel.textContent = `Выбранная папка: ${selectedFolderPath}`;
        modal.style.display = 'none';
    } else {
        alert("Пожалуйста, выберите папку.");
    }
});
