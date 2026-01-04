export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">Privacy Policy</h1>
        <p className="mt-4 text-gray-600 dark:text-gray-300">
          Last updated: January 15, 2025
        </p>

        <div className="prose prose-indigo mt-8 max-w-none dark:prose-invert">
          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">1. Introduction</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              RRA Module (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) respects your privacy and is committed to protecting
              your personal data. This privacy policy explains how we collect, use, and safeguard
              your information when you use our marketplace and related services.
            </p>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">2. Information We Collect</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">We collect the following types of information:</p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li><strong>Wallet Addresses:</strong> When you connect your Ethereum wallet, we store your public wallet address.</li>
              <li><strong>Transaction Data:</strong> All licensing transactions are recorded on the blockchain and are publicly visible.</li>
              <li><strong>Repository Information:</strong> When you register a repository, we index public information including repo name, description, and license terms.</li>
              <li><strong>Usage Data:</strong> We collect anonymous analytics about how you use the marketplace.</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">3. How We Use Your Information</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">We use collected information to:</p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>Process licensing transactions and royalty payments</li>
              <li>Display your listed repositories on the marketplace</li>
              <li>Provide customer support</li>
              <li>Improve our services and user experience</li>
              <li>Comply with legal obligations</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">4. Blockchain Data</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              Please note that transactions on the Story Protocol blockchain are permanent and publicly
              visible. This includes license purchases, royalty payments, and IP asset registrations.
              We cannot delete or modify blockchain data.
            </p>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">5. Data Sharing</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              We do not sell your personal data. We may share information with:
            </p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>Service providers who help us operate the marketplace</li>
              <li>Law enforcement when required by law</li>
              <li>Other users (public repository information only)</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">6. Your Rights</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">You have the right to:</p>
            <ul className="mt-4 list-disc pl-6 text-gray-600 dark:text-gray-300">
              <li>Access the personal data we hold about you</li>
              <li>Request correction of inaccurate data</li>
              <li>Request deletion of your data (except blockchain records)</li>
              <li>Opt out of marketing communications</li>
            </ul>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">7. Cookies</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              We use essential cookies to maintain your session and preferences. We do not use
              tracking cookies for advertising purposes.
            </p>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">8. Contact Us</h2>
            <p className="mt-4 text-gray-600 dark:text-gray-300">
              For privacy-related questions, contact us at:{' '}
              <a href="mailto:privacy@rra-marketplace.com" className="text-indigo-600 hover:underline dark:text-indigo-400">
                privacy@rra-marketplace.com
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
