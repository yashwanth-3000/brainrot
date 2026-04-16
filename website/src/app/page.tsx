/* eslint-disable @next/next/no-img-element */
import './page.css'
import Navbar from '@/components/ui/navbar'
import HomeHeroVideo from './home-hero-video'

const stats = [
  { value: '3 min', label: 'avg. video generated' },
  { value: '10×', label: 'faster than reading' },
  { value: '2 modes', label: 'guest or personal library' },
]

const features = [
  {
    tag: 'Drop a URL',
    headline: 'Any blog, article, or paper. Instant video.',
    body: 'Paste a link to any webpage, whether it is a research paper, a Medium post, or a news article. Draftr scrapes it, extracts the knowledge, and turns it into a brainrot-format short your brain devours in minutes.',
    accent: '#5235ef',
    icon: '🔗',
  },
  {
    tag: 'Upload your notes',
    headline: 'PDFs and docs, reimagined as content.',
    body: 'Your textbooks, lecture slides, and study guides can be uploaded and turned into scroll-stopping short-form video. Studying has never felt this illegal.',
    accent: '#7c3aed',
    icon: '📄',
  },
  {
    tag: 'Raw content',
    headline: 'Paste anything. Get a video back.',
    body: 'No file? No problem. Paste your raw notes, a chapter summary, a job description, or a recipe. Draftr shapes it into the exact format your brain already knows how to binge.',
    accent: '#6d28d9',
    icon: '✍️',
  },
]

const steps = [
  {
    n: '01',
    title: 'Start as guest or sign in',
    body: 'Use guest mode if you want to try it fast, or sign in with Google so every generation lands in your own private library instead of the shared one.',
  },
  {
    n: '02',
    title: 'CrewAI plans the coverage',
    body: 'Draftr ingests the source, splits it into sections, and lets CrewAI plan which parts deserve their own short before OpenAI writes each slot.',
  },
  {
    n: '03',
    title: 'Your library fills itself',
    body: 'Narration, subtitles, gameplay, and rendering all run automatically. Guests feed the general library, while signed-in users build a personal archive of every short.',
  },
]

const comparisons = [
  {
    bad: 'Subway Surfers + some guy reading r/AskReddit',
    good: 'Subway Surfers + your biochemistry exam notes',
  },
  {
    bad: 'Minecraft parkour + random life hacks you\'ll forget',
    good: 'Minecraft parkour + that research paper due Friday',
  },
  {
    bad: 'Satisfying clips + celebrity drama',
    good: 'Satisfying clips + the blog you saved 3 months ago',
  },
]

