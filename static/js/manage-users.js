const API_BASE_URL = 'http://localhost:8000'; // Your FastAPI backend URL
const usersTableBody = document.querySelector('#users-table tbody');
const addUserBtn = document.getElementById('add-user-btn');
const userModal = document.getElementById('user-modal');
const closeModalBtn = document.querySelector('.modal .close-button');
const cancelModalBtn = document.querySelector('.modal-footer .cancel-btn');
const userForm = document.getElementById('user-form');
const modalTitle = document.getElementById('modal-title');
const userIdInput = document.getElementById('user-id');
const modalErrorMessage = document.getElementById('modal-error-message');

const modalFirstName = document.getElementById('modal-first-name');
const modalLastName = document.getElementById('modal-last-name');
const modalEmail = document.getElementById('modal-email');
const modalPassword = document.getElementById('modal-password');
const modalPhoneNumber = document.getElementById('modal-phone-number');
const modalProfilePictureUrl = document.getElementById('modal-profile-picture-url');
const modalRole = document.getElementById('modal-role');
const modalIsActive = document.getElementById('modal-is-active');


// --- Helper Functions ---

// Function to get access token from localStorage
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        // If no token, redirect to login page (basic protection)
        window.location.href = '/login.html'; 
        throw new Error('No access token found. Redirecting to login.');
    }
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

// Populate role dropdown
async function populateRolesDropdown() {
    const roles = ['super_admin', 'admin', 'user', 'general_read_only']; // Hardcoded for example
    // In a real app, you might fetch available roles from a /roles endpoint
    modalRole.innerHTML = ''; // Clear existing options
    roles.forEach(role => {
        const option = document.createElement('option');
        option.value = role;
        option.textContent = role.replace('_', ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
        modalRole.appendChild(option);
    });
}


// --- CRUD Operations ---

async function fetchUsers() {
    try {
        const response = await fetch(`${API_BASE_URL}/users/`, {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                alert('Unauthorized or Forbidden. Please log in again with sufficient permissions.');
                localStorage.removeItem('access_token');
                window.location.href = '/login.html';
                return [];
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const users = await response.json();
        renderUsers(users);
        return users;
    } catch (error) {
        console.error('Error fetching users:', error);
        usersTableBody.innerHTML = '<tr><td colspan="6" class="error-message">Failed to load users. Please try again.</td></tr>';
        return [];
    }
}

async function createUser(userData) {
    try {
        const response = await fetch(`${API_BASE_URL}/users/register`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            modalErrorMessage.textContent = errorData.detail || 'Failed to create user.';
            throw new Error(errorData.detail || 'Failed to create user.');
        }

        modalErrorMessage.textContent = ''; // Clear error
        userModal.style.display = 'none'; // Close modal
        await fetchUsers(); // Refresh user list
    } catch (error) {
        console.error('Error creating user:', error);
    }
}

async function updateUser(userId, userData) {
    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            modalErrorMessage.textContent = errorData.detail || 'Failed to update user.';
            throw new Error(errorData.detail || 'Failed to update user.');
        }

        modalErrorMessage.textContent = ''; // Clear error
        userModal.style.display = 'none'; // Close modal
        await fetchUsers(); // Refresh user list
    } catch (error) {
        console.error('Error updating user:', error);
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user?')) {
        return;
    }
    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorData = await response.json();
            alert(errorData.detail || 'Failed to delete user.');
            throw new Error(errorData.detail || 'Failed to delete user.');
        }

        await fetchUsers(); // Refresh user list
    } catch (error) {
        console.error('Error deleting user:', error);
    }
}

// --- UI Rendering ---

