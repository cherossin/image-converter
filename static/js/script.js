document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const fileList = document.getElementById('file-list');
    const submitBtn = document.getElementById('submit-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    const convertDirectionRadios = document.getElementsByName('convert_direction');
    const resizeSection = document.getElementById('resize-section');
    const convertSection = document.getElementById('convert-section');
    const convertSelect = document.querySelector('select[name="convert_to"]');

    // --- Section Toggling Logic ---
    function toggleSections() {
        const selected = document.querySelector('input[name="convert_direction"]:checked').value;
        
        // Reset display
        resizeSection.style.display = 'none';
        convertSection.style.display = 'none';

        // Reset option visibility and text
        if (convertSelect && convertSelect.options.length > 0) {
            convertSelect.options[0].style.display = ""; // Show option
            convertSelect.options[0].text = "원본 포맷 유지";
        }

        if (selected === 'image_conversion') {
            resizeSection.style.display = 'block';
            convertSection.style.display = 'block';
        } else if (selected === 'pdf_to_image') {
            // PDF to Image allows format selection
            convertSection.style.display = 'block';
            
            // Hide "Original Format" option to avoid redundancy with "PNG"
            // and force selection of a specific format (defaulting to PNG)
            if (convertSelect && convertSelect.options.length > 0) {
                convertSelect.options[0].style.display = "none";
                
                // If "Original" (empty value) was selected, switch to "png"
                if (convertSelect.value === "") {
                    convertSelect.value = "png";
                }
            }
        }
        // image_to_pdf: no extra options needed
    }

    convertDirectionRadios.forEach(radio => {
        radio.addEventListener('change', toggleSections);
    });
    toggleSections(); // Initial state

    // --- File Handling Logic ---
    let selectedFiles = [];

    function updateFileList() {
        fileList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const li = document.createElement('li');
            li.className = 'file-item';
            li.innerHTML = `
                <span class="file-name">${file.name}</span>
                <span class="file-size">(${(file.size / 1024).toFixed(1)} KB)</span>
                <button type="button" class="remove-btn" data-index="${index}">×</button>
            `;
            fileList.appendChild(li);
        });

        // Update submit button state
        submitBtn.disabled = selectedFiles.length === 0;

        // Update the actual input element (required for form submission)
        const dataTransfer = new DataTransfer();
        selectedFiles.forEach(file => dataTransfer.items.add(file));
        fileInput.files = dataTransfer.files;
    }

    function handleFiles(files) {
        const newFiles = Array.from(files);
        // Filter duplicates if needed, or just append
        selectedFiles = [...selectedFiles, ...newFiles];
        updateFileList();
    }

    // Click to upload
    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    // Remove file
    fileList.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-btn')) {
            const index = parseInt(e.target.dataset.index);
            selectedFiles.splice(index, 1);
            updateFileList();
        }
    });

    // --- Form Submission ---
    form.addEventListener('submit', function() {
        loadingOverlay.style.display = 'flex';
        // Hide loading after a timeout (fallback) or when page reloads (if it does)
        // Since we return a file download, the page won't reload automatically.
        // We need a way to hide the loading spinner.
        // Simple hack: Hide it after 3 seconds (assuming download starts) 
        // or keep it until user interacts. 
        // Better UX for download: Use a cookie or just let it stay for a bit.
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
            // Optional: Show a "Download started" toast
        }, 5000); 
    });
});