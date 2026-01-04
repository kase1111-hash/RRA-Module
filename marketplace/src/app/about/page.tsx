import { Code2, Shield, Coins, Users } from 'lucide-react';

const values = [
  {
    icon: Code2,
    title: 'Open Source First',
    description: 'We believe in the power of open source. RRA is built on transparent, auditable code that anyone can verify.',
  },
  {
    icon: Shield,
    title: 'Creator Rights',
    description: 'Creators deserve fair compensation. Our on-chain licensing ensures automatic royalty distribution.',
  },
  {
    icon: Coins,
    title: 'Programmable IP',
    description: 'Built on Story Protocol, RRA enables programmable intellectual property with enforceable terms.',
  },
  {
    icon: Users,
    title: 'Community Driven',
    description: 'Governed by the community. Token holders can vote on protocol upgrades and fee structures.',
  },
];

const team = [
  {
    name: 'Kase Branham',
    role: 'Founder & Lead Developer',
    bio: 'Building the future of programmable IP licensing.',
  },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Hero */}
      <div className="bg-gradient-to-b from-indigo-50 to-white px-4 py-20 dark:from-gray-800 dark:to-gray-900">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-5xl">
            Autonomous Code Licensing
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-600 dark:text-gray-300">
            RRA (Revenant Repo Agent) is revolutionizing how code is licensed and monetized.
            We connect developers with AI license advisors that help buyers find the right license
            and complete purchases, with on-chain royalty enforcement.
          </p>
        </div>
      </div>

      {/* Mission */}
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Our Mission</h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            To create a fair, transparent, and automated marketplace where code creators
            can monetize their work while users get clear licensing terms backed by
            blockchain technology.
          </p>
        </div>

        {/* Values */}
        <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {values.map((value) => (
            <div key={value.title} className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-900">
                <value.icon className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                {value.title}
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                {value.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* How It Works */}
      <div className="bg-gray-50 px-4 py-16 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl">
          <h2 className="text-center text-3xl font-bold text-gray-900 dark:text-white">
            How It Works
          </h2>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            <div className="rounded-lg bg-white p-6 shadow dark:bg-gray-900">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-white font-bold">
                1
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                Register Your Repo
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                Run <code className="rounded bg-gray-100 px-1 dark:bg-gray-800">rra init</code> to
                create a .market.yaml and register your repository as an IP asset on Story Protocol.
              </p>
            </div>
            <div className="rounded-lg bg-white p-6 shadow dark:bg-gray-900">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-white font-bold">
                2
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                Set License Terms
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                Define pricing tiers, royalty rates, and usage terms. Your AI agent will guide
                buyers through selecting the right option.
              </p>
            </div>
            <div className="rounded-lg bg-white p-6 shadow dark:bg-gray-900">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-white font-bold">
                3
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                Earn Royalties
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                When users license your code or create derivatives, royalties are automatically
                distributed to your wallet via Story Protocol.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Team */}
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <h2 className="text-center text-3xl font-bold text-gray-900 dark:text-white">Team</h2>
        <div className="mt-12 flex justify-center">
          {team.map((member) => (
            <div key={member.name} className="text-center">
              <div className="mx-auto h-24 w-24 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500" />
              <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                {member.name}
              </h3>
              <p className="text-sm text-indigo-600 dark:text-indigo-400">{member.role}</p>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{member.bio}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="bg-indigo-600 px-4 py-16">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-3xl font-bold text-white">Ready to Get Started?</h2>
          <p className="mt-4 text-lg text-indigo-100">
            Join hundreds of developers already using RRA to monetize their code.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <a
              href="/docs/quickstart"
              className="rounded-lg bg-white px-6 py-3 font-medium text-indigo-600 hover:bg-indigo-50"
            >
              Read the Docs
            </a>
            <a
              href="/search"
              className="rounded-lg border border-white px-6 py-3 font-medium text-white hover:bg-indigo-700"
            >
              Explore Marketplace
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
