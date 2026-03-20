/* eslint-disable @next/next/no-img-element */
import './page.css'

const siteLogo = 'https://framerusercontent.com/images/wXnyZRIxNTskCYfZxaUW8sl0bo.svg'

const navItems = [
  { label: 'About', href: '/about' },
  { label: 'Blog', href: '/blog' },
  { label: 'Changelog', href: '/changelog' },
  { label: 'Contact', href: '/contact' },
  { label: 'Power-Ups', href: '/power-ups' },
]

const clientLogos = [
  'https://framerusercontent.com/images/d4hg31biMljU4aH2RDnh6wWqDfM.svg?width=87&height=24',
  'https://framerusercontent.com/images/LBtvbbMscujp7wOLmEoI7hneo.svg?width=103&height=45',
  'https://framerusercontent.com/images/bbXsJC7bsFfQZR7qsy0AXJDR2c.svg?width=150&height=37',
  'https://framerusercontent.com/images/IUvmt1THxXd3PXbz5CaMuhEuI6Q.svg?width=130&height=27',
  'https://framerusercontent.com/images/Jxv0OqRRv25KUWBoDu2ZlmiSAE.svg?width=149&height=37',
  'https://framerusercontent.com/images/8Cv9xasPycS59rovKfmcfBFsiZo.svg?width=111&height=37',
  'https://framerusercontent.com/images/7aIzRlMAo7aKEM8u0k2IGflPk0.svg?width=137&height=31',
]

const heroAssets = {
  canvas:
    'https://framerusercontent.com/images/lMSZKDPhVBBllLKnGtf5WALEkoU.png?scale-down-to=1024&width=1600&height=995',
  badgeLeft: 'https://framerusercontent.com/images/4FKumHemzcAc3N8KKCHn8yZrRAg.svg?width=111&height=66',
  badgeRight: 'https://framerusercontent.com/images/5zrSIP9NSKIsNbxQIW5WP5VvpXk.svg?width=187&height=58',
  sideCard:
    'https://framerusercontent.com/images/3ZbX0pAmwG1pNcXk5oRa5jN1I.png?scale-down-to=1024&width=800&height=1103',
}

const toolkitCards = [
  {
    title: 'Intuitive drag & drop editor',
    text: 'Create stunning designs effortlessly with a user-friendly interface.',
    tone: 'coral',
    image:
      'https://framerusercontent.com/images/YXLdqRrdQ3LpA0PPNhtbF5Rfsk.png?scale-down-to=512&width=700&height=553',
    overlay: 'https://framerusercontent.com/images/mJj3LBZOetQro23RQplCUhtc4.jpg?width=400&height=174',
  },
  {
    title: 'Advanced prototyping',
    text: 'Turn ideas into interactive prototypes without writing a single line of code.',
    tone: 'gold',
    image: 'https://framerusercontent.com/images/dkGE24Md1SbG1Y2bJVQBdWl1dns.png?scale-down-to=512',
  },
  {
    title: 'Real-time collaboration',
    text: 'Work seamlessly with your team, get instant feedback.',
    tone: 'violet',
    image:
      'https://framerusercontent.com/images/eAT8ehYRmt3nfNGdw82E5OhWPlQ.png?scale-down-to=512&width=700&height=558',
    avatars: [
      'https://framerusercontent.com/images/uHdnVRTHm13no6nk3Ipm2HuVs.jpg?scale-down-to=512&width=600&height=600',
      'https://framerusercontent.com/images/1d3VmmKfMjOwv8Gx0fb354Y80Q.jpg?scale-down-to=512&width=600&height=600',
      'https://framerusercontent.com/images/sYlCdwHA9SQgqMmPglnHbNYKMtc.jpg?scale-down-to=512&width=600&height=600',
      'https://framerusercontent.com/images/aUU2oWZTnGJSkZucLFR8TjVH50.jpg?scale-down-to=512&width=600&height=600',
      'https://framerusercontent.com/images/UQK9nK25dDlqFXJ6Cb5LrZik.jpg?scale-down-to=512&width=600&height=600',
    ],
  },
]

