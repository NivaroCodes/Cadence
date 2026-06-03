(function() {
  const form = document.getElementById('gen-form');
  if (!form) return;
  const company = document.getElementById('gen-company');
  const industry = document.getElementById('gen-industry');
  const language = document.getElementById('gen-language');
  const submit = document.getElementById('gen-submit');
  const empty = document.getElementById('gen-empty');
  const head = document.getElementById('gen-head');
  const typed = document.getElementById('gen-typed');
  const status = document.getElementById('gen-status');

  const templates = {
    'ru': (c, ind) => [
      { l: 'TO', t: `specialist@${(c || 'spotify').toLowerCase().replace(/\s+/g, '')}.kz` },
      { l: 'SUBJ', t: `Cadence: Personalized Email Automation for ${c || 'Spotify'}` },
      { l: 'LANG', t: 'RU' },
      { body: [
        `Здравствуйте,`,
        `Заметил, что ${c || 'Spotify'} активно расширяется в сегменте ${ind || 'Music Streaming'}.`,
        `Cadence пишет персонализированные письма каждому лиду на казахском, русском или английском, отправляет их через Gmail и отслеживает ответ автоматически.`,
        `Команды в КЗ экономят 4 часа в день.`,
        `Хотите узнать подробнее?`,
        `— Cadence Team`
      ]}
    ],
    'kz': (c, ind) => [
      { l: 'TO', t: `specialist@${(c || 'spotify').toLowerCase().replace(/\s+/g, '')}.kz` },
      { l: 'SUBJ', t: `Cadence: Personalized Email Automation for ${c || 'Spotify'}` },
      { l: 'LANG', t: 'KZ' },
      { body: [
        `Сәлеметсіз бе,`,
        `${c || 'Spotify'} ${ind || 'Music Streaming'} саласында белсенді өсіп жатқанын байқадым.`,
        `Cadence әр лидке қазақ, орыс немесе ағылшын тілінде дербес хат жазады, Gmail арқылы жібереді және жауаптарды автоматты түрде қадағалайды.`,
        `Қазақстандағы командалар күніне 4 сағат үнемдейді.`,
        `Толығырақ білгіңіз келе ме?`,
        `— Cadence Team`
      ]}
    ],
    'en': (c, ind) => [
      { l: 'TO', t: `specialist@${(c || 'spotify').toLowerCase().replace(/\s+/g, '')}.kz` },
      { l: 'SUBJ', t: `Cadence: Personalized Email Automation for ${c || 'Spotify'}` },
      { l: 'LANG', t: 'EN' },
      { body: [
        `Hi,`,
        `Noticed ${c || 'Spotify'} is expanding rapidly in ${ind || 'Music Streaming'}.`,
        `Cadence drafts personalised emails to every lead in Kazakh, Russian, or English, sends them via Gmail, and tracks replies automatically.`,
        `Teams in KZ are reclaiming 4 hours a day.`,
        `Would you like to learn more?`,
        `— Cadence Team`
      ]}
    ]
  };


  let typing = false;
  let abortTyping = null;

  const renderHead = (rows) => {
    head.innerHTML = '';
    rows.forEach((row, i) => {
      const div = document.createElement('div');
      div.className = 'line';
      div.innerHTML = `<span class="l">${row.l}</span><span class="t"></span>`;
      head.appendChild(div);
    });
    return [...head.querySelectorAll('.t')];
  };

  const typeText = (el, text, speed = 16, signal) => new Promise((resolve) => {
    let i = 0;
    const step = () => {
      if (signal && signal.aborted) return resolve();
      el.textContent = text.slice(0, i);
      if (i++ < text.length) {
        const d = Math.random() < 0.06 ? 80 : (speed + Math.random() * 20);
        setTimeout(step, d);
      } else resolve();
    };
    step();
  });

  const generate = async () => {
    if (typing) {
      if (abortTyping) abortTyping.abort();
    }
    typing = true;
    submit.disabled = true;
    submit.querySelector('.gen-label').textContent = 'Generating';
    const c = (company.value || '').trim();
    const ind = (industry.value || '').trim();
    const lang = language.value || 'ru';

    const rows = templates[lang](c, ind);
    const meta = rows.slice(0, 3);
    const body = rows.find(r => r.body).body;

    empty.style.display = 'none';
    head.style.display = '';
    typed.style.display = '';
    status.textContent = 'WRITING…';

    const targets = renderHead(meta);
    const ctrl = new AbortController();
    abortTyping = ctrl;
    for (let i = 0; i < meta.length; i++) {
      await typeText(targets[i], meta[i].t, 12, ctrl.signal);
      if (ctrl.signal.aborted) return cleanup();
    }

    typed.innerHTML = '';
    for (let i = 0; i < body.length; i++) {
      const p = document.createElement('p');
      p.style.marginBottom = '12px';
      typed.appendChild(p);
      const cursor = document.createElement('span');
      cursor.className = 'cursor';
      await typeText(p, body[i], 14, ctrl.signal);
      if (ctrl.signal.aborted) return cleanup();
      if (i < body.length - 1) {
        p.appendChild(cursor);
        await new Promise(r => setTimeout(r, 300));
        if (p.contains(cursor)) p.removeChild(cursor);
      }
    }
    status.textContent = 'READY · DRAFT';
    cleanup();
  };

  function cleanup() {
    typing = false;
    submit.disabled = false;
    submit.querySelector('.gen-label').textContent = 'Generate email';
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    generate();
  });
})();