function renderUsers(users) {
    usersTableBody.innerHTML = ''; // Clear existing rows
    if (users.length === 0) {
        usersTableBody.innerHTML = '<tr><td colspan="6">No users found.</td></tr>';
        return;
    }

    users.forEach(user => {
        const row = usersTableBody.insertRow();
        row.insertCell().textContent = user.id.substring(0, 8) + '...'; // Truncate ID for display
        row.insertCell().textContent = user.email;
        row.insertCell().textContent = `${user.first_name || ''} ${user.last_name || ''}`.trim();
        row.insertCell().textContent = user.role.replace('_', ' ').toUpperCase();
        row.insertCell().textContent = user.is_active ? 'Active' : 'Inactive';

        const actionsCell = row.insertCell();
        actionsCell.className = 'action-buttons';

        const editBtn = document.createElement('button');
        editBtn.textContent = 'Edit';
        editBtn.className = 'edit-btn';
        editBtn.addEventListener('click', () => openEditUserModal(user));

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'delete-btn';
        deleteBtn.addEventListener('click', () => deleteUser(user.id));

        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(deleteBtn);
    });
}

// --- Modal Handling ---

function openAddUserModal() {
    userForm.reset(); // Clear form
    userIdInput.value = ''; // Clear user ID
    modalTitle.textContent = 'Add New User';
    modalPassword.setAttribute('required', 'true'); // Password is required for creation
    modalEmail.readOnly = false; // Email can be changed for new user
    modalIsActive.checked = true; // Default new user to active
    modalErrorMessage.textContent = ''; // Clear any previous error messages
    userModal.style.display = 'flex'; // Show modal
    populateRolesDropdown(); // Populate roles
}

function openEditUserModal(user) {
    userForm.reset(); // Clear form
    modalTitle.textContent = 'Edit User';
    userIdInput.value = user.id;

    modalFirstName.value = user.first_name || '';
    modalLastName.value = user.last_name || '';
    modalEmail.value = user.email;
    modalEmail.readOnly = true; // Email usually not editable via this route
    modalPhoneNumber.value = user.phone_number || '';
    modalProfilePictureUrl.value = user.profile_picture_url || '';
    modalRole.value = user.role;
    modalIsActive.checked = user.is_active;

    modalPassword.removeAttribute('required'); // Password is optional for edit
    modalPassword.value = ''; // Don't pre-fill password

    modalErrorMessage.textContent = ''; // Clear any previous error messages
    userModal.style.display = 'flex'; // Show modal
    populateRolesDropdown(); // Populate roles and select current
    modalRole.value = user.role; // Select the actual role for the user
}

function closeUserModal() {
    userModal.style.display = 'none';
    modalErrorMessage.textContent = ''; // Clear any error messages
    modalEmail.readOnly = false; // Reset email readOnly state
    modalPassword.setAttribute('required', 'true'); // Reset password required state
}


// --- Event Listeners ---

document.addEventListener('DOMContentLoaded', () => {
    // Check if authenticated before fetching users
    if (localStorage.getItem('access_token')) {
        fetchUsers();
    } else {
        // Redirect to login if not authenticated
        window.location.href = '/login.html';
    }
});

addUserBtn.addEventListener('click', openAddUserModal);
closeModalBtn.addEventListener('click', closeUserModal);
cancelModalBtn.addEventListener('click', closeUserModal);

userForm.addEventListener('submit', async function(event) {
    event.preventDefault();

    const userId = userIdInput.value;
    const userData = {
        first_name: modalFirstName.value,
        last_name: modalLastName.value || null,
        email: modalEmail.value,
        phone_number: modalPhoneNumber.value || null,
        profile_picture_url: modalProfilePictureUrl.value || null,
        role: modalRole.value,
        is_active: modalIsActive.checked,
        // Add more fields if implemented in schema
    };

    // Only include password if it's set for creation or explicitly changed for update
    if (modalPassword.value) {
        userData.password = modalPassword.value;
    }

    if (userId) {
        // Update existing user
        await updateUser(userId, userData);
    } else {
        // Create new user
        // Ensure password exists for creation
        if (!userData.password) {
            modalErrorMessage.textContent = 'Password is required for new users.';
            return;
        }
        await createUser(userData);
    }
});

// Close modal when clicking outside of it
window.addEventListener('click', (event) => {
    if (event.target == userModal) {
        closeUserModal();
    }
});