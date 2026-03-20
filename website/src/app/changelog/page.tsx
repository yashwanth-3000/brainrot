import { Banner, MarketingShell, PageSection, SectionHeader, marketingPageStyles as styles } from '../_components/marketing-shell'

const releases = [
  {
    version: 'Version 1.2.0',
    lead: 'Stay up to date with the latest improvements, fixes, and new features.',
    blocks: [
      {
        title: 'New pages added',
        items: [
          'Power-Ups page: a collection of additional and alternative UI sections designed for when your website or message needs more flexibility.',
        ],
      },
      {
        title: 'Improvements',
        items: ['Homepage: improved feature card animations for smoother interaction.'],
      },
    ],
  },
  {
    version: 'Version 1.1.1',
    lead: 'A smaller update focused on implementation quality and source assets.',
    blocks: [
      {
        title: 'Added',
        items: ['Figma file added.'],
      },
    ],
  },
  {
    version: 'Version 1.1.0',
    lead: 'Expanded the template beyond the main landing page with more ready-to-use routes.',
    blocks: [
      {
        title: 'New pages added',
        items: [
          'Changelog page',
          'Waitlist page',
          'Privacy Policy (CMS)',
          'Blog (CMS)',
          'Blog Detail (CMS)',
        ],
      },
      {
        title: 'Fixes',
        items: ['Improved Contact Form button animation for smoother interaction.'],
      },
    ],
  },
  {
    version: 'Version 1.0.0',
    lead: 'A foundational release that established the core marketing system and content structure.',
    blocks: [
      {
        title: 'Updates',
        items: ['About page: added CTA in the team section.'],
      },
    ],
  },
]

export default function ChangelogPage() {
  return (
    <MarketingShell
      eyebrow="Changelog"
      title="Draftr changelog"
      description="Stay up to date with the latest improvements, fixes, and new features across the Draftr marketing experience."
    >
      <PageSection>
        <SectionHeader
          title="Release history"
          intro="A running log of what changed, what was added, and where the template experience improved."
        />

        <div className={styles.timeline}>
          {releases.map((release) => (
            <article className={styles.timelineItem} key={release.version}>
              <div>
                <h2 className={styles.timelineVersion}>{release.version}</h2>
                <p className={styles.timelineLead}>{release.lead}</p>
              </div>

              <div className={styles.timelineBlocks}>
                {release.blocks.map((block) => (
                  <section className={styles.timelineBlock} key={block.title}>
                    <h3 className={styles.timelineBlockTitle}>{block.title}</h3>
                    <ul>
                      {block.items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            </article>
          ))}
        </div>
      </PageSection>

      <PageSection>
        <Banner
          title="Need a closer product walkthrough?"
          text="Reach out and we can walk through the latest updates, what is shipping next, and where the product narrative is headed."
          href="/contact"
          label="Contact the team"
        />
      </PageSection>
    </MarketingShell>
  )
}
