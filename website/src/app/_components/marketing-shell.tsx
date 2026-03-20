/* eslint-disable @next/next/no-img-element */
import Link from 'next/link'
import type { ReactNode } from 'react'
import styles from './marketing-page.module.css'
import { footerColumns, routeNavItems, siteLogo, socialLinks } from './site-data'

type MarketingShellProps = {
  eyebrow: string
  title: string
  description: string
  children: ReactNode
}

export function MarketingShell({ eyebrow, title, description, children }: MarketingShellProps) {
  return (
    <div className={styles.shell}>
      <header className={styles.header} data-reveal data-reveal-delay="40ms" data-reveal-y="12px">
        <Link className={styles.brand} href="/" aria-label="Draftr home">
          <img src={siteLogo} alt="Draftr" />
        </Link>

        <nav className={styles.nav} aria-label="Primary navigation">
          {routeNavItems.map((item) => (
            <Link key={item.label} href={item.href} className={styles.navLink}>
              {item.label}
            </Link>
          ))}
        </nav>

        <Link className={styles.buttonGhost} href="/contact">
          Login now
        </Link>
      </header>

      <main>
        <section className={styles.hero} data-reveal data-reveal-delay="90ms">
          <p className={styles.eyebrow}>{eyebrow}</p>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.description}>{description}</p>
        </section>

        {children}
      </main>

      <footer className={styles.footer} data-reveal data-reveal-delay="80ms">
        <div className={styles.footerBrand}>
          <Link className={styles.brand} href="/" aria-label="Draftr home">
            <img src={siteLogo} alt="Draftr" />
          </Link>
          <p className={styles.footerCopy}>
            Create, review, and ship better design systems with a workspace made for speed.
          </p>
          <div className={styles.socialRow} aria-label="Social links">
            {socialLinks.map((link) => (
              <a
                key={link.label}
                className={styles.socialLink}
                href={link.href}
                rel="noreferrer"
                target="_blank"
                aria-label={link.label}
              >
                <img src={link.icon} alt="" />
              </a>
            ))}
          </div>
        </div>

        <div className={styles.footerLinks}>
          {footerColumns.map((column) => (
            <div className={styles.footerColumn} key={column.title}>
              <h3 className={styles.footerColumnTitle}>{column.title}</h3>
              <ul>
                {column.items.map((item) => (
                  <li key={item.label}>
                    <Link href={item.href}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </footer>
    </div>
  )
}

type SectionProps = {
  children: ReactNode
}

export function PageSection({ children }: SectionProps) {
  return <section className={styles.section} data-reveal>{children}</section>
}

type SectionHeaderProps = {
  title: string
  intro: string
}

export function SectionHeader({ title, intro }: SectionHeaderProps) {
  return (
    <>
      <h2 className={styles.sectionTitle}>{title}</h2>
      <p className={styles.sectionIntro}>{intro}</p>
    </>
  )
}

type CardGridProps = {
  items: Array<{ title: string; text: string }>
}

export function CardGrid({ items }: CardGridProps) {
  return (
    <div className={styles.cardGrid}>
      {items.map((item) => (
        <article className={styles.card} key={item.title}>
          <h3 className={styles.cardTitle}>{item.title}</h3>
          <p className={styles.cardText}>{item.text}</p>
        </article>
      ))}
    </div>
  )
}

type SplitLayoutProps = {
  left: ReactNode
  right: ReactNode
}

export function SplitLayout({ left, right }: SplitLayoutProps) {
  return (
    <div className={styles.split}>
      <div className={styles.panel}>{left}</div>
      <div className={styles.stack}>{right}</div>
    </div>
  )
}

type StackItemsProps = {
  items: Array<{ title: string; text: string }>
}

export function StackItems({ items }: StackItemsProps) {
  return (
    <>
      {items.map((item) => (
        <article className={styles.stackItem} key={item.title}>
          <h3 className={styles.stackItemTitle}>{item.title}</h3>
          <p className={styles.stackItemText}>{item.text}</p>
        </article>
      ))}
    </>
  )
}

type BannerProps = {
  title: string
  text: string
  href: string
  label: string
}

export function Banner({ title, text, href, label }: BannerProps) {
  return (
    <div className={styles.banner}>
      <div>
        <h2 className={styles.bannerTitle}>{title}</h2>
        <p className={styles.bannerText}>{text}</p>
      </div>
      <Link className={styles.button} href={href}>
        {label}
      </Link>
    </div>
  )
}

export { styles as marketingPageStyles }
