import { Banner, MarketingShell, PageSection, SectionHeader } from '../_components/marketing-shell'

export default function FourOhFourPage() {
  return (
    <MarketingShell
      eyebrow="404"
      title="This page does not exist."
      description="The route you tried to open could not be found. Head back to the homepage or jump into one of the main marketing pages."
    >
      <PageSection>
        <SectionHeader
          title="Try one of these next"
          intro="Use the footer links, head back to the homepage, or go directly to contact if you were looking for the main call to action."
        />
        <Banner
          title="Go back to the main experience."
          text="Return to the homepage to explore the primary product story, features, pricing, and call to action."
          href="/"
          label="Back to homepage"
        />
      </PageSection>
    </MarketingShell>
  )
}