const workflowSteps = [
  {
    number: '01',
    title: 'Start your project',
    text: 'Create a new design or import files with just a click. Set up your workspace effortlessly.',
  },
  {
    number: '02',
    title: 'Design with ease',
    text: 'Use our intuitive drag-and-drop editor and smart tools to create stunning designs.',
  },
  {
    number: '03',
    title: 'Export & Share',
    text: 'Easily integrate with your favorite tools to launch your project effortlessly.',
  },
]

const workflowAssets = {
  image: 'https://framerusercontent.com/images/ilnxb8JlQSPXcjRWoZTNLGSFBk.png?width=1071&height=920',
  badge: 'https://framerusercontent.com/images/LOD2H8PN4DInLuNxPHDPjskPc8.svg?width=67&height=51',
  windows: 'https://framerusercontent.com/images/uU2Zp13wFQUv9qyoOmfMWoDCR8.svg?width=20&height=20',
  apple: 'https://framerusercontent.com/images/sHQWKBlcdxgoBk75IhH8eY9bWVY.svg?width=20&height=20',
}

const integrationIcons = [
  'https://framerusercontent.com/images/VBINO0uPEBBtdnw2H556ai5y8.svg?width=65&height=63',
  'https://framerusercontent.com/images/ammBtYeCqDQpQX01AIdTTAJIX0s.svg?width=63&height=63',
  'https://framerusercontent.com/images/ev7o2fuywuHbshQIcSZ4Gj0vJs8.svg?width=64&height=63',
  'https://framerusercontent.com/images/RdY39UphF55oveWjwUW7nUVG0A.svg?width=63&height=63',
  'https://framerusercontent.com/images/qOnYNwclE4tZchSq2SGRZNe99A.svg?width=64&height=63',
  'https://framerusercontent.com/images/tApNdViJOVngDYaNMdpLNMWrE.svg?width=64&height=63',
  'https://framerusercontent.com/images/G2Zgz5YhqI9hCVQM2ZbkVjTyDc.svg?width=62&height=64',
  'https://framerusercontent.com/images/DbetTKBspAjyP9DPnteU3FLeaHQ.svg?width=64&height=64',
  'https://framerusercontent.com/images/J9T0namOEUFiwlJTW6EUHNumrCc.svg?width=64&height=64',
  'https://framerusercontent.com/images/0JqVCpsaxPlWJzUpjsMFieQYsg.svg?width=63&height=64',
]

const integrationsQuote = {
  logo: 'https://framerusercontent.com/images/zihHvrScDvGkIjPol8V3xIlAkkE.svg?width=100&height=100',
  portrait:
    'https://framerusercontent.com/images/UQK9nK25dDlqFXJ6Cb5LrZik.jpg?scale-down-to=512&width=600&height=600',
  name: 'Daniel Vaughn, Founder & CEO',
  text:
    'Our platform empowers teams to collaborate, innovate, and bring ideas to life - seamlessly and effortlessly.',
}

const featureShowcase = [
  {
    title: 'Cloud-based accessibility',
    text: 'Access your projects anytime, anywhere - no downloads or installations needed.',
    art: 'https://framerusercontent.com/images/dBBfzjGk2BtPPKjZRobmTlVSq4.svg?width=185&height=180',
    badgeA: 'https://framerusercontent.com/images/XGMkz3M7PyreZHbjACC1UUPQ8kI.svg?width=81&height=27',
    badgeB: 'https://framerusercontent.com/images/qG2dE3ZbHhYfw3Pjmvyqfe04O4.svg?width=70&height=28',
  },
  {
    title: 'Fast & secure performance',
    text: 'Experience lightning-fast speed with enterprise-level security and version control.',
    art: 'https://framerusercontent.com/images/6W02ncJAwEXl60GOBTttPIPb8.svg?width=110&height=170',
    artSecondary: 'https://framerusercontent.com/images/O3HEesRvxGJ99Z7m4PLbc2EatvI.svg?width=161&height=170',
    arrow: 'https://framerusercontent.com/images/IJhNKqkhnxkAILhlDMIrAWS7k.svg?width=47&height=80',
  },
]

