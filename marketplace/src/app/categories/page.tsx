import Link from 'next/link';
import { ArrowRight, Code, Cpu, Database, Globe, Lock, Palette, Server, Smartphone } from 'lucide-react';

const categories = [
  {
    id: 'web3',
    name: 'Web3 & Blockchain',
    description: 'Smart contracts, DeFi protocols, and blockchain utilities',
    icon: Database,
    color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-400',
    count: 24,
  },
  {
    id: 'ml-ai',
    name: 'Machine Learning & AI',
    description: 'ML pipelines, model training, and AI utilities',
    icon: Cpu,
    color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400',
    count: 18,
  },
  {
    id: 'frontend',
    name: 'Frontend & UI',
    description: 'React components, design systems, and UI libraries',
    icon: Palette,
    color: 'bg-pink-100 text-pink-600 dark:bg-pink-900/50 dark:text-pink-400',
    count: 42,
  },
  {
    id: 'backend',
    name: 'Backend & APIs',
    description: 'Server frameworks, API tools, and microservices',
    icon: Server,
    color: 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400',
    count: 36,
  },
  {
    id: 'security',
    name: 'Security & Crypto',
    description: 'Cryptographic libraries, authentication, and security tools',
    icon: Lock,
    color: 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400',
    count: 15,
  },
  {
    id: 'mobile',
    name: 'Mobile Development',
    description: 'React Native, Flutter, and mobile utilities',
    icon: Smartphone,
    color: 'bg-amber-100 text-amber-600 dark:bg-amber-900/50 dark:text-amber-400',
    count: 12,
  },
  {
    id: 'devtools',
    name: 'Developer Tools',
    description: 'CLI tools, linters, formatters, and dev utilities',
    icon: Code,
    color: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    count: 28,
  },
  {
    id: 'integrations',
    name: 'Integrations',
    description: 'Third-party API clients and service integrations',
    icon: Globe,
    color: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-400',
    count: 21,
  },
];

export default function CategoriesPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-8 dark:border-gray-800 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Categories
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Browse repositories by category
          </p>
        </div>
      </div>

      {/* Categories Grid */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <Link
                key={category.id}
                href={`/search?category=${category.id}`}
                className="group flex flex-col rounded-xl border border-gray-200 bg-white p-6 transition-all hover:border-gray-300 hover:shadow-lg dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600"
              >
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${category.color}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">
                  {category.name}
                </h3>
                <p className="mt-2 flex-1 text-sm text-gray-600 dark:text-gray-400">
                  {category.description}
                </p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {category.count} repositories
                  </span>
                  <ArrowRight className="h-4 w-4 text-gray-400 transition-transform group-hover:translate-x-1 group-hover:text-primary-600" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
