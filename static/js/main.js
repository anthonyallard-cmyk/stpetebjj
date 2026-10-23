/* St. Pete Brazilian Jiu-Jitsu — Frontend Interactive Controller */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Sticky Navbar Scroll Blur State
    const header = document.getElementById("site-header");
    const handleScroll = () => {
        if (!header) return;
        if (window.scrollY > 24) {
            header.classList.add("scrolled");
        } else {
            header.classList.remove("scrolled");
        }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    // 2. Mobile Navigation Drawer
    const mobileBtn = document.getElementById("mobile-menu-btn");
    const mobileMenu = document.getElementById("mobile-menu");
    if (mobileBtn && mobileMenu) {
        mobileBtn.addEventListener("click", () => {
            mobileMenu.classList.toggle("hidden");
        });
    }

    // 3. Live Search Autocomplete (Header & Mobile)
    const searchInput = document.getElementById("header-search-input");
    const searchDropdown = document.getElementById("header-search-dropdown");
    let debounceTimer = null;

    if (searchInput && searchDropdown) {
        searchInput.addEventListener("input", (e) => {
            const q = e.target.value.trim();
            clearTimeout(debounceTimer);
            if (q.length < 1) {
                searchDropdown.classList.add("hidden");
                searchDropdown.innerHTML = "";
                return;
            }
            debounceTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/search/autocomplete?q=${encodeURIComponent(q)}`);
                    const data = await res.json();
                    const items = data.results || [];
                    if (items.length === 0) {
                        searchDropdown.innerHTML = `
                            <div class="p-4 text-center text-sm text-zinc-400">
                                No direct matches for "<span class="text-white font-semibold">${q}</span>".
                                <a href="/contact" class="block mt-2 text-[#CE1E36] font-semibold hover:underline">Ask us or book a Free Class &rarr;</a>
                            </div>`;
                        searchDropdown.classList.remove("hidden");
                        return;
                    }
                    searchDropdown.innerHTML = items.map(item => `
                        <a href="${item.url}" class="flex items-center gap-3 p-3 hover:bg-zinc-800/90 transition border-b border-zinc-800/80 last:border-0">
                            <img src="${item.image}" alt="${item.title}" class="w-11 h-11 rounded-lg object-cover bg-zinc-900 border border-zinc-700 shrink-0" onerror="this.src='/static/images/logo-circle.png'">
                            <div class="min-w-0 flex-1">
                                <div class="flex items-center gap-2">
                                    <span class="text-[10px] font-mono-tech uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#CE1E36]/20 text-[#FF4D64] border border-[#CE1E36]/30">${item.type}</span>
                                </div>
                                <div class="text-sm font-bold text-white truncate mt-0.5">${item.title}</div>
                                <div class="text-xs text-zinc-400 truncate">${item.subtitle || ''}</div>
                            </div>
                        </a>
                    `).join("");
                    searchDropdown.classList.remove("hidden");
                } catch (err) {
                    console.error("Autocomplete error:", err);
                }
            }, 180);
        });

        document.addEventListener("click", (e) => {
            if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
                searchDropdown.classList.add("hidden");
            }
        });
    }

    // 4. Hero Slider
    const slides = document.querySelectorAll(".hero-slide");
    const dots = document.querySelectorAll(".hero-dot");
    const prevBtn = document.getElementById("hero-prev");
    const nextBtn = document.getElementById("hero-next");

    if (slides.length > 1) {
        let currentSlide = 0;
        let slideInterval = null;

        const goToSlide = (idx) => {
            slides[currentSlide].classList.remove("active");
            if (dots[currentSlide]) {
                dots[currentSlide].classList.remove("bg-[#CE1E36]", "w-8");
                dots[currentSlide].classList.add("bg-white/40", "w-2.5");
            }
            currentSlide = (idx + slides.length) % slides.length;
            slides[currentSlide].classList.add("active");
            if (dots[currentSlide]) {
                dots[currentSlide].classList.remove("bg-white/40", "w-2.5");
                dots[currentSlide].classList.add("bg-[#CE1E36]", "w-8");
            }
        };

        const startAuto = () => {
            clearInterval(slideInterval);
            slideInterval = setInterval(() => goToSlide(currentSlide + 1), 6500);
        };

        if (prevBtn) {
            prevBtn.addEventListener("click", () => {
                goToSlide(currentSlide - 1);
                startAuto();
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener("click", () => {
                goToSlide(currentSlide + 1);
                startAuto();
            });
        }
        dots.forEach((dot, i) => {
            dot.addEventListener("click", () => {
                goToSlide(i);
                startAuto();
            });
        });
        startAuto();
    }

    // 5. FAQ Accordions
    document.querySelectorAll(".faq-toggle").forEach((btn) => {
        btn.addEventListener("click", () => {
            const content = btn.nextElementSibling;
            const icon = btn.querySelector(".faq-icon");
            const isOpen = !content.classList.contains("hidden");
            if (isOpen) {
                content.classList.add("hidden");
                if (icon) icon.style.transform = "rotate(0deg)";
            } else {
                content.classList.remove("hidden");
                if (icon) icon.style.transform = "rotate(180deg)";
            }
        });
    });

    // 6. Photo Lightbox Modal
    const lightbox = document.getElementById("photo-lightbox");
    const lightboxImg = document.getElementById("lightbox-img");
    const lightboxCaption = document.getElementById("lightbox-caption");
    const lightboxClose = document.getElementById("lightbox-close");
    const lightboxPrev = document.getElementById("lightbox-prev");
    const lightboxNext = document.getElementById("lightbox-next");
    const galleryTriggers = Array.from(document.querySelectorAll("[data-lightbox-src]"));
    let activePhotoIdx = 0;

    if (lightbox && galleryTriggers.length > 0) {
        const showPhoto = (idx) => {
            activePhotoIdx = (idx + galleryTriggers.length) % galleryTriggers.length;
            const el = galleryTriggers[activePhotoIdx];
            lightboxImg.src = el.getAttribute("data-lightbox-src");
            if (lightboxCaption) {
                lightboxCaption.textContent = el.getAttribute("data-lightbox-caption") || "";
            }
            lightbox.classList.remove("hidden");
            lightbox.classList.add("flex");
        };

        galleryTriggers.forEach((el, idx) => {
            el.addEventListener("click", (e) => {
                e.preventDefault();
                showPhoto(idx);
            });
        });

        const closeLightbox = () => {
            lightbox.classList.add("hidden");
            lightbox.classList.remove("flex");
        };

        if (lightboxClose) lightboxClose.addEventListener("click", closeLightbox);
        if (lightboxPrev) lightboxPrev.addEventListener("click", () => showPhoto(activePhotoIdx - 1));
        if (lightboxNext) lightboxNext.addEventListener("click", () => showPhoto(activePhotoIdx + 1));

        lightbox.addEventListener("click", (e) => {
            if (e.target === lightbox) closeLightbox();
        });

        document.addEventListener("keydown", (e) => {
            if (lightbox.classList.contains("hidden")) return;
            if (e.key === "Escape") closeLightbox();
            if (e.key === "ArrowLeft") showPhoto(activePhotoIdx - 1);
            if (e.key === "ArrowRight") showPhoto(activePhotoIdx + 1);
        });
    }

    // 7. Free Trial / Inquiry Form Handler with Google reCAPTCHA v3
    document.querySelectorAll(".bjj-inquiry-form").forEach((form) => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector("button[type='submit']");
            const statusBox = form.querySelector(".form-status-box");
            const originalText = submitBtn ? submitBtn.innerHTML : "Submit";

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<span>Submitting...</span>`;
            }

            let recaptchaToken = "local-test";
            const siteKey = window.RECAPTCHA_SITE_KEY || "";
            if (window.grecaptcha && siteKey) {
                try {
                    recaptchaToken = await new Promise((resolve) => {
                        window.grecaptcha.ready(() => {
                            window.grecaptcha
                                .execute(siteKey, { action: "submit_inquiry" })
                                .then(resolve)
                                .catch(() => resolve("local-test"));
                        });
                    });
                } catch (_) {
                    recaptchaToken = "local-test";
                }
            }

            const formData = new FormData(form);
            const payload = {
                name: formData.get("name") || "",
                email: formData.get("email") || "",
                phone: formData.get("phone") || "",
                program_interest: formData.get("program_interest") || "Free Introductory Class (Fundamentals)",
                experience_level: formData.get("experience_level") || "Brand New Beginner",
                preferred_date: formData.get("preferred_date") || "",
                message: formData.get("message") || "",
                website_url: formData.get("website_url") || "",
                recaptcha_token: recaptchaToken,
            };

            try {
                const res = await fetch("/api/quote/submit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const result = await res.json();
                if (res.ok && result.status === "ok") {
                    form.reset();
                    if (statusBox) {
                        statusBox.className = "form-status-box mt-4 p-4 rounded-xl bg-emerald-950/90 border border-emerald-500/40 text-emerald-200 text-sm font-medium";
                        statusBox.innerHTML = `<strong class="block text-white mb-1">&#10003; Free Class / Inquiry Request Confirmed!</strong> ${result.message}`;
                        statusBox.classList.remove("hidden");
                    }
                } else {
                    if (statusBox) {
                        statusBox.className = "form-status-box mt-4 p-4 rounded-xl bg-red-950/90 border border-red-500/40 text-red-200 text-sm font-medium";
                        statusBox.textContent = result.detail || "Unable to submit right now. Please text or call (727) 619-4255.";
                        statusBox.classList.remove("hidden");
                    }
                }
            } catch (err) {
                if (statusBox) {
                    statusBox.className = "form-status-box mt-4 p-4 rounded-xl bg-red-950/90 border border-red-500/40 text-red-200 text-sm font-medium";
                    statusBox.textContent = "Network error. Please text or call (727) 619-4255.";
                    statusBox.classList.remove("hidden");
                }
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            }
        });
    });
});
