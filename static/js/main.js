// Add this to your existing main.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Image preview for memory forms
    document.querySelectorAll('input[type="file"][accept="image/*"]').forEach(function(input) {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const previewId = e.target.id + 'Preview';
                const previewContainer = document.getElementById(previewId) || 
                    document.createElement('div');
                if (!document.getElementById(previewId)) {
                    previewContainer.id = previewId;
                    previewContainer.className = 'mt-2 text-center';
                    e.target.parentNode.appendChild(previewContainer);
                }
                
                const reader = new FileReader();
                reader.onload = function(event) {
                    previewContainer.innerHTML = '';
                    const img = document.createElement('img');
                    img.src = event.target.result;
                    img.className = 'img-thumbnail';
                    img.style.maxHeight = '200px';
                    previewContainer.appendChild(img);
                };
                reader.readAsDataURL(file);
            }
        });
    });
});