export type BlogPost = {
  slug: string
  title: string
  date: string
  image: string
  excerpt: string
  sections: Array<{
    title: string
    paragraphs: string[]
  }>
}

export const blogPosts: BlogPost[] = [
  {
    slug: 'best-practices-for-showcasing-features',
    title: 'Best practices for showcasing features',
    date: 'Oct 13, 2025',
    image:
      'https://framerusercontent.com/images/UpYdm4GAhAy4TlREwNzfPP24MN0.jpg?scale-down-to=512&width=1400&height=800',
    excerpt:
      'A clear feature story helps visitors understand what your product does, why it matters, and where it fits into their workflow.',
    sections: [
      {
        title: 'Lead with the job to be done',
        paragraphs: [
          'Feature sections work best when they are written around outcomes, not internal product language. Visitors scan quickly, so the first line should explain the result they get, not just the capability you built.',
          'A strong feature headline pairs a clear promise with a short explanation that gives enough context for the user to picture it inside their own workflow.',
        ],
      },
      {
        title: 'Use structure to reduce cognitive load',
        paragraphs: [
          'The best SaaS pages keep sections visually distinct. Consistent spacing, a limited number of supporting points, and a clean rhythm between text and visuals make the page easier to understand.',
          'If every feature block is equally dense, nothing stands out. Prioritize the most important capabilities and let secondary details sit underneath in a calmer layout.',
        ],
      },
      {
        title: 'Pair copy with proof',
        paragraphs: [
          'Feature claims land better when they are supported by screenshots, short examples, or workflow states that feel concrete. That visual context turns a promise into something more believable.',
        ],
      },
    ],
  },
  {
    slug: 'visual-storytelling-for-complex-products',
    title: 'Visual storytelling for complex products',
    date: 'Oct 13, 2025',
    image:
      'https://framerusercontent.com/images/1gLOXwPPBbxglRm25gwjVIQNHt4.jpg?scale-down-to=512&width=1400&height=800',
    excerpt:
      'Complex products need pages that explain flow, not just surface-level features. Strong visual storytelling keeps that explanation clear.',
    sections: [
      {
        title: 'Show sequence, not just screens',
        paragraphs: [
          'For complex products, isolated screenshots often feel disconnected. A better approach is to show how one step leads into the next so the workflow feels intentional.',
          'Motion cues, stacked cards, and sequenced layouts help visitors follow the story without needing long paragraphs to bridge every transition.',
        ],
      },
      {
        title: 'Anchor every visual to a message',
        paragraphs: [
          'Visuals should reinforce a point the copy is already making. If a screenshot is attractive but disconnected from the text, it becomes decoration rather than explanation.',
        ],
      },
      {
        title: 'Balance atmosphere with clarity',
        paragraphs: [
          'A strong visual system can be expressive without getting noisy. Use contrast, depth, and brand color deliberately, but keep text legible and page structure obvious at every breakpoint.',
        ],
      },
    ],
  },
  {
    slug: 'how-microinteractions-boost-user-experience',
    title: 'How microinteractions boost user experience',
    date: 'Oct 13, 2025',
    image:
      'https://framerusercontent.com/images/F2C5Yf6CwPlnsYAlalA7lI2lbiQ.jpg?scale-down-to=512&width=1400&height=800',
    excerpt:
      'Small interactions shape how fast, clear, and polished a product feels. Done well, they reduce hesitation and reinforce confidence.',
    sections: [
      {
        title: 'Feedback should feel immediate',
        paragraphs: [
          'Hover states, pressed states, and subtle movement help users understand what is interactive before they commit to a click.',
          'These interactions are especially important in SaaS products where users are moving through dense interfaces and making frequent decisions.',
        ],
      },
      {
        title: 'Microinteractions should clarify, not distract',
        paragraphs: [
          'Animation should support understanding. If the motion is louder than the message, it slows the user down instead of helping them move forward.',
        ],
      },
      {
        title: 'Consistency matters more than novelty',
        paragraphs: [
          'The best interaction systems reuse the same timing, easing, and feedback patterns across the product so users learn them once and benefit everywhere.',
        ],
      },
    ],
  },
  {
    slug: 'why-performance-and-accessibility-matter',
    title: 'Why performance and accessibility matter',
    date: 'Oct 13, 2025',
    image:
      'https://framerusercontent.com/images/9rMiHqwr31qAGJB54MqJ6eNM4.jpg?scale-down-to=512&width=1400&height=800',
    excerpt:
      'Fast, accessible products are easier to trust. They load with less friction and work for more people across more contexts.',
    sections: [
      {
        title: 'Performance shapes first impressions',
        paragraphs: [
          'The first seconds on a page influence how credible the product feels. Slow layout shifts, heavy media, and delayed interactions all add hidden friction.',
        ],
      },
      {
        title: 'Accessibility improves the overall product',
        paragraphs: [
          'Accessible interfaces do not just help edge cases. Clear hierarchy, predictable controls, and thoughtful contrast improve comprehension for everyone.',
        ],
      },
      {
        title: 'Treat both as part of the design system',
        paragraphs: [
          'Performance and accessibility are easier to maintain when they are built into components, spacing rules, and content patterns from the start instead of added later as fixes.',
        ],
      },
    ],
  },
  {
    slug: 'from-idea-to-launch-saas-ui-ux-guide',
    title: 'From idea to launch: SaaS UI/UX guide',
    date: 'Oct 13, 2025',
    image:
      'https://framerusercontent.com/images/zfKj6bOFq5JiU7zl0geDsGQ82pY.jpg?scale-down-to=512&width=1400&height=800',
    excerpt:
      'Moving from concept to launch requires more than attractive screens. It takes a system that keeps decisions aligned from exploration through implementation.',
    sections: [
      {
        title: 'Start with the workflow, not the page',
        paragraphs: [
          'A SaaS product should be framed around what the user is trying to accomplish. That means mapping the workflow first and designing screens that support the key steps inside it.',
        ],
      },
      {
        title: 'Turn repeated decisions into patterns',
        paragraphs: [
          'Reusable layout logic, input behavior, and visual hierarchy make products easier to scale. They also reduce the amount of rework needed when the product grows.',
        ],
      },
      {
        title: 'Plan handoff early',
        paragraphs: [
          'Launch gets easier when design and engineering share a structured system. Clean naming, component reuse, and predictable states make the final build faster and more reliable.',
        ],
      },
    ],
  },
  {
    slug: 'simplifying-user-journeys-for-more-signups',
    title: 'Simplifying user journeys for more signups',
    date: 'Oct 13, 2025',
    image:
      'https://framerusercontent.com/images/IIjQuVoM5lwsVUtCbk8zUUPRX4.jpg?scale-down-to=512&width=1400&height=800',
    excerpt:
      'More signups usually come from fewer decisions, clearer value, and a path that feels easy to follow from first impression to action.',
    sections: [
      {
        title: 'Reduce competing calls to action',
        paragraphs: [
          'Visitors are more likely to convert when the page gives them an obvious next step. Too many equal-priority actions create hesitation instead of momentum.',
        ],
      },
      {
        title: 'Explain value before asking for commitment',
        paragraphs: [
          'If the page asks for a signup before the product feels clear, many visitors leave. Make the benefit legible before the ask gets heavy.',
        ],
      },
      {
        title: 'Use layout to guide attention',
        paragraphs: [
          'The most effective signup flows combine hierarchy, spacing, and proof in a way that quietly leads the visitor forward without forcing the interaction.',
        ],
      },
    ],
  },
]
