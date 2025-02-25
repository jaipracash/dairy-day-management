function addToCart(productId, quantity) {
    console.log('Adding to cart:', productId, quantity);
    if (!productId || isNaN(productId)) {
        console.error('Invalid product ID:', productId);
        alert('Error: Invalid product ID. Please try again.');
        return;
    }
    fetch('/cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `product_id=${encodeURIComponent(productId)}&quantity=${encodeURIComponent(quantity)}`
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Cart update response:', data);
        if (data.success) {
            document.getElementById('cart-count').innerText = data.cart_count;
            updateCart();
        } else {
            console.error('Cart update failed:', data.message);
            alert('Failed to add item to cart. ' + (data.message || 'Please try again.'));
        }
    })
    .catch(error => {
        console.error('Fetch error:', error);
        alert('An error occurred while adding to cart. Please try again.');
    });
}

function updateCart() {
    console.log('Updating cart...');
    fetch('/cart')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Cart data received:', data);
            const cartItemsDiv = document.getElementById('cart-items');
            const cartTotalSpan = document.getElementById('cart-total');
            const cartCountSpan = document.getElementById('cart-count');

            if (!cartItemsDiv || !cartTotalSpan || !cartCountSpan) {
                console.error('Cart elements not found in DOM');
                alert('Error: Cart elements not found. Please refresh the page.');
                return;
            }

            cartItemsDiv.innerHTML = '';
            let total = 0;

            if (data.cart_items.length === 0) {
                cartItemsDiv.innerHTML = '<p>Your cart is empty.</p>';
            } else {
                data.cart_items.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'cart-item';
                    itemDiv.innerHTML = `
                        <span>${item.name} (x${item.quantity})</span>
                        <span>₹${item.total}</span>
                        <button class="card-btn delete-btn" onclick="deleteFromCart(${item.product_id})">Delete</button>
                    `;
                    cartItemsDiv.appendChild(itemDiv);
                    total += item.total;
                });
            }
            cartTotalSpan.innerText = total;
            cartCountSpan.innerText = data.cart_count || 0;
        })
        .catch(error => {
            console.error('Fetch error for cart update:', error);
            alert('An error occurred while updating the cart. Please try again.');
        });
}

