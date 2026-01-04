export default function TermsPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">Terms of Service</h1>
        <p className="mt-4 text-gray-600 dark:text-gray-300">
          Last updated: January 15, 2025
        </p>

        <div className="prose prose-indigo mt-8 max-w-none dark:prose-invert">
          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">1. Acceptance of Terms</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              By accessing or using the RRA Marketplace, you agree to be bound by these Terms of
              Service. If you do not agree to these terms, do not use our services.
            </p>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">2. Description of Service</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              RRA Marketplace provides a platform for:
            </p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>Registering code repositories as IP assets on Story Protocol</li>
              <li>Discovering and licensing code from other developers</li>
              <li>AI-powered license selection and purchase assistance</li>
              <li>On-chain royalty collection and distribution</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">3. User Responsibilities</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">You agree to:</p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>Only list code that you own or have rights to license</li>
              <li>Provide accurate information about your repositories</li>
              <li>Honor licensing terms you set for your code</li>
              <li>Comply with all applicable laws and regulations</li>
              <li>Not use the platform for illegal activities</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">4. Licensing Terms</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              When you purchase a license through RRA Marketplace:
            </p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>You receive an on-chain license NFT as proof of purchase</li>
              <li>License terms are defined by the code owner and enforced via smart contracts</li>
              <li>Royalties are automatically distributed according to the license terms</li>
              <li>All transactions are final and recorded on the blockchain</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">5. Fees</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              RRA Marketplace may charge fees for certain services. Current fee structure:
            </p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>Platform fee: 2.5% of license transactions</li>
              <li>Gas fees: Paid by the user initiating the transaction</li>
              <li>Royalty processing: No additional fee</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">6. Intellectual Property</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              Code owners retain all intellectual property rights to their code. RRA Marketplace
              does not claim ownership of any user-submitted content. By listing code on our
              platform, you grant us a license to display and index your repository information.
            </p>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">7. Disclaimers</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              THE SERVICE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTIES OF ANY KIND. We do not guarantee:
            </p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>The quality or functionality of listed code</li>
              <li>Continuous, uninterrupted access to the platform</li>
              <li>That listed code is free from bugs or security vulnerabilities</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">8. Limitation of Liability</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              To the maximum extent permitted by law, RRA Marketplace shall not be liable for any
              indirect, incidental, special, consequential, or punitive damages arising from your
              use of the service.
            </p>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">9. Changes to Terms</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              We may update these terms from time to time. Continued use of the platform after
              changes constitutes acceptance of the new terms.
            </p>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">10. Contact</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              For questions about these terms, contact us at:{' '}
              <a href="mailto:legal@rra-marketplace.com" className="text-indigo-600 hover:underline dark:text-indigo-400">
                legal@rra-marketplace.com
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
