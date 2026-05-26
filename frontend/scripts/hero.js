(function() {
  // mask-line headline reveal on load
  requestAnimationFrame(() => {
    document.querySelectorAll('.hero .mask-line').forEach((el, i) => {
      el.style.setProperty('--reveal-delay', (i * 90) + 'ms');
      setTimeout(() => el.classList.add('in'), 80);
    });
  });

  const body = document.getElementById('hero-email-body');
  const progressBar = document.getElementById('hero-email-progress');
  const statusEl = document.querySelector('.email-head .status');
  if (!body) return;

  const EMAILS = {
    ru: {
      head: 'Тема: Снижение времени онбординга для команды Kazpost',
      paragraphs: [
        'Здравствуйте, Айгерим.',
        'Заметил, что Kazpost недавно объявил о развёртывании новой логистической системы в 14 регионах. Команды такого масштаба обычно теряют первые 6 недель на обучение сотрудников.',
        'Cadence пишет персонализированные письма каждому лиду — на казахском, русском или английском — и автоматически отслеживает ответы.',
        'Стоит ли показать, как это сэкономит вам 4 часа в день?'
      ],
      sig: 'AGENT · GMAIL THREAD #4291 · DRAFT'
    },
    kz: {
      head: 'Тақырыбы: Kazpost командасы үшін онбординг уақытын қысқарту',
      paragraphs: [
        'Сәлеметсіз бе, Айгерим.',
        'Kazpost жақында 14 өңірде жаңа логистикалық жүйені іске қосатынын жариялағанын байқадым. Мұндай ауқымдағы командалар көбінесе алғашқы 6 аптаны қызметкерлерді оқытуға жоғалтады.',
        'Cadence әрбір лидке қазақ, орыс немесе ағылшын тілдерінде дербес хат жазады және жауаптарды автоматты түрде қадағалайды.',
        'Сізге күніне 4 сағат үнемдеуге қалай көмектесетінін көрсетейін бе?'
      ],
      sig: 'AGENT · GMAIL THREAD #4291 · DRAFT'
    },
    en: {
      head: 'Subject: Cutting onboarding time for the Kazpost team',
      paragraphs: [
        'Hi Aigerim,',
        'Saw that Kazpost just announced a new logistics system rollout across 14 regions. Teams at that scale usually lose the first six weeks to training their people.',
        'Cadence writes personalised emails to every lead — in Kazakh, Russian, or English — and tracks replies automatically.',
        'Worth showing how this saves you 4 hours a day?'
      ],
      sig: 'AGENT · GMAIL THREAD #4291 · DRAFT'
    }
  };

  let typingHandle = null;
  let staticMode = false;

  const cancelTyping = () => {
    if (typingHandle) {
      clearTimeout(typingHandle);
      typingHandle = null;
    }
  };

  const renderStatic = (lang) => {
    cancelTyping();
    staticMode = true;
    const e = EMAILS[lang];
    body.innerHTML = '';

    const head = document.createElement('div');
    head.className = 'typed-line head show';
    head.style.fontFamily = "'JetBrains Mono', monospace";
    head.style.fontSize = '11px';
    head.style.letterSpacing = '0.12em';
    head.style.textTransform = 'uppercase';
    head.style.color = 'var(--muted)';
    head.style.marginBottom = '16px';
    head.textContent = e.head;
    body.appendChild(head);

    e.paragraphs.forEach(p => {
      const para = document.createElement('p');
      para.className = 'typed-line show';
      para.textContent = p;
      body.appendChild(para);
    });

    const sig = document.createElement('div');
    sig.className = 'sig';
    sig.textContent = e.sig;
    body.appendChild(sig);

    progressBar.style.width = '100%';
    if (statusEl) {
      statusEl.innerHTML = '<span class="pulse" style="animation:none;"></span>DRAFT · ' + lang.toUpperCase();
    }
  };

  // Pills click handler
  const pills = document.querySelectorAll('.hero-right .lang-pills .pill');
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      const lang = pill.textContent.trim().toLowerCase();
      if (!EMAILS[lang]) return;
      pills.forEach(p => p.classList.toggle('on', p === pill));
      renderStatic(lang);
    });
  });

  // Initial typing animation — RU body
  const lines = [
    { type: 'h', text: EMAILS.ru.head },
    ...EMAILS.ru.paragraphs.map(text => ({ type: 'p', text })),
    { type: 'sig', text: EMAILS.ru.sig }
  ];

  let lineIdx = 0;
  let charIdx = 0;
  let currentEl = null;
  let totalChars = lines.reduce((a, l) => a + l.text.length, 0);
  let done = 0;

  const tick = () => {
    if (staticMode) return;
    if (lineIdx >= lines.length) {
      progressBar.style.width = '100%';
      typingHandle = setTimeout(() => {
        if (staticMode) return;
        body.innerHTML = '';
        lineIdx = 0; charIdx = 0; done = 0; currentEl = null;
        progressBar.style.width = '0%';
        tick();
      }, 6000);
      return;
    }
    const line = lines[lineIdx];
    if (!currentEl) {
      currentEl = document.createElement(line.type === 'sig' ? 'div' : 'p');
      currentEl.className = line.type === 'sig' ? 'sig' : (line.type === 'h' ? 'typed-line head' : 'typed-line');
      if (line.type === 'h') {
        currentEl.style.fontFamily = "'JetBrains Mono', monospace";
        currentEl.style.fontSize = '11px';
        currentEl.style.letterSpacing = '0.12em';
        currentEl.style.textTransform = 'uppercase';
        currentEl.style.color = 'var(--muted)';
        currentEl.style.marginBottom = '16px';
      }
      body.appendChild(currentEl);
      requestAnimationFrame(() => currentEl.classList.add('show'));
    }
    if (charIdx < line.text.length) {
      currentEl.textContent = line.text.slice(0, charIdx + 1);
      const cursor = document.createElement('span');
      cursor.className = 'cursor';
      currentEl.appendChild(cursor);
      charIdx++;
      done++;
      progressBar.style.width = ((done / totalChars) * 100) + '%';
      const delay = line.type === 'sig' ? 14 : (Math.random() < 0.08 ? 90 : (18 + Math.random() * 28));
      typingHandle = setTimeout(tick, delay);
    } else {
      currentEl.textContent = line.text;
      lineIdx++;
      charIdx = 0;
      currentEl = null;
      typingHandle = setTimeout(tick, lineIdx === 1 ? 350 : 520);
    }
  };

  typingHandle = setTimeout(tick, 900);
})();