const featureList = [
  {
    title: 'Effortless design experience',
    text: 'Intuitive interface and smart tools to speed up your creative process.',
    icon: 'https://framerusercontent.com/images/l42PBTIUav2V302HEVgYzlS5jJU.svg?width=22&height=22',
  },
  {
    title: 'Hassle-free prototyping',
    text: 'Transform static designs into interactive prototypes in just a few clicks.',
    icon: 'https://framerusercontent.com/images/sy5ROC9x6CLiXyLV5LpuEUJheo.svg?width=22&height=22',
  },
  {
    title: 'One-click export & handoff',
    text: 'Generate code, export assets, and collaborate with developers effortlessly.',
    icon: 'https://framerusercontent.com/images/MX5HZSkOdkquLFzfFSVVE1ZmlJw.svg?width=22&height=22',
  },
]

const testimonial = {
  avatars: [
    {
      name: 'Emily Ray',
      src: 'https://framerusercontent.com/images/rCI59ZX0ZR56eQvkNscJuMxvaKE.jpg',
    },
    {
      name: 'Sofia Delgado',
      src: 'https://framerusercontent.com/images/mk21gOTOdvfX5KnyLebdCmKJ62c.jpg',
    },
    {
      name: 'Ryan Chen',
      src: 'https://framerusercontent.com/images/dujzU5kSm2vU1NuhwLmE5qacAt8.jpg',
    },
    {
      name: 'Jessica Moore',
      src: 'https://framerusercontent.com/images/qGUi2X5PZI5zMmaPEt895svrgN8.jpg',
    },
    {
      name: 'Alex Romero',
      src: 'https://framerusercontent.com/images/Ky2gFmrngrPCGRkq3vmMLs9NGbg.jpg',
    },
  ],
  quote:
    'This tool has completely transformed how our team collaborates. The real-time editing and seamless integrations make our process so much smoother!',
  author: 'Emily Ray, UX Designer',
}

const plans = [
  {
    name: 'Starter plan',
    price: '$19',
    blurb: 'For individuals & new creators',
    cta: 'Get Started',
    featured: false,
    perks: [
      '1 active project',
      'Basic collaboration tools',
      'Limited prototyping options',
      '500MB cloud storage',
      'Seamless third-party integrations',
      'Community support',
    ],
  },
  {
    name: 'Pro plan',
    price: '$49',
    blurb: 'For freelancers & small teams',
    cta: 'Get Started',
    featured: true,
    perks: [
      'Unlimited projects',
      'Real-time collaboration',
      'Advanced prototyping tools',
      'Cloud storage & version history',
      'Seamless third-party integrations',
      'Email & chat support',
    ],
  },
  {
    name: 'Business plan',
    price: '$79',
    blurb: 'For growing teams & agencies',
    cta: 'Get Started',
    featured: false,
    perks: [
      'Everything in Pro +',
      'Team management & permissions',
      'Enhanced security controls',
      'Priority integrations & API access',
      'Advanced cloud storage',
      '24/7 priority support',
    ],
  },
]

const workflowAudience = [
  'UI/UX designers',
  'App & Web developers',
  'Product teams',
  'Marketing teams',
  'Enterprise organizations',
  'Agencies & enterprises',
]

const showcaseAssets = {
  app: 'https://framerusercontent.com/images/d7m2VScguJ8Bzi0pVEKE6QiFs.png?width=601&height=914',
  appBadge: 'https://framerusercontent.com/images/Hlq968SBkAIwQwdlJBE8jTLn4c.png?width=363&height=290',
  dashboard: 'https://framerusercontent.com/images/3uvceqytCHwJDIfhFyK75EuwCys.png?width=3840&height=2223',
  dashboardBadge: 'https://framerusercontent.com/images/5ljK1L58NiwFSbuW5ci6fdKI2s.svg?width=87&height=59',
}

