// js/dashboard.js

// DOM Elements
const selectionCards = document.getElementById('selection-cards');
const cameraContainer = document.getElementById('camera-container');
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const previewContainer = document.getElementById('preview-container');
const previewImage = document.getElementById('preview-image');
const resultBox = document.getElementById('result-box');
const loading = document.getElementById('loading');
const diseaseNameEl = document.getElementById('disease-name');

const uploadSection = document.getElementById('upload-section');
const suggestionsSection = document.getElementById('suggestions-section');
const menuItems = document.querySelectorAll('.menu-item');
const cropRecommendation = document.getElementById('crop-recommendation');
const suggestedCropEl = document.getElementById('suggested-crop');
const cropReasoningEl = document.getElementById('crop-reasoning');

let currentStream = null;
let map = null;
let marker = null;

// Mock data to simulate AI detection results
const mockResults = [
    { name: "Healthy Plant", confidence: "99.2%", actions: ["No action needed.", "Maintain current watering schedule.", "Keep monitoring weekly."] },
    { name: "Tomato Early Blight", confidence: "94.5%", actions: ["Remove infected lower leaves.", "Apply copper fungicide.", "Avoid overhead watering."] },
    { name: "Potato Late Blight", confidence: "89.1%", actions: ["Destroy infected plants.", "Apply protective fungicide.", "Ensure good drainage."] },
    { name: "Apple Scab", confidence: "96.4%", actions: ["Rake and destroy fallen leaves.", "Apply fungicide during spring.", "Prune tree for better air circulation."] }
];

// Handle Image Upload
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            setupPreview(e.target.result, file);
        }
        reader.readAsDataURL(file);
    }
}

// Start Camera Mode
async function startCamera() {
    selectionCards.style.display = 'none';
    cameraContainer.style.display = 'flex';
    
    try {
        currentStream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'environment' } // Prefer rear camera on mobile
        });
        video.srcObject = currentStream;
    } catch (err) {
        console.error("Error accessing camera: ", err);
        alert("Unable to access the camera. Please make sure you have granted permission.");
        resetView();
    }
}

// Stop Camera
function stopCamera() {
    if (currentStream) {
        const tracks = currentStream.getTracks();
        tracks.forEach(track => track.stop());
    }
    cameraContainer.style.display = 'none';
    selectionCards.style.display = 'grid';
}

// Capture Photo from Canvas
function capturePhoto() {
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to image
    const dataUrl = canvas.toDataURL('image/jpeg');
    stopCamera();
    
    // Create a Blob from the canvas to send to the server
    canvas.toBlob((blob) => {
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        setupPreview(dataUrl, file);
    }, 'image/jpeg');
}

// Setup Preview and Start Analysis
function setupPreview(imageUrl, imageFile) {
    selectionCards.style.display = 'none';
    cameraContainer.style.display = 'none';
    previewContainer.style.display = 'block';
    
    previewImage.src = imageUrl;
    previewImage.style.display = 'inline-block';
    
    // Hide results initially
    resultBox.style.display = 'none';
    
    // Start Analysis
    analyzeImage(imageFile);
}

// Analyze image using the FastAPI backend
async function analyzeImage(imageFile) {
    loading.style.display = 'block';
    
    const formData = new FormData();
    formData.append('file', imageFile);
    
    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }
        
        const result = await response.json();
        showResults(result);
    } catch (error) {
        console.error("Error analyzing image:", error);
        loading.style.display = 'none';
        alert("Failed to analyze the image. Please ensure the backend server is running.");
        resetView();
    }
}

// Show Results
function showResults(result) {
    loading.style.display = 'none';
    
    // Update DOM
    diseaseNameEl.innerText = result.name;
    document.querySelector('.result-section p').innerText = `Confidence: ${result.confidence}`;
    
    const actionsList = document.querySelector('.result-section ul');
    actionsList.innerHTML = '';
    result.actions.forEach(action => {
        actionsList.innerHTML += `<li><i class="fa-solid fa-check text-primary" style="margin-right: 0.5rem;"></i> ${action}</li>`;
    });
    
    // Pick badge color based on health
    const badge = document.querySelector('.badge-success');
    if (result.name.toLowerCase().includes("healthy") || result.raw_class === "Healthy") {
        badge.innerText = "Healthy";
        badge.style.backgroundColor = "rgba(16, 185, 129, 0.2)";
        badge.style.color = "var(--primary)";
    } else {
        badge.innerText = "Disease Detected";
        badge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
        badge.style.color = "var(--error)";
    }

    resultBox.style.display = 'block';
}

