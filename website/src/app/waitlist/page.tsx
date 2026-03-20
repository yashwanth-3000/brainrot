import { Banner, MarketingShell, PageSection, SectionHeader, marketingPageStyles as styles } from '../_components/marketing-shell'

export default function WaitlistPage() {
  return (
    <MarketingShell
      eyebrow="Waitlist"
      title="Join the waitlist for early access"
      description="We’re opening up limited early access to writers, marketers, and teams who want to create smarter, faster, and with less effort."
    >
      <PageSection>
        <div className={styles.waitlistCard}>
          <SectionHeader
            title="Get notified first"
            intro="Join the list for early updates, new page releases, and product improvements as the Draftr system expands."
          />

          <div className={styles.waitlistInputRow}>
            <input className={styles.waitlistInput} placeholder="Email*" type="email" />
            <button className={styles.button} type="button">
              Join the waitlist
            </button>
          </div>

          <div className={styles.waitlistBenefits}>
            <div className={styles.waitlistBenefit}>
              <span className={styles.waitlistBenefitMark}></span>
              <p className={styles.waitlistBenefitText}>Get early visibility into new subpages, content blocks, and product-facing layout updates.</p>
            </div>
            <div className={styles.waitlistBenefit}>
              <span className={styles.waitlistBenefitMark}></span>
              <p className={styles.waitlistBenefitText}>Hear about release notes, workflow improvements, and new sections before they ship publicly.</p>
            </div>
            <div className={styles.waitlistBenefit}>
              <span className={styles.waitlistBenefitMark}></span>
              <p className={styles.waitlistBenefitText}>Stay close to the product story as Draftr grows into a broader SaaS marketing system.</p>
            </div>
          </div>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="Why join now"
          intro="The waitlist is the best place to stay close to the next wave of design, content, and workflow updates."
        />

        <div className={styles.cardGrid}>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>Early release access</h3>
            <p className={styles.cardText}>See changes to the marketing system before they are rolled into the wider public site.</p>
          </article>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>Priority product updates</h3>
            <p className={styles.cardText}>Track the highest-signal improvements without needing to dig through every release detail manually.</p>
          </article>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>Closer product feedback loop</h3>
            <p className={styles.cardText}>Stay connected to how the product narrative, route structure, and feature set continue to evolve.</p>
          </article>
        </div>
      </PageSection>

      <PageSection>
        <Banner
          title="Need a direct conversation instead?"
          text="If you already know what you want to build, the contact page is the fastest way to talk through product fit and rollout details."
          href="/contact"
          label="Contact the team"
        />
      </PageSection>
    </MarketingShell>
  )
}