const socialLinks = [
  {
    label: 'Facebook',
    href: 'https://www.facebook.com/',
    icon: 'https://framerusercontent.com/images/v5LDZ0ytEz6mMBdXdcs0AIPvYw.svg?width=18&height=18',
  },
  {
    label: 'X',
    href: 'https://www.x.com/',
    icon: 'https://framerusercontent.com/images/cGnXMN3RHYvM6awzQQEhr0nFVbA.svg?width=18&height=18',
  },
  {
    label: 'Instagram',
    href: 'https://www.instagram.com/',
    icon: 'https://framerusercontent.com/images/9LrqKZZPndecNYvQTOdNog1zs.svg?width=18&height=18',
  },
  {
    label: 'LinkedIn',
    href: 'https://www.linkedin.com/',
    icon: 'https://framerusercontent.com/images/PvLJXmFfH3Z2nEa6tJncH8MbEk.svg?width=24&height=18',
  },
  {
    label: 'YouTube',
    href: 'https://www.youtube.com/',
    icon: 'https://framerusercontent.com/images/JCDk8i61Ec1N2laCFRxqdUPv0sM.svg?width=21&height=21',
  },
]

const footerColumns = [
  {
    title: 'Quick Links',
    items: [
      { label: 'Home', href: '#hero' },
      { label: 'Features', href: '#feature' },
      { label: 'Pricing', href: '#pricing' },
      { label: 'Download', href: '#cta' },
    ],
  },
  {
    title: 'All Pages',
    items: [
      { label: 'Power-Ups', href: '/power-ups' },
      { label: 'About us', href: '/about' },
      { label: 'Contact us', href: '/contact' },
      { label: 'Blog', href: '/blog' },
      { label: 'Waitlist', href: '/waitlist' },
      { label: 'Changelog', href: '/changelog' },
      { label: 'Privacy Policy', href: '/legal-pages/privacy-policy' },
      { label: '404', href: '/404' },
    ],
  },
]

