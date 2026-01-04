import { MapPin, Clock, ArrowRight } from 'lucide-react';

const positions = [
  {
    id: 1,
    title: 'Senior Smart Contract Engineer',
    department: 'Engineering',
    location: 'Remote',
    type: 'Full-time',
    description: 'Build and maintain our Story Protocol integrations and smart contract infrastructure.',
  },
  {
    id: 2,
    title: 'Full Stack Developer',
    department: 'Engineering',
    location: 'Remote',
    type: 'Full-time',
    description: 'Work on our Next.js marketplace and Python-based RRA module.',
  },
  {
    id: 3,
    title: 'AI/ML Engineer',
    department: 'AI',
    location: 'Remote',
    type: 'Full-time',
    description: 'Develop and improve our AI negotiation agents and license recommendation systems.',
  },
  {
    id: 4,
    title: 'Developer Advocate',
    department: 'DevRel',
    location: 'Remote',
    type: 'Full-time',
    description: 'Help developers understand and integrate RRA into their projects.',
  },
];

const perks = [
  'Fully remote team across multiple time zones',
  'Competitive salary + token allocation',
  'Flexible working hours',
  'Latest hardware and software tools',
  'Annual team retreats',
  'Learning & development budget',
];

export default function CareersPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Hero */}
      <div className="bg-gradient-to-b from-indigo-50 to-white px-4 py-20 dark:from-gray-800 dark:to-gray-900">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white sm:text-5xl">
            Join Our Team
          </h1>
          <p className="mt-6 text-lg text-gray-600 dark:text-gray-300">
            Help us build the future of code licensing. We&apos;re looking for passionate
            individuals who want to revolutionize how developers monetize their work.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Open Positions */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Open Positions</h2>
          <div className="mt-8 space-y-4">
            {positions.map((position) => (
              <div
                key={position.id}
                className="group rounded-xl border border-gray-200 bg-white p-6 transition hover:border-indigo-300 hover:shadow-lg dark:border-gray-700 dark:bg-gray-800 dark:hover:border-indigo-600"
              >
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {position.title}
                    </h3>
                    <p className="mt-1 text-gray-600 dark:text-gray-300">{position.description}</p>
                    <div className="mt-3 flex flex-wrap gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        {position.location}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        {position.type}
                      </span>
                      <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
                        {position.department}
                      </span>
                    </div>
                  </div>
                  <button className="flex items-center gap-2 whitespace-nowrap rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white transition hover:bg-indigo-700">
                    Apply Now
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Perks */}
        <div className="mt-20">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Why Join Us?</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {perks.map((perk, index) => (
              <div
                key={index}
                className="flex items-center gap-3 rounded-lg bg-gray-50 p-4 dark:bg-gray-800"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                  <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <span className="text-gray-700 dark:text-gray-300">{perk}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Don't See a Fit */}
        <div className="mt-20 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 p-8 text-center md:p-12">
          <h2 className="text-2xl font-bold text-white">Don&apos;t see a perfect fit?</h2>
          <p className="mt-4 text-lg text-indigo-100">
            We&apos;re always looking for talented people. Send us your resume and tell us
            how you can contribute to RRA.
          </p>
          <a
            href="mailto:careers@rra-marketplace.com"
            className="mt-6 inline-block rounded-lg bg-white px-6 py-3 font-medium text-indigo-600 hover:bg-indigo-50"
          >
            Get in Touch
          </a>
        </div>
      </div>
    </div>
  );
}
