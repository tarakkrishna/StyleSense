import { fetchRecommendation, uploadImage } from "./api.js";
import {
  renderRecommendation,
  setRetryVisible,
  setUploadLoading,
  setView,
  showSkeleton,
  showToast,
} from "./ui.js";

const state = {
  file: null,
  skinTone: null,
  lastPayload: null,
};

const startBtn = document.getElementById("startBtn");
const backToLandingBtn = document.getElementById("backToLandingBtn");
const tryAgainBtn = document.getElementById("tryAgainBtn");
const recommendBtn = document.getElementById("recommendBtn");
const retryBtn = document.getElementById("retryBtn");

const dropZone = document.getElementById("dropZone");
const browseBtn = document.getElementById("browseBtn");
const fileInput = document.getElementById("fileInput");
const previewWrapper = document.getElementById("previewWrapper");
const previewImage = document.getElementById("previewImage");
const detectedTone = document.getElementById("detectedTone");

const genderSelect = document.getElementById("genderSelect");
const occasionSelect = document.getElementById("occasionSelect");
const seasonSelect = document.getElementById("seasonSelect");

startBtn.addEventListener("click", () => setView("upload"));
backToLandingBtn.addEventListener("click", () => setView("landing"));
tryAgainBtn.addEventListener("click", resetAndGoUpload);
retryBtn.addEventListener("click", () => {
  if (state.lastPayload) runRecommendation(state.lastPayload);
});

browseBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) handleFile(file);
});

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
  });
});

dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (file) handleFile(file);
});

recommendBtn.addEventListener("click", () => {
  if (!state.skinTone) {
    showToast("Upload a photo first to detect skin tone.");
    return;
  }

  const payload = {
    skin_tone: state.skinTone,
    gender: genderSelect.value,
    occasion: occasionSelect.value,
    season: seasonSelect.value,
  };

  state.lastPayload = payload;
  runRecommendation(payload);
});

async function handleFile(file) {
  if (!file.type.startsWith("image/")) {
    showToast("Please upload a valid image file.");
    return;
  }

  state.file = file;
  previewImage.src = URL.createObjectURL(file);
  previewWrapper.classList.remove("hidden");

  try {
    setUploadLoading(true);
    const uploadResult = await uploadImage(file);
    state.skinTone = uploadResult.skin_tone;

    detectedTone.textContent = `Detected Skin Tone: ${uploadResult.skin_tone}`;
    detectedTone.classList.remove("hidden");

    recommendBtn.disabled = false;
    showToast("Image analyzed successfully.", "success");
  } catch (error) {
    state.skinTone = null;
    recommendBtn.disabled = true;
    detectedTone.classList.add("hidden");
    showToast(error.message || "Image upload failed.");
  } finally {
    setUploadLoading(false);
  }
}

async function runRecommendation(payload) {
  setView("results");
  setRetryVisible(false);
  showSkeleton(true);

  try {
    const result = await fetchRecommendation(payload);
    renderRecommendation(result);
    showSkeleton(false);

    if (result.product_warning) {
      showToast(result.product_warning);
    } else {
      showToast("Recommendations generated.", "success");
    }
  } catch (error) {
    showSkeleton(false);
    setRetryVisible(true);
    showToast(error.message || "Could not fetch recommendations.");
  }
}

function resetAndGoUpload() {
  state.file = null;
  state.skinTone = null;
  state.lastPayload = null;

  previewImage.src = "";
  previewWrapper.classList.add("hidden");
  detectedTone.classList.add("hidden");
  recommendBtn.disabled = true;
  retryBtn.classList.add("hidden");
  fileInput.value = "";

  setView("upload");
}