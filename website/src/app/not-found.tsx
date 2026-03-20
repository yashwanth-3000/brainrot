import { Banner, MarketingShell, PageSection, SectionHeader } from './_components/marketing-shell'

export default function NotFound() {
  return (
    <MarketingShell
      eyebrow="Not found"
      title="We could not find that page."
      description="The route may have moved, the link may be outdated, or the page may not exist yet."
    >
      <PageSection>
        <SectionHeader
          title="Start from the homepage"
          intro="The main landing page includes the core product story, pricing, power-ups, and the primary call to action."
        />
        <Banner
          title="Return to Draftr."
          text="Go back to the homepage and continue from the main site experience."
          href="/"
          label="Go home"
        />
      </PageSection>
    </MarketingShell>
  )
}
