import {
  Banner,
  MarketingShell,
  PageSection,
  SectionHeader,
  marketingPageStyles as styles,
} from '../_components/marketing-shell'

const faqs = [
  {
    question: 'What is Draftr?',
    answer:
      'Draftr is a collaborative design platform built to simplify prototyping, feedback, and production-ready handoff in one workspace.',
  },
  {
    question: 'Do I need to install anything to use Draftr?',
    answer:
      'No. The platform is designed to be accessible in the cloud so teams can move quickly without heavy local setup.',
  },
  {
    question: 'Can I collaborate with others in real time?',
    answer:
      'Yes. Real-time collaboration, shared context, and faster review loops are central to the product experience.',
  },
  {
    question: 'Is there a free plan available?',
    answer:
      'The site is structured around a starter tier and higher plans for teams, with room to expand into more advanced workflows as needed.',
  },
]

export default function ContactPage() {
  return (
    <MarketingShell
      eyebrow="Contact"
      title="Get in touch with us"
      description="Have questions, need help, or want to discover more about Draftr? We&apos;re here to support you every step of the way."
    >
      <PageSection>
        <div className={styles.contactGrid}>
          <section className={styles.formCard}>
            <SectionHeader
              title="Send us a message"
              intro="Questions, feedback, or support? Our team is just a message away."
            />

            <form className={styles.fieldGrid}>
              <div className={styles.field}>
                <label htmlFor="name">Name*</label>
                <input id="name" placeholder="Your name" type="text" />
              </div>
              <div className={styles.field}>
                <label htmlFor="email">Email*</label>
                <input id="email" placeholder="you@company.com" type="email" />
              </div>
              <div className={styles.field}>
                <label htmlFor="company">Company*</label>
                <input id="company" placeholder="Company name" type="text" />
              </div>
              <div className={styles.field}>
                <label htmlFor="phone">Phone*</label>
                <input id="phone" placeholder="+1 (555) 000-0000" type="tel" />
              </div>
              <div className={styles.fieldFull}>
                <label htmlFor="message">Message*</label>
                <textarea id="message" placeholder="Tell us what you're building and how we can help." />
              </div>
              <div className={styles.fieldFull}>
                <button className={styles.button} type="button">
                  Send message
                </button>
              </div>
            </form>
          </section>

          <div className={styles.supportGrid}>
            <article className={styles.supportCard}>
              <p className={styles.supportLabel}>Support</p>
              <h3 className={styles.supportTitle}>support@draftr.com</h3>
              <p className={styles.supportText}>Need help? Our team is here to assist with setup, product questions, and active support issues.</p>
            </article>

            <article className={styles.supportCard}>
              <p className={styles.supportLabel}>Sales</p>
              <h3 className={styles.supportTitle}>sales@draftr.com</h3>
              <p className={styles.supportText}>Interested in Draftr for your team? Let’s talk pricing, rollout plans, and the right setup for your workflow.</p>
            </article>

            <article className={`${styles.panel} ${styles.panelSoft}`}>
              <h3 className={styles.cardTitle}>Response expectations</h3>
              <p className={styles.cardText}>
                Share the stage you&apos;re at, the size of your team, and what part of the workflow feels slow right now. That makes it easier for us to point you in the right direction.
              </p>
            </article>
          </div>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="Frequently asked questions"
          intro="Find quick answers to common questions about Draftr."
        />

        <div className={styles.faqList}>
          {faqs.map((item) => (
            <article className={styles.faqItem} key={item.question}>
              <h3 className={styles.faqQuestion}>{item.question}</h3>
              <p className={styles.faqAnswer}>{item.answer}</p>
            </article>
          ))}
        </div>
      </PageSection>

      <PageSection>
        <Banner
          title="Still deciding where to start?"
          text="Join the waitlist if you want updates first, or reach out directly if you need a faster conversation about pricing and product fit."
          href="/waitlist"
          label="Join the waitlist"
        />
      </PageSection>
    </MarketingShell>
  )
}
