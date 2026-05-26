(function() {
  // 1. Generic reveal observer
  const revealEls = document.querySelectorAll('[data-reveal]');
  const revealIO = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        revealIO.unobserve(e.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
  revealEls.forEach(el => revealIO.observe(el));

  // 2. Counters
  const counters = document.querySelectorAll('[data-counter]');
  const formatNum = (val, target) => {
    if (Number.isInteger(target)) return Math.round(val).toString();
    return val.toFixed(0);
  };
  const counterIO = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      const target = parseFloat(el.dataset.counter);
      const dur = parseFloat(el.dataset.duration || 1800);
      const start = performance.now();
      const tick = (t) => {
        const p = Math.min(1, (t - start) / dur);
        const eased = 1 - Math.pow(1 - p, 4);
        el.textContent = formatNum(target * eased, target);
        if (p < 1) requestAnimationFrame(tick);
        else el.textContent = formatNum(target, target);
      };
      requestAnimationFrame(tick);
      counterIO.unobserve(el);
    });
  }, { threshold: 0.35 });
  counters.forEach(el => counterIO.observe(el));

  // 3. Sticky horizontal scroll for "How it works"
  const pin = document.querySelector('.how-pin');
  const track = document.querySelector('.how-track');
  const rail = document.querySelector('.how-rail');
  const progressFill = document.querySelector('.how-progress-bar span');
  const progressCurrent = document.querySelector('.how-progress .current');
  const progressTotal = document.querySelector('.how-progress .total');

  if (pin && track && rail && window.matchMedia('(min-width: 721px)').matches) {
    const stepCount = rail.children.length;
    if (progressTotal) progressTotal.textContent = String(stepCount).padStart(2, '0');

    const update = () => {
      const rect = pin.getBoundingClientRect();
      const start = 0;
      const end = pin.offsetHeight - window.innerHeight;
      const progress = Math.max(0, Math.min(1, -rect.top / end));
      const maxX = rail.scrollWidth - track.clientWidth + parseFloat(getComputedStyle(track).paddingLeft) + parseFloat(getComputedStyle(track).paddingRight);
      const x = -progress * (rail.scrollWidth - window.innerWidth + 80);
      track.style.transform = `translate3d(${x}px, 0, 0)`;
      if (progressFill) progressFill.style.width = (progress * 100) + '%';
      if (progressCurrent) {
        const step = Math.min(stepCount, Math.floor(progress * stepCount) + 1);
        progressCurrent.textContent = String(step).padStart(2, '0');
      }
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
  }

  // 4. Timeline draw on scroll
  const tlAxis = document.querySelector('.timeline-axis-fill');
  const timeline = document.querySelector('.timeline');
  const tlItems = document.querySelectorAll('.tl-item');

  if (tlAxis && timeline) {
    const updateTl = () => {
      const r = timeline.getBoundingClientRect();
      const vh = window.innerHeight;
      const total = r.height;
      const visibleStart = vh * 0.7 - r.top;
      const progress = Math.max(0, Math.min(1, visibleStart / total));
      tlAxis.style.height = (progress * 100) + '%';
    };
    updateTl();
    window.addEventListener('scroll', updateTl, { passive: true });
    window.addEventListener('resize', updateTl);

    const tlIO = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          tlIO.unobserve(e.target);
        }
      });
    }, { threshold: 0.25 });
    tlItems.forEach(el => tlIO.observe(el));
  }

  // 5. Smooth anchor scrolling
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href');
      if (id.length < 2) return;
      const target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        const y = target.getBoundingClientRect().top + window.scrollY - 40;
        window.scrollTo({ top: y, behavior: 'smooth' });
      }
    });
  });

  // 6. Video play (visual demo only)
  const player = document.querySelector('.video-player');
  if (player) {
    player.addEventListener('click', () => {
      player.classList.toggle('playing');
    });
  }

  // 7. Early access form
  const accessForm = document.getElementById('access-form');
  if (accessForm) {
    accessForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const success = document.getElementById('access-success');
      const input = accessForm.querySelector('input');
      if (input && input.value.includes('@')) {
        accessForm.style.display = 'none';
        if (success) success.classList.add('show');
      }
    });
  }
})();
