document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.card[data-target]').forEach((card) => {
        card.addEventListener('click', () => {
            window.location.href = card.dataset.target;
        });
    });
});
