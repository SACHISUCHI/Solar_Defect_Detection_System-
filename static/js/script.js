// Simple form validation
document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    // Password confirmation validation
    const registrationForm = document.querySelector('form[action="{{ url_for(\'register\') }}"]');
    if (registrationForm) {
        registrationForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password');
            const confirmPassword = document.getElementById('confirm_password');

            if (password.value !== confirmPassword.value) {
                e.preventDefault();
                alert('Passwords do not match');
            }
        });
    }
});