// Reset View back to selection
function resetView() {
    previewContainer.style.display = 'none';
    previewImage.src = "";
    resultBox.style.display = 'none';
    selectionCards.style.display = 'grid';
    document.getElementById('file-upload').value = ""; // clear file input
}

// ---- New Location & Suggestion Features ----

// Switch to Detection View
function showDetection(event) {
    if(event) event.preventDefault();
    // Update Sidebar
    menuItems.forEach(item => item.classList.remove('active'));
    if(event) event.currentTarget.classList.add('active');
    
    // Switch View
    suggestionsSection.style.display = 'none';
    uploadSection.style.display = 'block';
}

// Switch to Suggestions View
function showSuggestions(event) {
    if(event) event.preventDefault();
    // Update Sidebar
    menuItems.forEach(item => item.classList.remove('active'));
    if(event) event.currentTarget.classList.add('active');
    
    // Switch View
    uploadSection.style.display = 'none';
    suggestionsSection.style.display = 'block';

    // Must invalidate map size when making container visible
    if(map) {
        setTimeout(() => map.invalidateSize(), 100);
    }
}

// Initialize Leaflet Map and Detect Location
function initMapAndLocation() {
    if (!map) {
        // Initialize map centered at a default location (e.g., India)
        map = L.map('map').setView([20.5937, 78.9629], 5); // Fallback coords
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Allow user to pick location manually on map click
        map.on('click', function(e) {
            updateLocationAndSuggest(e.latlng.lat, e.latlng.lng);
        });
    }

    // Try HTML5 Geolocation
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                updateLocationAndSuggest(lat, lng);
                map.setView([lat, lng], 10);
            },
            (error) => {
                console.error("Geolocation error:", error);
                alert("Please enable location services or click on the map to set your farm's location.");
            }
        );
    } else {
        alert("Geolocation is not supported by this browser.");
    }
}

const mockCropsByLocationCategory = [
    { name: "Wheat & Mustard", reason: "Suitable for temperate/cooler climates and moderate rainfall areas found near these coordinates." },
    { name: "Rice & Sugarcane", reason: "Ideal for regions with high humidity and abundant water supply." },
    { name: "Cotton & Millets", reason: "Best suited for warmer climates and black soils common in this region." },
    { name: "Soybean & Maize", reason: "Excellent choice for the moderate rainfall and soil composition detected." }
];

function updateLocationAndSuggest(lat, lng) {
    // Update Marker
    if (marker) {
        marker.setLatLng([lat, lng]);
    } else {
        marker = L.marker([lat, lng]).addTo(map);
    }
    marker.bindPopup("Farm Location").openPopup();

    // Show suggestion card
    cropRecommendation.style.display = 'block';
    suggestedCropEl.innerText = "Analyzing...";
    cropReasoningEl.innerText = "Fetching soil and climate data for selected coordinates...";

    // Simulate API delay for crop suggestion
    setTimeout(() => {
        // Pick a fake recommendation based on random logic for demo
        const randomCrop = mockCropsByLocationCategory[Math.floor(Math.random() * mockCropsByLocationCategory.length)];
        
        suggestedCropEl.innerText = randomCrop.name;
        cropReasoningEl.innerHTML = `<strong>Coordinates:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}<br><br>${randomCrop.reason}`;
    }, 1500);
}

// Check if URL has #suggestions hash (e.g. from signup page redirect)
window.addEventListener('load', () => {
    if(window.location.hash === '#suggestions') {
        const suggestionTab = document.querySelectorAll('.menu-item')[1];
        showSuggestions({ currentTarget: suggestionTab, preventDefault: () => {} });
        initMapAndLocation();
    }
});
