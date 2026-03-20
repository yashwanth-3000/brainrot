/* eslint-disable @next/next/no-img-element */
import { Banner, MarketingShell, PageSection, SectionHeader, marketingPageStyles as styles } from '../_components/marketing-shell'

const clientLogos = [
  'https://framerusercontent.com/images/d4hg31biMljU4aH2RDnh6wWqDfM.svg?width=87&height=24',
  'https://framerusercontent.com/images/YYV5QoPK9M9NhyUxptVvm0o7WFM.svg',
  'https://framerusercontent.com/images/LBtvbbMscujp7wOLmEoI7hneo.svg?width=103&height=45',
  'https://framerusercontent.com/images/bbXsJC7bsFfQZR7qsy0AXJDR2c.svg?width=150&height=37',
  'https://framerusercontent.com/images/IUvmt1THxXd3PXbz5CaMuhEuI6Q.svg?width=130&height=27',
  'https://framerusercontent.com/images/Jxv0OqRRv25KUWBoDu2ZlmiSAE.svg?width=149&height=37',
  'https://framerusercontent.com/images/8Cv9xasPycS59rovKfmcfBFsiZo.svg?width=111&height=37',
  'https://framerusercontent.com/images/7aIzRlMAo7aKEM8u0k2IGflPk0.svg?width=137&height=31',
]

const team = [
  { name: 'Jane Lin', role: 'Co-Founder', bio: 'Shapes product direction and keeps the platform grounded in real team workflows.' },
  { name: 'Sofia Mendes', role: 'Design Lead', bio: 'Turns complexity into clear systems that feel expressive without becoming heavy.' },
  { name: 'Liam Chen', role: 'Product Engineer', bio: 'Focuses on speed, structure, and the details that make collaboration feel effortless.' },
  { name: 'Ethan Ross', role: 'Creative Strategist', bio: 'Bridges product story and brand expression so the experience stays coherent end to end.' },
]

export default function AboutPage() {
  return (
    <MarketingShell
      eyebrow="About"
      title="Design isn’t just what we do — it’s how we think."
      description="At Draftr, we’re building the next generation of design tools: simple, collaborative, and lightning fast. Our goal is to help teams move from idea to execution without friction."
    >
      <PageSection>
        <div className={styles.aboutHeroMedia}>
          <img
            src="https://framerusercontent.com/images/wS6rtfG8W5jA7CMDfuRpk25jAvc.jpg?width=1400&height=700"
            alt="Draftr team collaborating"
          />
          <img
            className={styles.heroPanelBadgeWide}
            src="https://framerusercontent.com/images/mXjFmud2eKYX0WdABUIFXgqS5G8.png?scale-down-to=512&width=642&height=130"
            alt=""
          />
          <div className={styles.heroPanelGlow}>
            <img
              src="https://framerusercontent.com/images/OYulHZgDcWdqRuNrBwBW0oT8.png?scale-down-to=512&width=900&height=898"
              alt=""
            />
          </div>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="From Idea to Impact"
          intro="At Draftr, we’re building the next generation of design tools — simple, collaborative, and lightning fast. Our mission is to empower teams to move from idea to execution without friction."
        />

        <div className={styles.aboutCopy}>
          <p className={styles.proseLead}>
            Design is no longer just about aesthetics. It&apos;s about speed, clarity, and
            collaboration. At Draftr, we&apos;re redefining how design happens in modern teams.
            We believe that anyone with an idea should be able to bring it to life without
            getting lost in complexity.
          </p>
          <p className={styles.smallText}>
            Born out of frustration with bloated, rigid design tools, Draftr was created to
            give creators a smarter, simpler way to design. Whether you&apos;re building an
            interface, presenting an idea, or refining a brand concept, Draftr is the place
            where clarity meets creativity.
          </p>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="Why we exist"
          intro="Design is no longer just about aesthetics. It is about speed, clarity, and collaboration. These principles shape every part of the product."
        />

        <ul className={styles.statementGrid}>
          <li className={styles.statementItem}>
            <span className={styles.statementDot}></span>
            <span>Design is too complicated. We strip away unnecessary complexity.</span>
          </li>
          <li className={styles.statementItem}>
            <span className={styles.statementDot}></span>
            <span>Workflow is too fragmented. We combine the essential tools into one experience.</span>
          </li>
          <li className={styles.statementItem}>
            <span className={styles.statementDot}></span>
            <span>Speed matters. We optimize for fast execution without compromising quality.</span>
          </li>
          <li className={styles.statementItem}>
            <span className={styles.statementDot}></span>
            <span>Collaboration is non-negotiable. We make it seamless for modern teams.</span>
          </li>
          <li className={styles.statementItem}>
            <span className={styles.statementDot}></span>
            <span>Creativity thrives on constraints. We provide structure without stifling ideas.</span>
          </li>
          <li className={styles.statementItem}>
            <span className={styles.statementDot}></span>
            <span>Tools should work for people, not the other way around. We design with empathy and clarity.</span>
          </li>
        </ul>
      </PageSection>

      <PageSection>
        <div className={styles.metricGrid}>
          <article className={styles.metricCard}>
            <p className={styles.metricValue}>98%</p>
            <p className={styles.metricLabel}>Customer satisfaction score across all users</p>
          </article>
          <article className={styles.metricCard}>
            <p className={styles.metricValue}>12x</p>
            <p className={styles.metricLabel}>Faster design-to-launch time compared to traditional tools</p>
          </article>
          <article className={styles.metricCard}>
            <p className={styles.metricValue}>60+</p>
            <p className={styles.metricLabel}>Projects launched using Draftr</p>
          </article>
          <article className={styles.metricCard}>
            <p className={styles.metricValue}>85%</p>
            <p className={styles.metricLabel}>Teams that switched to Draftr now use it as their primary design tool</p>
          </article>
        </div>
      </PageSection>

      <PageSection>
        <div className={styles.aboutStatementBanner}>
          <h2 className={styles.darkShowcaseTitle}>
            Great tools create momentum for teams that need speed, clarity, and sharper collaboration.
          </h2>
          <p className={styles.darkShowcaseText}>
            Draftr is built to remove friction from the design process so teams can spend less
            time wrestling with tools and more time moving ideas into production.
          </p>
        </div>
      </PageSection>

      <PageSection>
        <div className={styles.logoStrip}>
          <div className={styles.logoTrack}>
            {[...clientLogos, ...clientLogos].map((logo, index) => (
              <img key={`${logo}-${index}`} src={logo} alt="" loading="lazy" />
            ))}
          </div>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="Meet the team"
          intro="At Draftr, we’re a small but passionate team of designers and product thinkers who believe that great tools create great outcomes."
        />

        <div className={styles.teamGrid}>
          {team.map((member) => (
            <article className={styles.teamCard} key={member.name}>
              <div className={styles.teamAvatar}>
                <span className={styles.teamInitials}>
                  {member.name
                    .split(' ')
                    .map((part) => part[0])
                    .join('')}
                </span>
              </div>
              <h3 className={styles.teamName}>{member.name}</h3>
              <p className={styles.teamRole}>{member.role}</p>
              <p className={styles.teamBio}>{member.bio}</p>
            </article>
          ))}
        </div>
      </PageSection>

      <PageSection>
        <Banner
          title="Take your creative workflow to the next level."
          text="We are always looking for people who care about thoughtful tools, sharper workflows, and better design systems."
          href="/contact"
          label="Open positions"
        />
      </PageSection>
    </MarketingShell>
  )
}
