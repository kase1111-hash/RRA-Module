'use client';

import Link from 'next/link';
import { ArrowRight, Package, DollarSign, MessageSquare, TrendingUp, Clock, CheckCircle } from 'lucide-react';

// Mock data for dashboard
const stats = [
  { label: 'Total Repositories', value: '3', icon: Package, change: '+1 this month' },
  { label: 'Total Revenue', value: '2.45 ETH', icon: DollarSign, change: '+0.8 ETH this month' },
  { label: 'Active Chats', value: '5', icon: MessageSquare, change: '2 pending response' },
  { label: 'Completed Sales', value: '12', icon: CheckCircle, change: '+3 this week' },
];

const recentActivity = [
  {
    id: 1,
    type: 'sale',
    message: 'License sold for RRA-Module',
    amount: '0.05 ETH',
    time: '2 hours ago',
  },
  {
    id: 2,
    type: 'inquiry',
    message: 'New license inquiry for web3-utils',
    amount: null,
    time: '5 hours ago',
  },
  {
    id: 3,
    type: 'sale',
    message: 'Enterprise license sold for ml-pipeline',
    amount: '0.15 ETH',
    time: '1 day ago',
  },
  {
    id: 4,
    type: 'update',
    message: 'RRA-Module verification score updated',
    amount: null,
    time: '2 days ago',
  },
];

const myRepositories = [
  {
    id: 'rra-module-abc123',
    name: 'RRA-Module',
    sales: 8,
    revenue: '0.40 ETH',
    activeChats: 2,
    status: 'active',
  },
  {
    id: 'web3-utils-def456',
    name: 'web3-utils',
    sales: 3,
    revenue: '0.06 ETH',
    activeChats: 1,
    status: 'active',
  },
  {
    id: 'ml-pipeline-ghi789',
    name: 'ml-pipeline',
    sales: 1,
    revenue: '0.15 ETH',
    activeChats: 2,
    status: 'pending_verification',
  },
];

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-8 dark:border-gray-800 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Dashboard
              </h1>
              <p className="mt-1 text-gray-600 dark:text-gray-400">
                Manage your repositories and track earnings
              </p>
            </div>
            <Link
              href="/docs/quickstart"
              className="inline-flex items-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              Add Repository
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/50">
                    <Icon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <TrendingUp className="h-4 w-4 text-green-500" />
                </div>
                <p className="mt-4 text-2xl font-bold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{stat.label}</p>
                <p className="mt-1 text-xs text-green-600 dark:text-green-400">{stat.change}</p>
              </div>
            );
          })}
        </div>

        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* My Repositories */}
          <div className="lg:col-span-2 rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
              <h2 className="font-semibold text-gray-900 dark:text-white">My Repositories</h2>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {myRepositories.map((repo) => (
                <Link
                  key={repo.id}
                  href={`/agent/${repo.id}`}
                  className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{repo.name}</p>
                    <div className="mt-1 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <span>{repo.sales} sales</span>
                      <span>{repo.revenue}</span>
                      <span>{repo.activeChats} active chats</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      repo.status === 'active'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                    }`}>
                      {repo.status === 'active' ? 'Active' : 'Pending'}
                    </span>
                    <ArrowRight className="h-4 w-4 text-gray-400" />
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
              <h2 className="font-semibold text-gray-900 dark:text-white">Recent Activity</h2>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="px-6 py-4">
                  <div className="flex items-start justify-between">
                    <p className="text-sm text-gray-900 dark:text-white">{activity.message}</p>
                    {activity.amount && (
                      <span className="ml-2 text-sm font-medium text-green-600 dark:text-green-400">
                        +{activity.amount}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <Clock className="h-3 w-3" />
                    {activity.time}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
