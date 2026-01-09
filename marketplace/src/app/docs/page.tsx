import Link from 'next/link';
import { Book, Rocket, Code, Settings, Shield, HelpCircle, ArrowRight } from 'lucide-react';

const docSections = [
  {
    title: 'Getting Started',
    description: 'Learn the basics of the RRA Marketplace',
    icon: Rocket,
    href: '/docs/quickstart',
    articles: [
      { title: 'Quick Start Guide', href: '/docs/quickstart' },
      { title: 'How It Works', href: '/docs/how-it-works' },
    ],
  },
  {
    title: 'Configuration',
    description: 'Configure your repository for the marketplace',
    icon: Settings,
    href: '/docs/market-yaml',
    articles: [
      { title: 'market.yaml Reference', href: '/docs/market-yaml' },
    ],
  },
  {
    title: 'Integration',
    description: 'Integrate with NatLangChain and other systems',
    icon: Code,
    href: '/docs/natlangchain',
    articles: [
      { title: 'NatLangChain Integration', href: '/docs/natlangchain' },
      { title: 'API Reference', href: '/docs/api' },
    ],
  },
  {
    title: 'Security',
    description: 'Security best practices and verification',
    icon: Shield,
    href: '/docs/verification',
    articles: [
      { title: 'Code Verification', href: '/docs/verification' },
    ],
  },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-12 dark:border-gray-800 dark:bg-gray-800">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center justify-center rounded-full bg-primary-100 p-3 dark:bg-primary-900/50">
            <Book className="h-8 w-8 text-primary-600 dark:text-primary-400" />
          </div>
          <h1 className="mt-4 text-3xl font-bold text-gray-900 dark:text-white">
            Documentation
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
            Everything you need to know about the RRA Marketplace
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Quick Start Banner */}
        <Link
          href="/docs/quickstart"
          className="group mb-12 flex items-center justify-between rounded-xl border border-primary-200 bg-gradient-to-r from-primary-50 to-primary-100 p-6 transition-all hover:shadow-lg dark:border-primary-800 dark:from-primary-900/20 dark:to-primary-900/40"
        >
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-600 text-white">
              <Rocket className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Quick Start Guide
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Get your repository on the marketplace in 5 minutes
              </p>
            </div>
          </div>
          <ArrowRight className="h-5 w-5 text-primary-600 transition-transform group-hover:translate-x-1" />
        </Link>

        {/* Doc Sections */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          {docSections.map((section) => {
            const Icon = section.icon;
            return (
              <div
                key={section.title}
                className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700">
                    <Icon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {section.title}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {section.description}
                    </p>
                  </div>
                </div>
                <ul className="mt-4 space-y-2">
                  {section.articles.map((article) => (
                    <li key={article.href}>
                      <Link
                        href={article.href}
                        className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                      >
                        {article.title}
                        <ArrowRight className="h-4 w-4 text-gray-400" />
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>

        {/* Help Section */}
        <div className="mt-12 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center gap-3">
            <HelpCircle className="h-6 w-6 text-gray-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Need Help?</h3>
          </div>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Can&apos;t find what you&apos;re looking for? Check out our{' '}
            <Link href="https://github.com/kase1111-hash/RRA-Module/issues" className="text-primary-600 hover:underline">
              GitHub Issues
            </Link>{' '}
            or join our community.
          </p>
        </div>
      </div>
    </div>
  );
}
