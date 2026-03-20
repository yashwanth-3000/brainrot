/* eslint-disable @next/next/no-img-element */
import Link from 'next/link'
import { Banner, MarketingShell, PageSection, SectionHeader, marketingPageStyles as styles } from '../_components/marketing-shell'
import { blogPosts } from '../_content/blog-posts'

export default function BlogPage() {
  return (
    <MarketingShell
      eyebrow="Blog"
      title="SaaS insights & tips"
      description="Practical ideas and trends to help your software brand grow, communicate more clearly, and stand out with stronger product storytelling."
    >
      <PageSection>
        <SectionHeader
          title="Latest stories"
          intro="A focused library of articles on SaaS design, performance, onboarding, and product communication."
        />

        <div className={styles.postGrid}>
          {blogPosts.map((post, index) => (
            <article
              className={`${styles.postCard}${index === 0 ? ` ${styles.postCardFeatured}` : ''}`}
              key={post.slug}
            >
              <img className={styles.postImage} src={post.image} alt="" loading="lazy" />
              <div className={styles.postBody}>
                <p className={styles.postMeta}>{post.date}</p>
                <h2 className={styles.postTitle}>{post.title}</h2>
                <p className={styles.postExcerpt}>{post.excerpt}</p>
                <Link className={styles.postLink} href={`/blog/${post.slug}`}>
                  Read article
                </Link>
              </div>
            </article>
          ))}
        </div>
      </PageSection>

      <PageSection>
        <Banner
          title="Want updates when new posts land?"
          text="Join the waitlist and we will share release notes, product ideas, and fresh resources as the platform evolves."
          href="/waitlist"
          label="Join the waitlist"
        />
      </PageSection>
    </MarketingShell>
  )
}
