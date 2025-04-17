// Cache DOM elements to avoid repeated queries
const elements = {
    nameInput: document.getElementById('name'),
    dobInput: document.getElementById('dob'),
    maleInput: document.getElementById('male'),
    femaleInput: document.getElementById('female'),
    messageInput: document.getElementById('message'),
    submitButton: document.querySelector('button[type="submit"]'),
    komentar: document.querySelector('.komentar'),
    labels: {
        name: document.querySelector('label[for="name"]'),
        dob: document.querySelector('label[for="dob"]'),
        male: document.querySelector('label[for="male"]'),
        female: document.querySelector('label[for="female"]')
    }
};

// Function to get the current timestamp
const getCurrentTimestamp = () => {
    const now = new Date();
    const days = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'];
    const months = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ];

    return `${now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}, ${days[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
};

// Handle form submission
elements.submitButton.addEventListener('click', (e) => {
    e.preventDefault();

    const name = elements.nameInput.value.trim();
    const dob = elements.dobInput.value.trim();
    const gender = elements.maleInput.checked ? 'Laki-laki' : elements.femaleInput.checked ? 'Perempuan' : '';
    const message = elements.messageInput.value.trim();

    if (!name || !dob || !gender || !message) {
        alert('Harap isi semua bidang formulir!');
        return;
    }

    const timestamp = getCurrentTimestamp();

    // Create and append the comment
    const komentarDiv = document.createElement('div');
    komentarDiv.innerHTML = `
        <p>Waktu: ${timestamp}</p>
        <p>Nama: ${name}</p>
        <p>Tanggal Lahir: ${dob}</p>
        <p>Jenis Kelamin: ${gender}</p>
        <p>Pesan: ${message}</p>
    `;
    elements.komentar.appendChild(komentarDiv);

    // Update labels
    elements.labels.name.textContent = `Nama: ${name}`;
    elements.labels.dob.textContent = `Tanggal Lahir: ${dob}`;
    elements.labels.male.textContent = `Laki-laki: ${elements.maleInput.checked ? '✓' : ''}`;
    elements.labels.female.textContent = `Perempuan: ${elements.femaleInput.checked ? '✓' : ''}`;

    // Clear inputs
    elements.nameInput.value = '';
    elements.dobInput.value = '';
    elements.maleInput.checked = false;
    elements.femaleInput.checked = false;
    elements.messageInput.value = '';
});

// Slideshow functionality
let currentSlide = 0;
let slides;

const changeSlide = (direction) => {
    if (!slides) slides = document.querySelectorAll('.slides img');
    slides[currentSlide].classList.remove('active');
    currentSlide = (currentSlide + direction + slides.length) % slides.length;
    slides[currentSlide].classList.add('active');
};

// Initialize the first slide as active
document.addEventListener('DOMContentLoaded', () => {
    slides = document.querySelectorAll('.slides img');
    if (slides.length > 0) slides[0].classList.add('active');
});