function App() {
  return (
    <div className="page-shell">
      <header className="site-header" data-reveal data-reveal-delay="40ms" data-reveal-y="12px">
        <a className="brand brand--image" href="#hero" aria-label="Draftr home">
          <img src={siteLogo} alt="Draftr" />
        </a>

        <nav className="site-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <a key={item.label} href={item.href} className="site-nav__link">
              {item.label}
            </a>
          ))}
        </nav>

        <a className="ghost-button" href="/contact">
          Login now
        </a>
      </header>

      <main>
        <section className="hero-section" id="hero">
          <div className="hero-section__glow hero-section__glow--left"></div>
          <div className="hero-section__glow hero-section__glow--right"></div>

          <div className="hero-copy" data-reveal data-reveal-delay="80ms">
            <div className="announce-pill">
              <span className="announce-pill__tag">New</span>
              <span>Revolutionize your design workflow</span>
            </div>

            <h1>Bring ideas to life in just a few clicks.</h1>

            <p className="hero-copy__lede">
              Design, prototype, and collaborate in real-time - all in one powerful
              platform. Elevate your creative process with seamless teamwork and
              limitless possibilities.
            </p>

            <div className="hero-actions">
              <a className="primary-button" href="/contact">
                Get Started • it&apos;s free <ArrowUpRightIcon />
              </a>
            </div>
          </div>

          <div className="hero-visuals" aria-hidden="true">
            <div className="hero-canvas" data-reveal data-reveal-delay="150ms" data-reveal-scale="0.985">
              <img
                className="hero-canvas__hero-image"
                src={heroAssets.canvas}
                alt="Draftr editor preview"
              />
              <img className="hero-canvas__badge hero-canvas__badge--left" src={heroAssets.badgeLeft} alt="" />
              <img className="hero-canvas__badge hero-canvas__badge--right" src={heroAssets.badgeRight} alt="" />
            </div>

            <div className="hero-sidecard" data-reveal data-reveal-delay="250ms" data-reveal-x="18px">
              <img className="hero-sidecard__image" src={heroAssets.sideCard} alt="Draftr card preview" />
            </div>
          </div>

          <div className="client-marquee" aria-label="Trusted by creative teams" data-reveal data-reveal-delay="310ms" data-reveal-y="10px">
            <div className="client-marquee__track">
              {[...clientLogos, ...clientLogos].map((logo, index) => (
                <img key={`${logo}-${index}`} src={logo} alt="" loading="lazy" />
              ))}
            </div>
          </div>
        </section>

        <section className="section intro-section" id="about">
          <div data-reveal>
            <SectionEyebrow>Toolkit</SectionEyebrow>
            <h2>The ultimate toolkit for designers &amp; teams</h2>
            <p className="section-copy">
              Everything you need to create, prototype, and collaborate - all in a
              single, easy-to-use platform.
            </p>
          </div>

          <div className="toolkit-grid">
            {toolkitCards.map((card, index) => (
              <article
                className={`toolkit-card toolkit-card--${card.tone}`}
                key={card.title}
                data-reveal
                data-reveal-delay={`${120 + index * 100}ms`}
                style={{ ['--card-delay' as string]: `${index * 140}ms` }}
              >
                <div className="toolkit-card__art">
                  <img className="toolkit-card__image" src={card.image} alt="" loading="lazy" />
                  {card.overlay ? (
                    <img className="toolkit-card__overlay" src={card.overlay} alt="" loading="lazy" />
                  ) : null}
                  {card.avatars ? (
                    <div className="toolkit-card__avatars">
                      {card.avatars.map((avatar) => (
                        <img key={avatar} src={avatar} alt="" loading="lazy" />
                      ))}
                    </div>
                  ) : null}
                </div>
                <h3>{card.title}</h3>
                <p>{card.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section workflow-section" id="blog">
          <div className="workflow-copy" data-reveal>
            <SectionEyebrow>Workflow</SectionEyebrow>
            <h2>Simplify your workflow</h2>
            <p className="section-copy section-copy--left">
              A clean three-step flow for turning ideas into polished output with
              less friction and better handoff.
            </p>

            <div className="workflow-steps">
              {workflowSteps.map((step, index) => (
                <article
                  className="workflow-step"
                  key={step.number}
                  data-reveal
                  data-reveal-delay={`${100 + index * 90}ms`}
                >
                  <span className="workflow-step__number">{step.number}</span>
                  <div>
                    <h3>{step.title}</h3>
                    <p>{step.text}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="workflow-preview" aria-hidden="true" data-reveal data-reveal-delay="140ms" data-reveal-x="20px">
            <div className="workflow-preview__panel">
              <img className="workflow-preview__image" src={workflowAssets.image} alt="" loading="lazy" />
              <img className="workflow-preview__badge" src={workflowAssets.badge} alt="" loading="lazy" />

              <div className="workflow-preview__platforms">
                <span>Available on Windows &amp; Mac</span>
                <div className="workflow-preview__platform-icons">
                  <img src={workflowAssets.windows} alt="" loading="lazy" />
                  <img src={workflowAssets.apple} alt="" loading="lazy" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section integrations-section" id="waitlist">
          <div className="integrations-cloud" aria-hidden="true" data-reveal data-reveal-scale="0.985">
            <div className="integrations-cloud__surface">
              {integrationIcons.map((icon, index) => (
                <div
                  className={`integration-chip integration-chip--${index + 1}`}
                  key={icon}
                  style={{ ['--delay' as string]: `${index * 110}ms` }}
                >
                  <img src={icon} alt="" loading="lazy" />
                </div>
              ))}

              <div className="integrations-cloud__hub">
                <img src={integrationsQuote.logo} alt="" loading="lazy" />
              </div>
            </div>
          </div>

          <div className="integrations-copy" data-reveal data-reveal-delay="130ms" data-reveal-x="18px">
            <SectionEyebrow>Integrations</SectionEyebrow>
            <h2>One platform, unlimited integrations</h2>
            <p className="section-copy section-copy--left">
              Connect your favorite tools and keep your creative pipeline moving
              from idea to delivery without losing momentum.
            </p>
            <a className="text-link" href="/power-ups">
              View all integrations
            </a>

            <article className="quote-card">
              <p>&quot;{integrationsQuote.text}&quot;</p>
              <div className="quote-card__author">
                <img src={integrationsQuote.portrait} alt="Daniel Vaughn" loading="lazy" />
                <span>{integrationsQuote.name}</span>
              </div>
            </article>
          </div>
        </section>

        <section className="section feature-panel" id="power-ups">
          <span className="section-anchor" id="feature"></span>
          <div data-reveal>
            <SectionEyebrow>Features</SectionEyebrow>
            <h2>Power up your workflow with next-gen features</h2>
          </div>

          <div className="feature-panel__layout">
            {featureShowcase.map((card, index) => (
              <article
                className="feature-card feature-card--large"
                key={card.title}
                data-reveal
                data-reveal-delay={`${120 + index * 110}ms`}
              >
                <div className={`feature-card__art feature-card__art--${index + 1}`}>
                  <img className="feature-card__art-main" src={card.art} alt="" loading="lazy" />
                  {card.badgeA ? <img className="feature-card__badge feature-card__badge--a" src={card.badgeA} alt="" loading="lazy" /> : null}
                  {card.badgeB ? <img className="feature-card__badge feature-card__badge--b" src={card.badgeB} alt="" loading="lazy" /> : null}
                  {card.artSecondary ? (
                    <>
                      <img
                        className="feature-card__art-secondary"
                        src={card.artSecondary}
                        alt=""
                        loading="lazy"
                      />
                      <div className="feature-card__arrows">
                        <img src={card.arrow} alt="" loading="lazy" />
                        <img src={card.arrow} alt="" loading="lazy" />
                        <img src={card.arrow} alt="" loading="lazy" />
                      </div>
                    </>
                  ) : null}
                </div>
                <h3>{card.title}</h3>
                <p>{card.text}</p>
              </article>
            ))}

            <div className="feature-card feature-card--stack" data-reveal data-reveal-delay="300ms">
              {featureList.map((item) => (
                <article className="feature-list-item" key={item.title}>
                  <div className="feature-list-item__icon">
                    <img src={item.icon} alt="" loading="lazy" />
                  </div>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section proof-section" id="changelog">
          <div className="proof-copy" data-reveal>
            <SectionEyebrow>Testimonials</SectionEyebrow>
            <h2>Loved by designers &amp; teams</h2>
            <p className="section-copy section-copy--left">
              Trusted by modern teams that need cleaner review cycles, stronger
              collaboration, and faster creative delivery.
            </p>
          </div>

          <article className="proof-quote" data-reveal data-reveal-delay="140ms" data-reveal-x="18px">
            <div className="avatar-cluster" aria-hidden="true">
              {testimonial.avatars.map((avatar) => (
                <img key={avatar.name} src={avatar.src} alt="" loading="lazy" />
              ))}
            </div>
            <p>&quot;{testimonial.quote}&quot;</p>
            <span className="proof-quote__author">{testimonial.author}</span>
          </article>
        </section>

        <section className="section pricing-section" id="pricing">
          <div data-reveal>
            <SectionEyebrow>Pricing</SectionEyebrow>
            <h2>Flexible pricing plans</h2>
            <p className="section-copy">
              Choose a plan that grows with you. Start for free and upgrade anytime
              for more features and support.
            </p>
          </div>

          <div className="billing-toggle" aria-label="Billing cadence" data-reveal data-reveal-delay="100ms" data-reveal-y="12px">
            <span className="billing-toggle__option billing-toggle__option--active">Monthly</span>
            <span className="billing-toggle__option">Yearly 20% off</span>
          </div>

          <div className="pricing-grid">
            {plans.map((plan, index) => (
              <article
                className={`pricing-card${plan.featured ? ' pricing-card--featured' : ''}`}
                key={plan.name}
                data-reveal
                data-reveal-delay={`${160 + index * 100}ms`}
              >
                <div className="pricing-card__header">
                  <div>
                    <p className="pricing-card__name">{plan.name}</p>
                    <p className="pricing-card__blurb">{plan.blurb}</p>
                  </div>

                  <div className="pricing-card__price">
                    <span>{plan.price}</span>
                    <small>/month</small>
                  </div>
                </div>

                <a className={plan.featured ? 'primary-button' : 'secondary-button'} href="/contact">
                  {plan.cta}
                </a>

                <div className="pricing-card__meta">Included features:</div>

                <ul className="pricing-card__perks">
                  {plan.perks.map((perk) => (
                    <li key={perk}>
                      <CheckIcon />
                      <span>{perk}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section className="section split-showcase">
          <div className="split-showcase__visual" aria-hidden="true" data-reveal>
            <div className="showcase-card">
              <img className="showcase-card__image" src={showcaseAssets.app} alt="" loading="lazy" />
              <img className="showcase-card__badge" src={showcaseAssets.appBadge} alt="" loading="lazy" />
            </div>
          </div>

          <div className="split-showcase__copy" data-reveal data-reveal-delay="130ms" data-reveal-x="18px">
            <SectionEyebrow>Solutions</SectionEyebrow>
            <h2>The perfect design solution for every workflow</h2>
            <p className="section-copy section-copy--left">
              Discover how our design platform fits your needs, whether you&apos;re a
              freelancer, startup, or enterprise.
            </p>

            <div className="audience-grid">
              {workflowAudience.map((item) => (
                <article className="audience-card" key={item}>
                  <span className="audience-card__dot"></span>
                  <span>{item}</span>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section cta-section" id="contact">
          <span className="section-anchor" id="cta"></span>
          <div data-reveal>
            <SectionEyebrow>Creative flow</SectionEyebrow>
            <h2>Take your creative workflow to the next level</h2>
            <p className="section-copy">
              Supercharge your workflow with powerful design tools and effortless
              collaboration - perfect for freelancers and teams.
            </p>
          </div>

          <div className="hero-actions hero-actions--center" data-reveal data-reveal-delay="110ms" data-reveal-y="12px">
            <a className="primary-button" href="#pricing">
              Get Started
            </a>
            <a className="icon-button icon-button--platform" href="https://www.microsoft.com/" rel="noreferrer" target="_blank">
              <img src={workflowAssets.windows} alt="Windows" />
            </a>
            <a className="icon-button icon-button--platform" href="https://www.apple.com/" rel="noreferrer" target="_blank">
              <img src={workflowAssets.apple} alt="Apple" />
            </a>
          </div>

          <div className="cta-showcase" aria-hidden="true" data-reveal data-reveal-delay="180ms" data-reveal-scale="0.99">
            <div className="cta-showcase__screen">
              <img className="cta-showcase__image" src={showcaseAssets.dashboard} alt="" loading="lazy" />
              <img
                className="cta-showcase__badge"
                src={showcaseAssets.dashboardBadge}
                alt=""
                loading="lazy"
              />
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer" data-reveal data-reveal-delay="80ms" data-reveal-y="18px">
        <div className="site-footer__brand">
          <a className="brand brand--image brand--footer" href="#hero" aria-label="Draftr home">
            <img src={siteLogo} alt="Draftr" />
          </a>
          <div className="site-footer__follow">
            <p>Follow us on:</p>
            <div className="site-footer__socials" aria-label="Social links">
              {socialLinks.map((link) => (
                <a key={link.label} href={link.href} rel="noreferrer" target="_blank" aria-label={link.label}>
                  <img src={link.icon} alt="" loading="lazy" />
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="site-footer__links">
          {footerColumns.map((column) => (
            <div key={column.title}>
              <h3>{column.title}</h3>
              <ul>
                {column.items.map((item) => (
                  <li key={item.label}>
                    <a href={item.href}>{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </footer>
    </div>
  )
}

function SectionEyebrow({ children }: { children: string }) {
  return <p className="section-eyebrow">{children}</p>
}

function ArrowUpRightIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20">
      <path
        d="M6 14 14 6M8 6h6v6"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20">
      <path
        d="m4.5 10.5 3.5 3.5 7.5-8"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}

export default App