function deleteFromCart(productId) {
    console.log('Deleting from cart:', productId);
    fetch(`/cart/delete/${productId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Delete response:', data);
        if (data.success) {
            document.getElementById('cart-count').innerText = data.cart_count;
            updateCart();
        } else {
            console.error('Delete failed:', data.message);
            alert('Failed to delete item. ' + (data.message || 'Please try again.'));
        }
    })
    .catch(error => {
        console.error('Fetch error for delete:', error);
        alert('An error occurred while deleting the item. Please try again.');
    });
}

function updateProfile() {
    console.log('Updating profile...');
    fetch('/user_orders_json', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Profile data received:', data);
        const profileOrdersDiv = document.getElementById('profile-orders');
        if (!profileOrdersDiv) {
            console.error('Profile orders element not found in DOM');
            alert('Error: Profile orders element not found. Please refresh the page.');
            return;
        }

        profileOrdersDiv.innerHTML = '';
        if (data.orders && data.orders.length > 0) {
            data.orders.forEach(order => {
                const orderDiv = document.createElement('div');
                orderDiv.className = 'order-item';
                orderDiv.innerHTML = `
                    <p>Order #${order.id} - ₹${order.total_amount} (${order.status}) on ${order.order_date}</p>
                `;
                profileOrdersDiv.appendChild(orderDiv);
            });
        } else {
            profileOrdersDiv.innerHTML = '<p>No orders found.</p>';
        }
    })
    .catch(error => {
        console.error('Fetch error for profile update:', error);
        alert('An error occurred while updating the profile. Please try again.');
    });
}

// Cart and Profile Sidebar Toggles
document.getElementById('cart-toggle').addEventListener('click', (e) => {
    e.preventDefault();
    const sidebar = document.getElementById('cart-sidebar');
    sidebar.classList.add('open');
    updateCart();
});

document.getElementById('cart-close').addEventListener('click', () => {
    const sidebar = document.getElementById('cart-sidebar');
    sidebar.classList.remove('open');
});

document.getElementById('profile-toggle').addEventListener('click', (e) => {
    e.preventDefault();
    const sidebar = document.getElementById('profile-sidebar');
    sidebar.classList.add('open');
    if (document.getElementById('profile-sidebar-toggle')) {
        updateProfile(); // Only fetch orders if the profile sidebar is triggered
    }
});

document.getElementById('profile-close').addEventListener('click', () => {
    const sidebar = document.getElementById('profile-sidebar');
    sidebar.classList.remove('open');
});

// Update cart and profile on page load if applicable
document.addEventListener('DOMContentLoaded', () => {
    const cartCount = document.getElementById('cart-count');
    if (cartCount && parseInt(cartCount.innerText) > 0) {
        updateCart();
    }
    // No need to auto-update profile unless triggered by user
});
// Existing cart and profile toggle functions remain unchanged...

document.getElementById('profile-logout')?.addEventListener('click', function(e) {
    e.preventDefault();
    fetch('/logout', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',  // Ensure session cookies are sent
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        const profileContent = document.getElementById('profile-content');
        if (data.message) {
            profileContent.innerHTML = `<div class="message success">${data.message}</div>`;
            setTimeout(() => {
                window.location.href = '/';  // Force full reload to clear client state
            }, 2000);
        } else {
            window.location.href = '/';
        }
    })
    .catch(error => {
        console.error('Error during logout:', error);
        alert('Failed to log out. Please try again.');
        window.location.href = '/';
    });
});

function updateProfile() {
    console.log('Updating profile...');
    fetch('/user_orders_json', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401 || response.status === 302) {
                throw new Error('User not authenticated');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Profile data received:', data);
        const profileOrdersDiv = document.getElementById('profile-orders');
        if (!profileOrdersDiv) {
            console.error('Profile orders element not found in DOM');
            return;
        }
        profileOrdersDiv.innerHTML = '';
        if (data.error) {
            profileOrdersDiv.innerHTML = `<p>Error: ${data.error}</p>`;
        } else if (data.orders && data.orders.length > 0) {
            data.orders.forEach(order => {
                const orderDiv = document.createElement('div');
                orderDiv.className = 'order-item';
                orderDiv.innerHTML = `
                    <p>Order #${order.id} - ₹${order.total_amount} (${order.status}) on ${order.order_date}</p>
                `;
                profileOrdersDiv.appendChild(orderDiv);
            });
        } else {
            profileOrdersDiv.innerHTML = '<p>No orders found.</p>';
        }
    })
    .catch(error => {
        console.error('Fetch error for profile update:', error);
        const profileOrdersDiv = document.getElementById('profile-orders');
        if (profileOrdersDiv) {
            if (error.message === 'User not authenticated') {
                profileOrdersDiv.innerHTML = '<p>Please log in to view your orders.</p>';
            } else {
                profileOrdersDiv.innerHTML = '<p>Failed to load orders. Please try again.</p>';
            }
        }
    });
}

// Update profile toggle to check authentication state
document.getElementById('profile-toggle').addEventListener('click', (e) => {
    e.preventDefault();
    const sidebar = document.getElementById('profile-sidebar');
    sidebar.classList.add('open');
    updateProfile();
});
// Ensure other existing JavaScript (e.g., cart, profile toggle) remains functional
// Get CSRF token from meta tag (if using Flask-WTF)
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Existing cart and profile toggle functions remain unchanged...

// Admin panel order acceptance (updated from admin_panel.html)
document.querySelectorAll('.accept-btn').forEach(button => {
    button.addEventListener('click', function() {
        const orderId = this.getAttribute('data-order-id');
        fetch(`/admin/order/${orderId}/accept`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()  // Include CSRF token for security
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                flashMessage(data.message, 'success');
                this.textContent = 'Accepted';
                this.disabled = true;
                this.classList.remove('card-btn');
            } else {
                flashMessage(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error accepting order:', error);
            flashMessage('Failed to accept order. Please try again.', 'error');
        });
    });
});

function flashMessage(message, category) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${category}`;
    messageDiv.textContent = message;
    document.querySelector('.admin-container').appendChild(messageDiv);
    setTimeout(() => messageDiv.remove(), 3000); // Remove message after 3 seconds
}

// Ensure other existing JavaScript (e.g., cart, profile toggle) remains functional