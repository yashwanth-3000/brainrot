import {
  MarketingShell,
  PageSection,
  SectionHeader,
  marketingPageStyles as styles,
} from '../../_components/marketing-shell'

export default function PrivacyPolicyPage() {
  return (
    <MarketingShell
      eyebrow="Privacy"
      title="Privacy policy"
      description="This page reflects the structure and content style of the live Draftr privacy page while staying consistent with the rest of the rebuilt site."
    >
      <PageSection>
        <SectionHeader
          title="How information is handled"
          intro="A concise overview of the information Draftr may collect, how it may be used, and what users can expect in a typical SaaS privacy policy."
        />

        <div className={styles.prose}>
          <p className={styles.proseMeta}>Last updated: Jan 5, 2026</p>
          <p className={styles.proseLead}>
            We collect information to provide a better experience and improve our
            services. The types of data we collect typically include account details,
            communication records, uploaded content, usage signals, and device information.
          </p>

          <h2>Information we collect</h2>
          <p>
            Account information may include name, email address, company name,
            password, and other details provided during sign-up.
          </p>
          <p>
            Billing information may include payment details and billing addresses,
            processed securely through payment partners.
          </p>
          <p>
            We may also collect communications submitted through support, contact forms,
            or chat channels, along with uploaded files and workspace content required
            to provide the service.
          </p>

          <h2>Usage, device, and tracking data</h2>
          <p>
            Usage data may include how features are accessed, the amount of time spent in
            the application, and the pages visited while using Draftr.
          </p>
          <p>
            Device information may include browser type, IP address, operating system,
            and device identifiers. Cookies, web beacons, and analytics tools may be
            used to understand behavior and improve the platform.
          </p>

          <h2>Information from integrations</h2>
          <p>
            We may receive limited data from integrations such as Slack, Notion, or
            Trello when you choose to connect them to Draftr, as well as from payment
            processors and analytics providers.
          </p>

          <h2>How collected information is used</h2>
          <ul>
            <li>Provide, operate, and maintain the service.</li>
            <li>Improve performance, reliability, and overall user experience.</li>
            <li>Process payments and send invoices.</li>
            <li>Respond to support requests and product inquiries.</li>
            <li>Send product updates, promotional offers, and security alerts.</li>
          </ul>

          <h2>Questions or requests</h2>
          <p>
            If you have questions about data handling, privacy requests, or account
            information, contact <a className={styles.inlineLink} href="mailto:support@draftr.com">support@draftr.com</a>.
          </p>
        </div>
      </PageSection>
    </MarketingShell>
  )
}
