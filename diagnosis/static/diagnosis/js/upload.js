const fileInput = document.querySelector('[data-file-input="files"]');
const folderInput = document.querySelector('[data-file-input="folder"]');
const zone = document.querySelector('[data-drop-zone]');
const list = document.querySelector('[data-selected-files]');
const form = document.querySelector('[data-upload-form]');
const processing = document.querySelector('[data-processing]');
const submit = document.querySelector('[data-submit-button]');

function allSelectedFiles() {
  return [
    ...Array.from(fileInput?.files || []),
    ...Array.from(folderInput?.files || []),
  ];
}

function displayName(file) {
  return file.webkitRelativePath || file.name;
}

function renderFiles() {
  if (!list) return;
  const files = allSelectedFiles();
  if (!files.length) {
    list.innerHTML = '<p>No files or folder selected.</p>';
    return;
  }

  const total = files.reduce((sum, file) => sum + file.size, 0);
  const fileCount = Array.from(fileInput?.files || []).length;
  const folderCount = Array.from(folderInput?.files || []).length;
  const sourceText = [
    fileCount ? `${fileCount} individual file(s)` : '',
    folderCount ? `${folderCount} folder file(s)` : '',
  ].filter(Boolean).join(' + ');

  const rows = files.slice(0, 20).map(file => (
    `<div class="selected-row"><span title="${displayName(file)}">${displayName(file)}</span>` +
    `<small>${(file.size / 1024 / 1024).toFixed(2)} MB</small></div>`
  )).join('');

  list.innerHTML =
    `<div class="selected-head"><strong>${files.length} total file(s)</strong>` +
    `<span>${(total / 1024 / 1024).toFixed(2)} MB</span></div>` +
    `<small class="selected-source">${sourceText}</small>` + rows +
    (files.length > 20 ? `<small>and ${files.length - 20} more file(s)</small>` : '');
}

[fileInput, folderInput].forEach(input => {
  if (input) input.addEventListener('change', renderFiles);
});

if (zone && fileInput) {
  zone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(name => zone.addEventListener(name, event => {
    event.preventDefault();
    zone.classList.add('dragging');
  }));

  ['dragleave', 'drop'].forEach(name => zone.addEventListener(name, event => {
    event.preventDefault();
    zone.classList.remove('dragging');
  }));

  zone.addEventListener('drop', event => {
    if (!event.dataTransfer.files.length) return;
    try {
      const transfer = new DataTransfer();
      Array.from(event.dataTransfer.files).forEach(file => transfer.items.add(file));
      fileInput.files = transfer.files;
    } catch (_error) {
      // Older browsers may not permit assigning FileList. The file/folder
      // buttons above remain available in that case.
    }
    renderFiles();
  });
}

if (form) {
  form.addEventListener('submit', event => {
    if (!allSelectedFiles().length) {
      event.preventDefault();
      if (list) list.innerHTML = '<div class="form-error">Choose files or choose a folder before continuing.</div>';
      return;
    }
    if (processing) processing.hidden = false;
    if (submit) {
      submit.disabled = true;
      submit.textContent = 'Processing…';
    }
  });
}
