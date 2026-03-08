const API_BASE = "https://ai-bazaar-backend-g2yb.onrender.com";

document.addEventListener("DOMContentLoaded", function () {
    if (localStorage.getItem("access_token")) {
        window.location.href = "dashboard.html";
        return;
    }
    initLoginTabs();
    initPasswordToggles();
    setupForms();
});

function initLoginTabs() {
    const tabs = document.querySelectorAll(".login-tab");
    const forms = document.querySelectorAll(".login-form");
    tabs.forEach(tab => {
        tab.addEventListener("click", function () {
            const tabId = this.getAttribute("data-tab");
            tabs.forEach(t => t.classList.remove("active"));
            this.classList.add("active");
            forms.forEach(form => {
                form.classList.remove("active");
                if (form.id === tabId + "Form") form.classList.add("active");
            });
        });
    });
}

function initPasswordToggles() {
    document.querySelectorAll(".password-toggle").forEach(toggle => {
        toggle.addEventListener("click", function () {
            const input = document.getElementById(this.id.replace("toggle", ""));
            if (!input) return;
            input.type = input.type === "password" ? "text" : "password";
        });
    });
}

function setupForms() {
    const loginForm = document.getElementById("loginForm");
    const signupForm = document.getElementById("signupForm");
    if (loginForm) loginForm.addEventListener("submit", doLogin);
    if (signupForm) signupForm.addEventListener("submit", doSignup);
}

async function doLogin(e) {
    e.preventDefault();

    const phone = document.getElementById("loginPhone").value.trim();
    const password = document.getElementById("loginPassword").value;
    const phoneErr = document.getElementById("loginPhoneError");
    const successMsg = document.getElementById("loginSuccess");
    const btn = e.target.querySelector("button[type=submit]");

    phoneErr.style.display = "none";
    successMsg.style.display = "none";

    if (!phone || phone.length < 10) {
        phoneErr.innerText = "Enter valid 10 digit phone number";
        phoneErr.style.display = "block";
        return;
    }
    if (!password || password.length < 6) {
        phoneErr.innerText = "Password must be at least 6 characters";
        phoneErr.style.display = "block";
        return;
    }

    btn.disabled = true;
    btn.innerText = "Please wait...";

    try {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone: phone, password: password })
        });

        const data = await res.json();

        if (res.ok && data.access_token) {
            localStorage.setItem("access_token", data.access_token);

            successMsg.innerText = "Login successful! Redirecting to dashboard...";
            successMsg.style.display = "block";
            phoneErr.style.display = "none";

            setTimeout(() => {
                window.location.href = "dashboard/dashboard_index.html";
            }, 1000);

        } else {
            phoneErr.innerText = data.detail || "Wrong phone or password. Try again.";
            phoneErr.style.display = "block";
        }

    } catch (err) {
        phoneErr.innerText = "Cannot reach server. Please try again.";
        phoneErr.style.display = "block";
    } finally {
        btn.disabled = false;
        btn.innerText = "Login";
    }
}

async function doSignup(e) {
    e.preventDefault();

    const name = document.getElementById("signupName").value.trim();
    const phone = document.getElementById("signupPhone").value.trim();
    const password = document.getElementById("signupPassword").value;
    const confirm = document.getElementById("signupConfirmPassword").value;
    const language = document.getElementById("signupLanguage");
    const terms = document.getElementById("termsAgreement");
    const phoneErr = document.getElementById("signupPhoneError");
    const successMsg = document.getElementById("signupSuccess");
    const btn = e.target.querySelector("button[type=submit]");

    phoneErr.style.display = "none";
    successMsg.style.display = "none";

    if (!name) { phoneErr.innerText = "Name is required"; phoneErr.style.display = "block"; return; }
    if (!phone || phone.length < 10) { phoneErr.innerText = "Enter valid 10 digit phone"; phoneErr.style.display = "block"; return; }
    if (!password || password.length < 6) { phoneErr.innerText = "Password must be 6+ characters"; phoneErr.style.display = "block"; return; }
    if (password !== confirm) { phoneErr.innerText = "Passwords do not match"; phoneErr.style.display = "block"; return; }
    if (terms && !terms.checked) { alert("Please agree to Terms & Conditions"); return; }

    btn.disabled = true;
    btn.innerText = "Creating...";

    try {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: name,
                phone: phone,
                password: password,
                language: language ? language.value : "en"
            })
        });

        const data = await res.json();

        if (res.ok) {
            successMsg.innerText = "Account created! Please login now.";
            successMsg.style.display = "block";
            setTimeout(function () {
                const loginTab = document.querySelector(".login-tab[data-tab='login']");
                if (loginTab) loginTab.click();
                const lp = document.getElementById("loginPhone");
                if (lp) lp.value = phone;
            }, 1500);
        } else {
            phoneErr.innerText = data.detail || "Registration failed. Try again.";
            phoneErr.style.display = "block";
        }

    } catch (err) {
        phoneErr.innerText = "Cannot reach server. Please try again.";
        phoneErr.style.display = "block";
    } finally {
        btn.disabled = false;
        btn.innerText = "Create Account";
    }
}
