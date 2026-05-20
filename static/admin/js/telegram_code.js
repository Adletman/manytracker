(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function showToast(text) {
    let toast = document.getElementById("tg-code-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "tg-code-toast";
      toast.style.cssText =
        "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);" +
        "background:#222;color:#fff;padding:12px 20px;border-radius:6px;" +
        "font-size:14px;z-index:9999;box-shadow:0 2px 12px rgba(0,0,0,.3);";
      document.body.appendChild(toast);
    }
    toast.textContent = text;
    toast.style.display = "block";
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.display = "none"; }, 4000);
  }

  document.addEventListener("click", async function (e) {
    const btn = e.target.closest(".btn-gen-tg-code");
    if (!btn) return;
    e.preventDefault();

    const userId = btn.dataset.userId;
    const url = `/admin/accounts/user/${userId}/gen-tg-code/`;
    const csrf = getCookie("csrftoken");

    btn.disabled = true;
    btn.textContent = "...";

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();
      await navigator.clipboard.writeText(data.copy_text);
      btn.textContent = "✓ " + data.code;
      showToast("Скопировано: код " + data.code + " (действует 10 мин)");
    } catch (err) {
      btn.textContent = "Сген. код";
      btn.disabled = false;
      alert("Ошибка: " + err.message);
    }
  });
})();
