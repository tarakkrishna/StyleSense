function listToHtml(items = []) {
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function shoppingItemsToHtml(items = []) {
  if (!items.length) {
    return '<p class="muted">No product results found right now. Try another occasion or season.</p>';
  }

  return items
    .map((item) => {
      const name = escapeHtml(item.title || "Style pick");
      const image = escapeHtml(item.image_url || "");
      const link = escapeHtml(item.product_link || "#");
      const price = escapeHtml(item.price || "N/A");
      const store = escapeHtml(item.source_store || "Store");
      const fallbackSvg = encodeURIComponent(
        "<svg xmlns='http://www.w3.org/2000/svg' width='800' height='1000'><rect width='100%' height='100%' fill='#1a2238'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' fill='#eaf2ff' font-size='42' font-family='Arial'>StyleAI Item</text></svg>"
      );

      return `
        <article class="shopping-item">
          <div class="shopping-image-wrap">
            <img
              src="${image}"
              alt="${name}"
              loading="lazy"
              onerror="this.onerror=null;this.src='data:image/svg+xml;utf8,${fallbackSvg}';"
            />
          </div>
          <div class="shopping-item-body">
            <p class="shopping-title">${name}</p>
            <p class="shopping-price">${price}</p>
            <p class="shopping-store">${store}</p>
            <a href="${link}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">Buy Now</a>
          </div>
        </article>
      `;
    })
    .join("");
}

export function showToast(message, type = "error") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3200);
}

export function setView(viewId) {
  document.querySelectorAll(".view").forEach((el) => el.classList.remove("active"));
  const target = document.getElementById(viewId);
  if (target) {
    target.classList.add("active");
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

export function setUploadLoading(isLoading) {
  document.getElementById("uploadLoader").classList.toggle("hidden", !isLoading);
}

export function showSkeleton(isVisible) {
  document.getElementById("skeleton").classList.toggle("hidden", !isVisible);
  document.getElementById("resultsGrid").classList.toggle("hidden", isVisible);
}

export function renderRecommendation(data) {
  const recommendation = data.ai_recommendation || {};
  const products = data.products || [];
  const mandatory = recommendation.mandatory_outfit || {};

  document.getElementById("mandatoryTop").textContent = mandatory.top || recommendation.outfit?.[0] || "-";
  document.getElementById("mandatoryBottom").textContent = mandatory.bottom || recommendation.outfit?.[1] || "-";
  document.getElementById("mandatoryFootwear").textContent =
    mandatory.footwear || mandatory.footware || recommendation.outfit?.[2] || "-";
  document.getElementById("outfitList").innerHTML = listToHtml(recommendation.outfit || []);
  document.getElementById("colorList").innerHTML = listToHtml(recommendation.colors || []);
  document.getElementById("accessoryList").innerHTML = listToHtml(recommendation.accessories || []);
  document.getElementById("hairstyleText").textContent = recommendation.hairstyle || "-";
  document.getElementById("whyText").textContent = recommendation.why_it_works || "-";
  document.getElementById("shoppingGrid").innerHTML = shoppingItemsToHtml(products);
}

export function setRetryVisible(isVisible) {
  document.getElementById("retryBtn").classList.toggle("hidden", !isVisible);
}
