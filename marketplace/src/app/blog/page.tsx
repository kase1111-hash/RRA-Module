import Link from 'next/link';
import { Calendar, ArrowRight } from 'lucide-react';

const posts = [
  {
    id: 1,
    title: 'Introducing RRA: Autonomous Code Licensing',
    excerpt: 'Today we launch RRA, a new way to license and monetize code using AI agents and blockchain technology.',
    date: '2025-01-15',
    category: 'Announcement',
    readTime: '5 min read',
  },
  {
    id: 2,
    title: 'Understanding Story Protocol Integration',
    excerpt: 'A deep dive into how RRA uses Story Protocol for on-chain IP registration and royalty enforcement.',
    date: '2025-01-10',
    category: 'Technical',
    readTime: '8 min read',
  },
  {
    id: 3,
    title: 'The Future of Open Source Monetization',
    excerpt: 'How programmable IP and AI agents are changing the economics of open source software.',
    date: '2025-01-05',
    category: 'Insights',
    readTime: '6 min read',
  },
];

export default function BlogPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">Blog</h1>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            News, updates, and insights from the RRA team.
          </p>
        </div>

        {/* Featured Post */}
        <div className="mt-12">
          <div className="overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 shadow-xl">
            <div className="p-8 md:p-12">
              <span className="inline-block rounded-full bg-white/20 px-3 py-1 text-sm text-white">
                Featured
              </span>
              <h2 className="mt-4 text-3xl font-bold text-white">
                RRA Module v1.0 Released
              </h2>
              <p className="mt-4 max-w-2xl text-lg text-indigo-100">
                We&apos;re excited to announce the first stable release of RRA Module.
                This release includes full Story Protocol integration, AI-powered license
                advisors, and a beautiful marketplace UI.
              </p>
              <Link
                href="/docs"
                className="mt-6 inline-flex items-center gap-2 text-white hover:underline"
              >
                Read the full announcement
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>

        {/* Post Grid */}
        <div className="mt-12 grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post) => (
            <article
              key={post.id}
              className="overflow-hidden rounded-xl bg-white shadow-lg transition hover:shadow-xl dark:bg-gray-800"
            >
              <div className="h-48 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600" />
              <div className="p-6">
                <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
                    {post.category}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {new Date(post.date).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </span>
                </div>
                <h3 className="mt-3 text-xl font-semibold text-gray-900 dark:text-white">
                  {post.title}
                </h3>
                <p className="mt-2 text-gray-600 dark:text-gray-300">{post.excerpt}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">{post.readTime}</span>
                  <Link
                    href={`/blog/${post.id}`}
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
                  >
                    Read more →
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </div>

        {/* Newsletter */}
        <div className="mt-16 rounded-2xl bg-white p-8 shadow-lg dark:bg-gray-800 md:p-12">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Subscribe to our newsletter
            </h2>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              Get the latest updates on RRA development and the future of code licensing.
            </p>
            <form className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <input
                type="email"
                placeholder="Enter your email"
                className="rounded-lg border border-gray-300 px-4 py-3 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
              <button
                type="submit"
                className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white hover:bg-indigo-700"
              >
                Subscribe
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
