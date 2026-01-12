document.addEventListener('DOMContentLoaded', () => {
    // Card Elements
    const experimentCard = document.querySelector('.card-experiment');
    const phoneCard = document.querySelector('.card-phone');
    const dataCard = document.querySelector('.card-data');

    // Modal Elements
    const modalOverlay = document.getElementById('experiment-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const submitBtn = document.getElementById('submit-experiment');
    const spinner = document.getElementById('loading-spinner');
    const formContent = document.getElementById('modal-form-content');

    // --- Navigation Logic ---

    // Experiment Card -> Open Modal
    experimentCard.addEventListener('click', () => {
        modalOverlay.classList.add('active');
    });

    // Phone Card -> Localhost:8000
    phoneCard.addEventListener('click', () => {
        window.location.href = 'http://localhost:8000';
    });

    // Data Card -> Localhost:5173
    dataCard.addEventListener('click', () => {
        window.location.href = 'http://localhost:5173';
    });

    // --- Modal Logic ---

    // Close Modal
    closeModalBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent card click
        modalOverlay.classList.remove('active');
        resetModal();
    });

    // Close on clicking overlay
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            modalOverlay.classList.remove('active');
            resetModal();
        }
    });

    // File input visual feedback
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const fileName = e.target.files[0]?.name;
            const label = e.target.parentElement.querySelector('span');
            if (fileName && label) {
                label.textContent = fileName;
                label.style.color = '#fff';
            }
        });
    });

    // Submit Action
    submitBtn.addEventListener('click', () => {
        // Validation could go here

        // Show Spinner
        formContent.style.display = 'none';
        spinner.style.display = 'block';

        // Simulate processing delay then redirect
        setTimeout(() => {
            window.location.href = '../setup_wizard/wizard.html';
        }, 1500); // 1.5s delay
    });

    function resetModal() {
        formContent.style.display = 'block';
        spinner.style.display = 'none';
        // Reset file inputs visually if needed, specifically labels
        const spans = document.querySelectorAll('.custom-file-input span');
        spans[0].textContent = 'Upload Protocol PDF';
        spans[1].textContent = 'Upload KML / GeoJSON';
        spans.forEach(s => s.style.color = '#ccc');
        // Reset forms
        document.querySelector('form').reset();
    }
});
