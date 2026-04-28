document.addEventListener('DOMContentLoaded', () => {
    const indicatorsCard = document.querySelector('.card-indicators');
    const experimentCard = document.querySelector('.card-experiment');
    const alienCard = document.querySelector('.card-alien');
    const expModalOverlay = document.getElementById('experiment-modal');
    const expCloseBtn = document.getElementById('close-modal');
    const expSubmitBtn = document.getElementById('submit-experiment');
    const expSpinner = document.getElementById('loading-spinner');
    const expFormContent = document.getElementById('modal-form-content');
    const indModalOverlay = document.getElementById('indicators-modal');
    const indCloseBtn = document.getElementById('close-modal-indicators');
    const indSubmitBtn = document.getElementById('submit-indicators');
    const indSpinner = document.getElementById('loading-spinner-indicators');
    const indFormContent = document.getElementById('modal-form-content-indicators');

    if (indicatorsCard) {
        indicatorsCard.addEventListener('click', () => indModalOverlay.classList.add('active'));
    }
    if (experimentCard) {
        experimentCard.addEventListener('click', () => expModalOverlay.classList.add('active'));
    }

    function closeModal(overlay, formContent, spinner) {
        overlay.classList.remove('active');
        if (formContent && spinner) {
            formContent.style.display = 'block';
            spinner.style.display = 'none';
        }
        document.querySelectorAll('form').forEach(f => f.reset());
        document.querySelectorAll('.custom-file-input span').forEach(s => {
            s.style.color = '#ccc';
            if (s.parentElement.querySelector('#protocol-file')) s.textContent = 'Upload Protocol PDF';
            if (s.parentElement.querySelector('#map-file')) s.textContent = 'Upload KML / GeoJSON';
            if (s.parentElement.querySelector('#dataset-folder')) s.textContent = 'Upload Dataset';
            if (s.parentElement.querySelector('#indicator-protocol-file')) s.textContent = 'Upload Indicator Protocol PDF';
            if (s.parentElement.querySelector('#forms-directory')) s.textContent = 'Upload Forms Directory';
            if (s.parentElement.querySelector('#excel-dataset')) s.textContent = 'Upload Excel Dataset';
        });
    }

    expCloseBtn.addEventListener('click', (e) => { e.stopPropagation(); closeModal(expModalOverlay, expFormContent, expSpinner); });
    expModalOverlay.addEventListener('click', (e) => { if (e.target === expModalOverlay) closeModal(expModalOverlay, expFormContent, expSpinner); });
    if (indCloseBtn) indCloseBtn.addEventListener('click', (e) => { e.stopPropagation(); closeModal(indModalOverlay, indFormContent, indSpinner); });
    if (indModalOverlay) indModalOverlay.addEventListener('click', (e) => { if (e.target === indModalOverlay) closeModal(indModalOverlay, indFormContent, indSpinner); });

    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', (e) => {
            let fileName = '';
            if (e.target.files && e.target.files.length > 0) {
                fileName = e.target.files[0].name;
                if (e.target.webkitdirectory) fileName = `Directory Selected (${e.target.files.length} files)`;
            }
            const label = e.target.parentElement.querySelector('span');
            if (fileName && label) {
                label.textContent = fileName;
                label.style.color = '#fff';
            }
        });
    });

    expSubmitBtn.addEventListener('click', () => {
        expFormContent.style.display = 'none';
        expSpinner.style.display = 'block';
        setTimeout(() => {
            window.location.href = '../setup_wizard_2/wizard.html';
        }, 1500);
    });

    if (indSubmitBtn) {
        indSubmitBtn.addEventListener('click', () => {
            indFormContent.style.display = 'none';
            indSpinner.style.display = 'block';
            setTimeout(() => {
                window.location.href = '../indicators_2/output/indicator_wizard.html';
            }, 1500);
        });
    }
});
