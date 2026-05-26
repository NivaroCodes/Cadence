(function() {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  const onScroll = () => {
    if (window.scrollY > 20) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  const timeEl = document.querySelector('.live-time');
  if (timeEl) {
    const updateTime = () => {
      timeEl.textContent = new Date().toLocaleTimeString('ru-KZ', {
        timeZone: 'Asia/Almaty',
        hour: '2-digit',
        minute: '2-digit'
      });
    };
    updateTime();
    setInterval(updateTime, 1000);
  }
})();
