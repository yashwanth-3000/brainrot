/* eslint-disable @next/next/no-img-element */
import Link from 'next/link'
import { Banner, MarketingShell, PageSection, SectionHeader, marketingPageStyles as styles } from '../_components/marketing-shell'

const coreCards = [
  {
    title: 'Auto layout',
    text: 'Keep alignment, spacing, and structure consistent as pages evolve without rebuilding each section by hand.',
  },
  {
    title: 'Version history',
    text: 'Track iterations, compare changes, and revisit previous states without losing momentum in the current flow.',
  },
  {
    title: 'Reusable components',
    text: 'Build faster with patterns that stay consistent across teams, pages, and handoff states.',
  },
  {
    title: 'Developer handoff',
    text: 'Export-ready assets and clearer structure make the move from design to implementation easier.',
  },
  {
    title: 'Team permissions',
    text: 'Manage contributors, reviews, and ownership with better visibility across shared workspaces.',
  },
  {
    title: 'Built-in prototyping',
    text: 'Move from static ideas to interactive product flows without leaving the main design environment.',
  },
]

export default function PowerUpsPage() {
  return (
    <MarketingShell
      eyebrow="Power-Ups"
      title="Power-Ups"
      description="This is not another homepage. These are additional and alternative sections designed for when your website or message needs more flexibility."
    >
      <PageSection>
        <div className={styles.heroSplit}>
          <div className={`${styles.panel} ${styles.panelDark}`}>
            <p className={styles.eyebrow}>New</p>
            <h2 className={styles.darkShowcaseTitle}>Revolutionize your design workflow</h2>
            <p className={styles.darkShowcaseText}>
              Copy any section, paste it into your page, and customize it as needed.
              Add only what supports your goal. Skip the rest. Nothing breaks the original structure.
            </p>

            <div className={styles.actions}>
              <Link className={styles.button} href="/contact">
                Get Started • it&apos;s free
              </Link>
              <Link className={styles.buttonSecondary} href="/contact">
                Watch a 2-min demo
              </Link>
            </div>

            <div className={styles.pillRow}>
              <span className={styles.pill}>All-in-one workspace</span>
              <span className={styles.pill}>Real-time collaboration</span>
              <span className={styles.pill}>Built-in prototyping</span>
              <span className={styles.pill}>Easy setup</span>
            </div>
          </div>

          <div className={styles.heroPanel}>
            <img
              src="https://framerusercontent.com/images/eKS0KEkPf4QiU3IiHORWYygVUI.jpg?scale-down-to=1024&width=2400&height=1900"
              alt="Power-Ups hero preview"
            />
            <img
              className={styles.heroPanelBadge}
              src="https://framerusercontent.com/images/4FKumHemzcAc3N8KKCHn8yZrRAg.svg?width=111&height=66"
              alt=""
            />
            <img
              className={styles.heroPanelBadgeCorner}
              src="https://framerusercontent.com/images/5zrSIP9NSKIsNbxQIW5WP5VvpXk.svg?width=187&height=58"
              alt=""
            />
          </div>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="Built to replace tool stacks"
          intro="The Power-Ups page extends the system with flexible sections that can be dropped into your marketing site without breaking the overall visual rhythm."
        />

        <div className={styles.valueGrid}>
          {coreCards.map((card) => (
            <article className={styles.valueCard} key={card.title}>
              <h3>{card.title}</h3>
              <p>{card.text}</p>
            </article>
          ))}
        </div>
      </PageSection>

      <PageSection>
        <div className={styles.darkShowcase}>
          <h2 className={styles.darkShowcaseTitle}>
            Auto layout is here, along with improvements to alignment and structure.
          </h2>
          <p className={styles.darkShowcaseText}>
            Use Power-Ups when you need more flexibility in the marketing story, more room
            to explain workflows, or a stronger bridge between product value and page structure.
          </p>

          <div className={styles.darkGrid}>
            <article className={styles.darkGridCard}>
              <h3>AI Layout optimizer</h3>
              <p>Organize complex sections faster and keep spacing logic cleaner across breakpoints.</p>
            </article>
            <article className={styles.darkGridCard}>
              <h3>Designed for real team workflows</h3>
              <p>Show more context around collaboration, approvals, and reusable systems without clutter.</p>
            </article>
            <article className={styles.darkGridCard}>
              <h3>Built for modern design workflows</h3>
              <p>Combine structure, motion, and product proof in a way that feels stronger than a static template.</p>
            </article>
          </div>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="How Draftr works"
          intro="The same visual language can support multiple narratives: feature education, workflow explanation, or more product-forward storytelling."
        />

        <div className={styles.cardGrid}>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>1. Start with the core story</h3>
            <p className={styles.cardText}>Use the strongest product message as the anchor, then add only the sections that help explain it.</p>
          </article>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>2. Mix in the right Power-Ups</h3>
            <p className={styles.cardText}>Drop in alternate hero blocks, workflow sections, or comparison layouts where the default homepage needs more range.</p>
          </article>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>3. Keep the system coherent</h3>
            <p className={styles.cardText}>The goal is flexibility without losing the clean Draftr visual identity across the site.</p>
          </article>
        </div>
      </PageSection>

      <PageSection>
        <Banner
          title="Need more sections than the base site includes?"
          text="Use the contact page if you want to extend the site further with more route-specific layouts, CMS pages, or a deeper SaaS marketing system."
          href="/contact"
          label="Request them here"
        />
      </PageSection>
    </MarketingShell>
  )
}
