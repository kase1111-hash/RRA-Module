import Link from 'next/link';
import { ChevronRight, Shield, CheckCircle, AlertTriangle, Code } from 'lucide-react';

export default function VerificationPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-500">
          <Link href="/docs" className="hover:text-gray-700 dark:hover:text-gray-300">Docs</Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-gray-900 dark:text-white">Code Verification</span>
        </nav>

        <div className="mt-6 flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-100 dark:bg-green-900">
            <Shield className="h-6 w-6 text-green-600 dark:text-green-400" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            Code Verification
          </h1>
        </div>

        <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
          RRA provides multiple layers of verification to ensure code authenticity and ownership.
        </p>

        {/* Verification Levels */}
        <div className="mt-12 space-y-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Verification Levels</h2>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-green-200 bg-green-50 p-6 dark:border-green-800 dark:bg-green-900/20">
              <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
              <h3 className="mt-4 font-semibold text-green-800 dark:text-green-200">Basic</h3>
              <p className="mt-2 text-sm text-green-700 dark:text-green-300">
                Repository ownership verified via GitHub/GitLab OAuth
              </p>
            </div>
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-6 dark:border-blue-800 dark:bg-blue-900/20">
              <Shield className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <h3 className="mt-4 font-semibold text-blue-800 dark:text-blue-200">Enhanced</h3>
              <p className="mt-2 text-sm text-blue-700 dark:text-blue-300">
                Code hash stored on-chain + DID verification
              </p>
            </div>
            <div className="rounded-lg border border-purple-200 bg-purple-50 p-6 dark:border-purple-800 dark:bg-purple-900/20">
              <Code className="h-8 w-8 text-purple-600 dark:text-purple-400" />
              <h3 className="mt-4 font-semibold text-purple-800 dark:text-purple-200">Audited</h3>
              <p className="mt-2 text-sm text-purple-700 dark:text-purple-300">
                Third-party security audit + formal verification
              </p>
            </div>
          </div>
        </div>

        {/* How Verification Works */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">How Verification Works</h2>

          <div className="mt-6 space-y-4">
            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">1. Repository Ownership</h3>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                When you register a repository, we verify you have admin access via OAuth.
                This creates a cryptographic link between your wallet and the repository.
              </p>
              <pre className="mt-4 rounded bg-gray-900 p-4 text-sm text-gray-100">
                <code>{`# Verification creates a signed attestation
{
  "repository": "github.com/you/repo",
  "owner_wallet": "0x1234...5678",
  "verified_at": "2025-01-15T10:30:00Z",
  "signature": "0xabcd..."
}`}</code>
              </pre>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">2. Code Hash Anchoring</h3>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                A hash of your codebase is stored on-chain when you register your IP asset.
                This allows verification that the code hasn&apos;t been tampered with.
              </p>
              <pre className="mt-4 rounded bg-gray-900 p-4 text-sm text-gray-100">
                <code>{`# Code hash stored in IP metadata
rra verify --check-hash
✓ Code hash matches on-chain record
✓ Last verified: 2025-01-15 (commit abc123)`}</code>
              </pre>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">3. License Verification</h3>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                Buyers can verify their license is valid and check the terms on-chain.
              </p>
              <pre className="mt-4 rounded bg-gray-900 p-4 text-sm text-gray-100">
                <code>{`# Verify a license NFT
rra verify-license --token-id 42

License Details:
  Repository: my-awesome-lib
  Tier: Commercial
  Licensee: 0x9876...5432
  Expires: Never
  On-chain: ✓ Verified`}</code>
              </pre>
            </div>
          </div>
        </div>

        {/* Security Warnings */}
        <div className="mt-12 rounded-lg border border-amber-200 bg-amber-50 p-6 dark:border-amber-800 dark:bg-amber-900/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-6 w-6 shrink-0 text-amber-600 dark:text-amber-400" />
            <div>
              <h3 className="font-semibold text-amber-800 dark:text-amber-200">Security Notice</h3>
              <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
                Verification confirms ownership and integrity, but does not guarantee the code
                is free from bugs or vulnerabilities. Always review code before using it in
                production. See our <Link href="/buyer-beware" className="underline">Buyer Beware</Link> page.
              </p>
            </div>
          </div>
        </div>

        {/* Next Steps */}
        <div className="mt-12 flex gap-4">
          <Link
            href="/docs"
            className="rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            ← Back to Docs
          </Link>
          <Link
            href="/docs/api"
            className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white hover:bg-indigo-700"
          >
            API Reference →
          </Link>
        </div>
      </div>
    </div>
  );
}
