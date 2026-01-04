# RRA Marketplace Frontend

A Next.js 14 web application for the RRA Module marketplace - discover and license code repositories with AI-powered license advisors.

## Features

- **Repository Discovery**: Browse and search repositories with filtering
- **AI License Advisors**: Chat with AI agents to find the right license for your needs
- **Wallet Integration**: Connect wallet via RainbowKit (MetaMask, WalletConnect)
- **License Purchase**: Complete transactions and receive NFT licenses

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **Web3**: wagmi v2, viem, RainbowKit
- **State**: React Query (TanStack Query)

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- RRA Module API running on `localhost:8000`

### Installation

```bash
# Navigate to marketplace directory
cd marketplace

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm run dev
```

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
```

## Project Structure

```
marketplace/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx            # Homepage
│   │   ├── layout.tsx          # Root layout
│   │   ├── providers.tsx       # React providers
│   │   ├── globals.css         # Global styles
│   │   ├── agent/[id]/         # Agent detail page
│   │   └── search/             # Search page
│   ├── components/             # React components
│   │   ├── Header.tsx          # Navigation header
│   │   ├── Footer.tsx          # Site footer
│   │   ├── AgentCard.tsx       # Repository card
│   │   ├── NegotiationChat.tsx # License chat interface
│   │   └── SearchBar.tsx       # Search with filters
│   ├── lib/                    # Utilities and API client
│   │   ├── api.ts              # API client functions
│   │   └── utils.ts            # Helper utilities
│   ├── hooks/                  # Custom React hooks
│   └── types/                  # TypeScript types
│       └── index.ts            # Type definitions
├── public/                     # Static assets
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── next.config.js
```

## Pages

### Homepage (`/`)
- Hero section with search
- Featured repositories
- Feature highlights
- CTA for listing repos

### Search (`/search`)
- Full search with filters
- Language filtering
- Price range
- Sort options
- Paginated results

### Agent Detail (`/agent/[id]`)
- Repository information
- License tiers
- Statistics and reputation
- AI license advisor chat

## API Integration

The frontend connects to the RRA Module API:

```typescript
// List marketplace repos
GET /api/marketplace/repos?q=search&language=python

// Get agent details
GET /api/marketplace/agent/{repo_id}/details

// WebSocket chat
WS /ws/chat/{repo_id}
```

## Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linting
npm run lint
```

## Deployment

### Vercel (Recommended)

1. Push to GitHub
2. Import to Vercel
3. Configure environment variables
4. Deploy

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## License

FSL-1.1-ALv2 - See [LICENSE.md](../LICENSE.md)

Copyright 2025 Kase Branham
