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
      { l: 'TO', t: `${(c || 'Компания').toLowerCase().replace(/\s+/g, '.')}@example.kz` },
      { l: 'SUBJ', t: `Cadence × ${c || 'Компания'} — 12 минут?` },
      { l: 'LANG', t: 'RU · автоматически определён' },
      { body: [
        `Здравствуйте, Алибек.`,
        `Заметил, что ${c || 'ваша компания'} активно расширяется в сегменте ${ind || 'B2B-логистики'} — это требует серьёзного outbound-пайплайна.`,
        `Cadence пишет персонализированные письма каждому лиду на казахском, русском или английском, отправляет их через Gmail и отслеживает ответы автоматически.`,
        `Команды в КЗ экономят 4 часа в день. Покажу 12-минутное демо?`,
        `— Динара, Cadence`
      ]}
    ],
    'kz': (c, ind) => [
      { l: 'TO', t: `${(c || 'kompaniya').toLowerCase().replace(/\s+/g, '.')}@example.kz` },
      { l: 'SUBJ', t: `${c || 'Компанияңыз'} үшін Cadence — 12 минут?` },
      { l: 'LANG', t: 'KZ · автоматически определён' },
      { body: [
        `Сәлеметсіз бе, Алибек.`,
        `${c || 'Сіздің компанияңыз'} ${ind || 'B2B-логистика'} саласында белсенді өсіп жатқанын байқадым.`,
        `Cadence әр лидке қазақ, орыс немесе ағылшын тілінде дербес хат жазады, Gmail арқылы жібереді және жауаптарды автоматты түрде қадағалайды.`,
        `Қазақстандағы командалар күніне 4 сағат үнемдейді. 12 минуттық демо көрсетейін бе?`,
        `— Динара, Cadence`
      ]}
    ],
    'en': (c, ind) => [
      { l: 'TO', t: `intro@${(c || 'company').toLowerCase().replace(/\s+/g, '')}.com` },
      { l: 'SUBJ', t: `${c || 'Company'} × Cadence — 12 minutes?` },
      { l: 'LANG', t: 'EN · auto-detected' },
      { body: [
        `Hi Alibek,`,
        `Noticed ${c || 'your team'} is expanding rapidly in ${ind || 'B2B logistics'} — that demands a serious outbound pipeline.`,
        `Cadence drafts personalised emails to every lead in Kazakh, Russian, or English, sends them via Gmail, and tracks replies automatically.`,
        `Teams in KZ are reclaiming 4 hours a day. Show you a 12-min demo?`,
        `— Dinara, Cadence`
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
