import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
  title: 'RRA Marketplace - License Code with AI Agents',
  description:
    'Discover and license code repositories with AI-powered license advisors. Blockchain-enforced licensing for the modern developer.',
  keywords: ['code licensing', 'AI agents', 'blockchain', 'NFT licenses', 'GitHub'],
  openGraph: {
    title: 'RRA Marketplace',
    description: 'AI-powered code licensing marketplace',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans">
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
