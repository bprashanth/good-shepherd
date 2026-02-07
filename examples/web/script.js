document.addEventListener('DOMContentLoaded', () => {
    // Card Elements
    const experimentCard = document.querySelector('.card-experiment');
    const phoneCard = document.querySelector('.card-phone');
    const dataCard = document.querySelector('.card-data');
    const indicatorsCard = document.querySelector('.card-indicators');
    const alienCard = document.querySelector('.card-alien');

    // Modal Elements - Experiment
    const expModalOverlay = document.getElementById('experiment-modal');
    const expCloseBtn = document.getElementById('close-modal');
    const expSubmitBtn = document.getElementById('submit-experiment');
    const expSpinner = document.getElementById('loading-spinner');
    const expFormContent = document.getElementById('modal-form-content');

    // Modal Elements - Indicators
    const indModalOverlay = document.getElementById('indicators-modal');
    const indCloseBtn = document.getElementById('close-modal-indicators');
    const indSubmitBtn = document.getElementById('submit-indicators');
    const indSpinner = document.getElementById('loading-spinner-indicators');
    const indFormContent = document.getElementById('modal-form-content-indicators');

    // --- Navigation Logic ---

    // Experiment Card -> Open Modal
    experimentCard.addEventListener('click', () => {
        expModalOverlay.classList.add('active');
    });

    // Indicators Card -> Open Modal (only if element interaction happened from previous Step 127/128)
    // The user manually added .card-indicators to DOM but we are editing script.js now.
    // We must ensure the element exists.
    if (indicatorsCard) {
        indicatorsCard.addEventListener('click', () => {
            indModalOverlay.classList.add('active');
        });
    }

    // Phone Card -> Localhost:8001
    phoneCard.addEventListener('click', () => {
        window.location.href = 'http://localhost:8001';
    });

    // Data Card -> Localhost:5173
    dataCard.addEventListener('click', () => {
        window.location.href = 'http://localhost:5173';
    });

    // Alien Card -> Localhost:8080
    alienCard.addEventListener('click', () => {
        window.location.href = 'http://localhost:8080/alienwise_viewer.html';
    });

    // --- Modal Logic ---

    // Generic Close Function
    function closeModal(overlay, formContent, spinner) {
        overlay.classList.remove('active');
        // Reset state
        if (formContent && spinner) {
            formContent.style.display = 'block';
            spinner.style.display = 'none';
        }
        document.querySelectorAll('form').forEach(f => f.reset());
        document.querySelectorAll('.custom-file-input span').forEach(s => {
            // Reset to original text if possible (simple reset style color for now)
            s.style.color = '#ccc';
            // Simple naive reset based on ID presence in same container
            if (s.parentElement.querySelector('#protocol-file')) s.textContent = 'Upload Protocol PDF';
            if (s.parentElement.querySelector('#map-file')) s.textContent = 'Upload KML / GeoJSON';
            if (s.parentElement.querySelector('#indicator-protocol-file')) s.textContent = 'Upload Indicator Protocol PDF';
            if (s.parentElement.querySelector('#forms-directory')) s.textContent = 'Upload Forms Directory';
            if (s.parentElement.querySelector('#excel-dataset')) s.textContent = 'Upload Excel Dataset';
        });
    }

    // Experiment Modal Listeners
    expCloseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closeModal(expModalOverlay, expFormContent, expSpinner);
    });

    expModalOverlay.addEventListener('click', (e) => {
        if (e.target === expModalOverlay) {
            closeModal(expModalOverlay, expFormContent, expSpinner);
        }
    });

    // Indicators Modal Listeners
    if (indCloseBtn) {
        indCloseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeModal(indModalOverlay, indFormContent, indSpinner);
        });
    }

    if (indModalOverlay) {
        indModalOverlay.addEventListener('click', (e) => {
            if (e.target === indModalOverlay) {
                closeModal(indModalOverlay, indFormContent, indSpinner);
            }
        });
    }

    // File input visual feedback
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            let fileName = '';
            if (e.target.files && e.target.files.length > 0) {
                fileName = e.target.files[0].name;
                // For directory, maybe show count or just first file
                if (e.target.webkitdirectory) {
                    fileName = `Directory Selected (${e.target.files.length} files)`;
                }
            }

            const label = e.target.parentElement.querySelector('span');
            if (fileName && label) {
                label.textContent = fileName;
                label.style.color = '#fff';
            }
        });
    });

    // Submit Action - Experiment
    expSubmitBtn.addEventListener('click', () => {
        // Validation could go here
        expFormContent.style.display = 'none';
        expSpinner.style.display = 'block';

        setTimeout(() => {
            window.location.href = '../setup_wizard/wizard.html';
        }, 1500);
    });

    // Submit Action - Indicators
    if (indSubmitBtn) {
        indSubmitBtn.addEventListener('click', () => {
            indFormContent.style.display = 'none';
            indSpinner.style.display = 'block';

            setTimeout(() => {
                window.location.href = 'file:///home/desinotorious/src/github.com/bprashanth/good-shepherd/examples/indicators/output/indicator_wizard.html';
            }, 1500);
        });
    }
});
