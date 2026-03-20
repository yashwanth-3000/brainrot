/* eslint-disable @next/next/no-img-element */
import { notFound } from 'next/navigation'
import {
  Banner,
  MarketingShell,
  PageSection,
  SectionHeader,
  marketingPageStyles as styles,
} from '../../_components/marketing-shell'
import { blogPosts } from '../../_content/blog-posts'

type PageProps = {
  params: Promise<{ slug: string }>
}

export function generateStaticParams() {
  return blogPosts.map((post) => ({ slug: post.slug }))
}

export default async function BlogDetailPage({ params }: PageProps) {
  const { slug } = await params
  const post = blogPosts.find((entry) => entry.slug === slug)

  if (!post) {
    notFound()
  }

  return (
    <MarketingShell
      eyebrow="Blog"
      title={post.title}
      description={post.excerpt}
    >
      <PageSection>
        <div className={styles.articleFrame}>
          <img className={styles.articleImage} src={post.image} alt="" />

          <div className={styles.articleBody}>
            <p className={styles.articleMeta}>{post.date}</p>
            <p className={styles.proseLead}>
              Strong SaaS pages are built on clarity: clearer value, clearer interaction,
              and clearer structure around the user’s next step.
            </p>

            {post.sections.map((section) => (
              <section className={styles.articleSection} key={section.title}>
                <h2>{section.title}</h2>
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </section>
            ))}
          </div>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeader
          title="More from the Draftr journal"
          intro="Keep exploring ideas on product communication, interaction design, and how strong SaaS experiences move from concept to launch."
        />

        <div className={styles.cardGrid}>
          {blogPosts
            .filter((entry) => entry.slug !== post.slug)
            .slice(0, 3)
            .map((entry) => (
              <article className={styles.card} key={entry.slug}>
                <p className={styles.postMeta}>{entry.date}</p>
                <h3 className={styles.cardTitle}>{entry.title}</h3>
                <p className={styles.cardText}>{entry.excerpt}</p>
              </article>
            ))}
        </div>
      </PageSection>

      <PageSection>
        <Banner
          title="Bring this level of clarity into your product site."
          text="Explore the main landing page and the rest of the subpages to see how the Draftr system carries across the full marketing site."
          href="/"
          label="Back to homepage"
        />
      </PageSection>
    </MarketingShell>
  )
}