export default function HomePage() {
  return (
    <div className="hp">
      <Navbar />

      {/* ── Hero ── */}
      <section className="hp-hero">
        <div className="hp-hero__copy">
          <h1 className="hp-h1">
            Your feed is making
            <br />you dumber.<br />
            <em>We fixed that.</em>
          </h1>

          <p className="hp-lede">
            You&apos;re already watching hours of gameplay clips with text over them.
            What if that content was <strong>your study notes? Your bookmarked articles?
            That paper you keep putting off?</strong> Draftr converts any content into short-form brainrot videos
            your brain actually learns from. Try it instantly in guest mode, then sign in with Google when you want
            your own library and saved generation history.
          </p>

          <div className="hp-actions">
            <a className="hp-btn hp-btn--primary" href="/chat">
              Generate your first video <ArrowRight />
            </a>
            <a className="hp-btn hp-btn--ghost" href="/about">
              See how it works
            </a>
          </div>

          <div className="hp-stats">
            {stats.map(s => (
              <div key={s.label} className="hp-stat">
                <span className="hp-stat__value">{s.value}</span>
                <span className="hp-stat__label">{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Phone mockup - brainrot video preview */}
        <div className="hp-hero__visual" aria-hidden="true">
          <div className="hp-phone-wrap">
            <div className="hp-phone">
              <div className="hp-phone__island" />
              <div className="hp-phone__screen">
                <HomeHeroVideo />
              </div>
              <div className="hp-phone__btn hp-phone__btn--vol-up" />
              <div className="hp-phone__btn hp-phone__btn--vol-down" />
              <div className="hp-phone__btn hp-phone__btn--power" />
            </div>

          </div>
        </div>
      </section>

      {/* ── Comparison strip ── */}
      <section className="hp-compare">
        <p className="hp-eyebrow hp-eyebrow--center">What actually changes</p>
        <h2 className="hp-h2 hp-h2--center">Same format. Completely different outcome.</h2>
        <div className="hp-compare__grid">
          {comparisons.map((c, i) => (
            <div key={i} className="hp-compare__row">
              <div className="hp-compare__cell hp-compare__cell--bad">
                <span className="hp-compare__icon">✕</span>
                <span>{c.bad}</span>
              </div>
              <div className="hp-compare__arrow">→</div>
              <div className="hp-compare__cell hp-compare__cell--good">
                <span className="hp-compare__icon">✓</span>
                <span>{c.good}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="hp-features" id="features">
        <div className="hp-section-head">
          <p className="hp-eyebrow">How you feed it</p>
          <h2 className="hp-h2">Three ways to turn your content into brainrot.</h2>
          <p className="hp-sub hp-sub--center">
            URL, file, or raw paste. Whatever format your knowledge lives in, Draftr eats it.
          </p>
        </div>

        <div className="hp-features__grid">
          {features.map((f) => (
            <article
              className="hp-feat-card"
              key={f.tag}
              style={{ '--card-accent': f.accent } as React.CSSProperties}
            >
              <div className="hp-feat-card__icon">{f.icon}</div>
              <span className="hp-feat-card__tag">{f.tag}</span>
              <h3 className="hp-feat-card__headline">{f.headline}</h3>
              <p className="hp-feat-card__body">{f.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="hp-how" id="how">
        <div className="hp-how__copy">
          <p className="hp-eyebrow">How it works</p>
          <h2 className="hp-h2">Drop it. Draftr does the rest.</h2>
          <p className="hp-sub">
            No editing software. No script writing. No production skills.
            Just your content and two minutes.
          </p>

          <div className="hp-steps">
            {steps.map((s) => (
              <div className="hp-step" key={s.n}>
                <span className="hp-step__n">{s.n}</span>
                <div>
                  <h3 className="hp-step__title">{s.title}</h3>
                  <p className="hp-step__body">{s.body}</p>
                </div>
              </div>
            ))}
          </div>

          <a className="hp-btn hp-btn--primary" href="/chat">
            Make your first video <ArrowRight />
          </a>
        </div>

        <div className="hp-how__visual" aria-hidden="true">
          <div className="hp-phone hp-phone--sm">
            <div className="hp-phone__island" />
            <div className="hp-phone__screen">
              <div className="hp-mock">
                <div className="hp-mock__header">
                  <span className="hp-mock__logo">Draftr</span>
                  <span className="hp-mock__badge">AI</span>
                </div>
                <div className="hp-mock__messages">
                  <div className="hp-mock__mode-row">
                    <span className="hp-mock__mode hp-mock__mode--active">URL</span>
                    <span className="hp-mock__mode">Upload</span>
                    <span className="hp-mock__mode">Paste</span>
                  </div>
                  <div className="hp-mock__msg hp-mock__msg--user">
                    Turn this into a brainrot video →<br />
                    <span style={{fontSize: '10px', opacity: 0.7}}>pubmed.ncbi.nlm.nih.gov/...</span>
                  </div>
                  <div className="hp-mock__msg hp-mock__msg--ai">
                    <span className="hp-mock__ai-avatar" />
                    <div className="hp-mock__ai-text">
                      Reading the paper… extracting 7 key findings. Generating your video now 🎮
                    </div>
                  </div>
                  <div className="hp-mock__thinking">
                    <span className="hp-mock__thinking-dot" />
                    Rendering with gameplay overlay…
                  </div>
                </div>
                <div className="hp-mock__input">
                  <span>Paste a URL or describe your content…</span>
                </div>
              </div>
            </div>
            <div className="hp-phone__btn hp-phone__btn--vol-up" />
            <div className="hp-phone__btn hp-phone__btn--vol-down" />
            <div className="hp-phone__btn hp-phone__btn--power" />
          </div>
        </div>
      </section>

    </div>
  )
}

function ArrowRight() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" width="15" height="15" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <path d="M4 10h12M11 5l5 5-5 5" />
    </svg>
  )
}
