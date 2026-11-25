(function () {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. HERO ORBITAL BOOK WHEEL (16 capas em círculo com rotação contínua suave)
    const heroWheel = document.getElementById('hero-wheel');
    if (heroWheel) {
        const items = Array.from(heroWheel.querySelectorAll('.k50-orbital-item'));
        const total = items.length;
        let wheelAngle = 0;
        let speed = 0.08;
        let targetSpeed = 0.08;

        function positionHeroItems() {
            const radius = heroWheel.clientWidth * 0.43;
            items.forEach((el, idx) => {
                const deg = (360 / total) * idx;
                const rad = (deg * Math.PI) / 180;
                const x = Math.cos(rad) * radius;
                const y = Math.sin(rad) * radius;
                el.style.transform = `translate3d(${x}px, ${y}px, 0) rotate(${deg + 90}deg)`;
                el.classList.add('is-ready');
            });
        }

        positionHeroItems();
        window.addEventListener('resize', positionHeroItems);

        heroWheel.addEventListener('mouseenter', () => {
            targetSpeed = 0.015;
        });
        heroWheel.addEventListener('mouseleave', () => {
            targetSpeed = 0.08;
        });

        if (!reducedMotion) {
            const animateHeroWheel = () => {
                speed += (targetSpeed - speed) * 0.06;
                wheelAngle = (wheelAngle + speed) % 360;
                heroWheel.style.transform = `rotate(${wheelAngle}deg)`;
                requestAnimationFrame(animateHeroWheel);
            };
            requestAnimationFrame(animateHeroWheel);
        }
    }

    // 2. SCROLL-DRIVEN WORD-BY-WORD HIGHLIGHT
    const highlightSection = document.getElementById('destaque');
    const highlightText = document.getElementById('highlight-text');
    let wordSpans = [];

    if (highlightText) {
        const words = highlightText.textContent.trim().split(/\s+/);
        highlightText.innerHTML = '';
        wordSpans = words.map((word) => {
            const span = document.createElement('span');
            span.className = 'hl-word';
            span.textContent = `${word} `;
            highlightText.appendChild(span);
            return span;
        });
    }

    const parallaxEls = Array.from(document.querySelectorAll('[data-parallax]'));

    function handleScrollEffects() {
        const vh = window.innerHeight || 800;

        if (!reducedMotion && highlightSection && wordSpans.length > 0) {
            const rect = highlightSection.getBoundingClientRect();
            const progress = Math.min(1, Math.max(0, (vh * 0.85 - rect.top) / (vh * 0.72)));
            const litCount = Math.round(progress * wordSpans.length);
            wordSpans.forEach((span, idx) => {
                span.classList.toggle('is-lit', idx < litCount);
            });
        }

        if (!reducedMotion) {
            parallaxEls.forEach((el) => {
                const factor = parseFloat(el.dataset.parallax || '0');
                const rect = el.getBoundingClientRect();
                const centerOffset = (rect.top + rect.height / 2 - vh / 2) / vh;
                const y = centerOffset * factor;
                el.style.transform = `translate3d(0, ${y.toFixed(1)}px, 0)`;
            });
        }
    }

    handleScrollEffects();
    window.addEventListener('scroll', handleScrollEffects, { passive: true });

    // 3. INTERSECTION OBSERVER PARA HEADLINES E BLOCOS
    const revealEls = document.querySelectorAll('[data-scroll-reveal]');
    if ('IntersectionObserver' in window && !reducedMotion) {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.16 }
        );
        revealEls.forEach((el) => observer.observe(el));
    } else {
        revealEls.forEach((el) => el.classList.add('is-visible'));
    }

    // 4. RODA INTERATIVA DE CAPAS (ARRASTAR COM INÉRCIA + CLIQUE + SETAS)
    const viewport = document.getElementById('story-wheel-viewport');
    const disc = document.getElementById('story-wheel-disc');
    const spotlight = document.getElementById('story-spotlight');
    const metaEl = document.getElementById('spotlight-meta');
    const titleEl = document.getElementById('spotlight-title');
    const authorEl = document.getElementById('spotlight-author');
    const summaryEl = document.getElementById('spotlight-summary');
    const prevBtn = document.getElementById('wheel-prev');
    const nextBtn = document.getElementById('wheel-next');

    if (viewport && disc) {
        const cards = Array.from(disc.querySelectorAll('.k50-story-card'));
        const count = cards.length;
        const stepDeg = 360 / count;
        const discRadius = 470;

        cards.forEach((card, idx) => {
            const deg = stepDeg * idx - 90;
            const rad = (deg * Math.PI) / 180;
            const x = Math.cos(rad) * discRadius;
            const y = Math.sin(rad) * discRadius;
            card.style.transform = `translate3d(${x}px, ${y}px, 0) rotate(${deg + 90}deg)`;
        });

        let currentAngle = 0;
        let targetAngle = 0;
        let activeIndex = 0;
        let isDragging = false;
        let dragMoved = false;
        let startX = 0;
        let startAngle = 0;
        let velocity = 0;
        let lastX = 0;

        function normalizarIndice(idx) {
            return ((idx % count) + count) % count;
        }

        function atualizarSpotlight(idx) {
            const norm = normalizarIndice(idx);
            if (norm === activeIndex && cards[norm].classList.contains('is-active')) {
                return;
            }
            activeIndex = norm;
            cards.forEach((c, i) => c.classList.toggle('is-active', i === norm));

            const card = cards[norm];
            if (!spotlight || !card) {
                return;
            }
            spotlight.classList.add('is-switching');
            setTimeout(() => {
                metaEl.textContent = `${card.dataset.categoria} · ${card.dataset.ano}`;
                titleEl.textContent = card.dataset.titulo;
                authorEl.textContent = card.dataset.autor;
                summaryEl.textContent = card.dataset.resumo;
                spotlight.classList.remove('is-switching');
            }, 120);
        }

        function irParaIndice(idx) {
            const targetStep = -idx * stepDeg;
            // Escolhe a volta mais curta a partir do ângulo atual
            const diff = ((((targetStep - targetAngle) % 360) + 540) % 360) - 180;
            targetAngle += diff;
            atualizarSpotlight(idx);
        }

        cards[0]?.classList.add('is-active');

        viewport.addEventListener('pointerdown', (e) => {
            isDragging = true;
            dragMoved = false;
            startX = e.clientX;
            lastX = e.clientX;
            startAngle = targetAngle;
            velocity = 0;
        });

        viewport.addEventListener('pointermove', (e) => {
            if (!isDragging) {
                return;
            }
            const dx = e.clientX - startX;
            if (!dragMoved && Math.abs(dx) > 6) {
                dragMoved = true;
                viewport.classList.add('is-dragging');
                try {
                    viewport.setPointerCapture(e.pointerId);
                } catch {}
            }
            if (!dragMoved) {
                return;
            }
            velocity = (e.clientX - lastX) * 0.22;
            lastX = e.clientX;
            targetAngle = startAngle + dx * 0.16;

            const nearest = Math.round(-targetAngle / stepDeg);
            atualizarSpotlight(nearest);
        });

        function finalizarArraste() {
            if (!isDragging) {
                return;
            }
            isDragging = false;
            viewport.classList.remove('is-dragging');
            if (!dragMoved) {
                return;
            }
            targetAngle += velocity * 4;
            const snapped = Math.round(-targetAngle / stepDeg);
            targetAngle = -snapped * stepDeg;
            atualizarSpotlight(snapped);
        }

        viewport.addEventListener('pointerup', finalizarArraste);
        viewport.addEventListener('pointercancel', finalizarArraste);

        cards.forEach((card, idx) => {
            card.addEventListener('click', () => {
                if (dragMoved) {
                    return;
                }
                irParaIndice(idx);
            });
        });

        prevBtn?.addEventListener('click', () => irParaIndice(activeIndex - 1));
        nextBtn?.addEventListener('click', () => irParaIndice(activeIndex + 1));

        const loopWheel = () => {
            currentAngle += (targetAngle - currentAngle) * (isDragging ? 0.35 : 0.12);
            disc.style.transform = `rotate(${currentAngle}deg)`;
            requestAnimationFrame(loopWheel);
        };
        requestAnimationFrame(loopWheel);
    }

    // 5. PREVIEW FLUTUANTE DE CAPA NO CATÁLOGO NUMERADO
    const preview = document.getElementById('hover-preview');
    const previewImg = document.getElementById('hover-preview-img');
    const nameItems = document.querySelectorAll('.k50-name-item');

    if (preview && previewImg && nameItems.length > 0) {
        nameItems.forEach((item) => {
            item.addEventListener('mouseenter', () => {
                previewImg.src = item.dataset.cover || '';
                previewImg.alt = item.dataset.title || '';
                preview.classList.add('is-visible');
            });
            item.addEventListener('mousemove', (e) => {
                preview.style.left = `${e.clientX + 20}px`;
                preview.style.top = `${e.clientY - 80}px`;
            });
            item.addEventListener('mouseleave', () => {
                preview.classList.remove('is-visible');
            });
        });
    }
})();
