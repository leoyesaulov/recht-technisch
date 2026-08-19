const modal = document.getElementById('password-modal');
const passwordValue = document.getElementById('password-value');
const button = document.getElementById('check-password-btn');
const closeModalButton = document.getElementById('close-modal-btn');

button.addEventListener('click', async () => {
  try {
    button.disabled = true;
    button.textContent = 'Loading...';

    const response = await fetch('/api/test_connection');

    if (!response.ok) {
      throw new Error('Unable to fetch the password.');
    }

    const data = await response.json();
    passwordValue.textContent = data.password || 'No password returned.';
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  } catch (error) {
    passwordValue.textContent = error.message;
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  } finally {
    button.disabled = false;
    button.textContent = 'Check password';
  }
});

closeModalButton.addEventListener('click', () => {
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
});

modal.addEventListener('click', (event) => {
  if (event.target === modal) {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
  }
});
