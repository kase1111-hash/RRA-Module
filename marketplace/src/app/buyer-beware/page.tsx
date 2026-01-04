import { AlertTriangle, Shield, Search, FileCheck } from 'lucide-react';

export default function BuyerBewarePage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Warning Banner */}
      <div className="bg-amber-50 dark:bg-amber-900/20">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-6 w-6 text-amber-600 dark:text-amber-400" />
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
              Important information for all marketplace users. Please read carefully.
            </p>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">Buyer Beware</h1>
        <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
          RRA Marketplace is a decentralized platform. While we strive to maintain quality,
          users should exercise due diligence when licensing code.
        </p>

        {/* Key Points */}
        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <div className="rounded-xl border border-gray-200 p-6 dark:border-gray-700">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-red-100 dark:bg-red-900/30">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
              No Guarantees
            </h3>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              We do not guarantee that code listed on the marketplace is free from bugs,
              security vulnerabilities, or malicious content.
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 p-6 dark:border-gray-700">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <Search className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
              Do Your Research
            </h3>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              Always review the source code before purchasing a license. Check the repository&apos;s
              history, contributors, and community feedback.
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 p-6 dark:border-gray-700">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
              <Shield className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
              Security Audits
            </h3>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              For production use, consider getting an independent security audit of any code
              you license, especially for financial or security-critical applications.
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 p-6 dark:border-gray-700">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <FileCheck className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
              Verify Ownership
            </h3>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              Confirm that the licensor actually owns or has rights to license the code. Check
              the on-chain IP asset registration and compare with GitHub ownership.
            </p>
          </div>
        </div>

        {/* Detailed Sections */}
        <div className="mt-16 space-y-12">
          <section>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Understanding the Risks
            </h2>
            <div className="mt-4 space-y-4 text-gray-600 dark:text-gray-300">
              <p>
                <strong className="text-gray-900 dark:text-white">Code Quality:</strong> Listings
                are not reviewed for code quality. Some code may be poorly written, unmaintained,
                or incompatible with your use case.
              </p>
              <p>
                <strong className="text-gray-900 dark:text-white">Security Vulnerabilities:</strong> Code
                may contain known or unknown security issues. Always scan for vulnerabilities
                before deploying to production.
              </p>
              <p>
                <strong className="text-gray-900 dark:text-white">License Disputes:</strong> While
                licenses are recorded on-chain, legal interpretation may vary by jurisdiction.
                Consult a lawyer for complex licensing scenarios.
              </p>
              <p>
                <strong className="text-gray-900 dark:text-white">Blockchain Finality:</strong> All
                transactions are final. There are no refunds once a license is minted. Make sure
                you understand what you&apos;re purchasing.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Before You Buy
            </h2>
            <ul className="mt-4 space-y-3 text-gray-600 dark:text-gray-300">
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">1</span>
                <span>Review the complete source code in the linked repository</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">2</span>
                <span>Check the repository&apos;s commit history and recent activity</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">3</span>
                <span>Verify the licensor&apos;s identity matches the repository owner</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">4</span>
                <span>Read all license terms and understand the royalty structure</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">5</span>
                <span>Test the code in a sandbox environment before production use</span>
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Reporting Issues
            </h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              If you discover malicious code, fraudulent listings, or license violations,
              please report them immediately to our team:
            </p>
            <a
              href="mailto:security@rra-marketplace.com"
              className="mt-4 inline-block rounded-lg bg-red-600 px-6 py-3 font-medium text-white hover:bg-red-700"
            >
              Report an Issue
            </a>
          </section>
        </div>
      </div>
    </div>
  );
}
