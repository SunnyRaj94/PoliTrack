const setPageTitle = document.querySelector('title.set-page-title');
setPageTitle.textContent = 'Politrack | Login';

document.getElementById('login-form').addEventListener('submit', async function(event) {
    event.preventDefault(); // Prevent default form submission

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('error-message');

    errorMessage.textContent = ''; // Clear previous errors

    try {
        const response = await fetch('http://localhost:8000/users/login', { // Replace with your FastAPI backend URL
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            const errorData = await response.json();
            errorMessage.textContent = errorData.detail || 'Login failed. Please try again.';
            return;
        }

        const data = await response.json();
        // Store the access token (e.g., in localStorage or sessionStorage)
        localStorage.setItem('access_token', data.access_token);
        // Redirect to the dashboard or a protected page
        window.location.href = '/manage-users'; // Or your dashboard page
    } catch (error) {
        console.error('Error during login:', error);
        errorMessage.textContent = 'An unexpected error occurred. Please try again later.';
    }
});

// Basic check if already logged in (optional, for SPA behavior)
// (This isn't strict security, just UX)
if (localStorage.getItem('access_token')) {
    // window.location.href = '/manage-users.html'; // Redirect if token exists
}