'use client';

import { useState } from 'react';
import { Copy, Check, ChevronRight } from 'lucide-react';

const endpoints = [
  {
    method: 'GET',
    path: '/api/agents',
    description: 'List all available agents',
    response: `{
  "agents": [
    {
      "id": "agent-123",
      "name": "MyProject",
      "owner": "0x1234...5678",
      "ipAssetId": "0xabcd...efgh",
      "tiers": ["personal", "commercial", "enterprise"]
    }
  ],
  "total": 1,
  "page": 1
}`,
  },
  {
    method: 'GET',
    path: '/api/agents/:id',
    description: 'Get agent details by ID',
    response: `{
  "id": "agent-123",
  "name": "MyProject",
  "description": "A sample project",
  "owner": "0x1234...5678",
  "ipAssetId": "0xabcd...efgh",
  "royaltyVault": "0x9876...5432",
  "tiers": {
    "personal": { "price": "0.01", "currency": "WIP" },
    "commercial": { "price": "0.1", "currency": "WIP" }
  }
}`,
  },
  {
    method: 'POST',
    path: '/api/licenses/mint',
    description: 'Mint a new license NFT',
    body: `{
  "agentId": "agent-123",
  "tier": "commercial",
  "licensorIpId": "0xabcd...efgh",
  "receiver": "0x1234...5678"
}`,
    response: `{
  "success": true,
  "licenseId": "license-456",
  "transactionHash": "0xdef0...1234",
  "tokenId": 42
}`,
  },
  {
    method: 'GET',
    path: '/api/royalties/:ipAssetId',
    description: 'Get royalty balance for an IP asset',
    response: `{
  "ipAssetId": "0xabcd...efgh",
  "vault": "0x9876...5432",
  "balances": {
    "WIP": "1.5",
    "claimable": "1.2"
  }
}`,
  },
  {
    method: 'POST',
    path: '/api/royalties/claim',
    description: 'Claim accumulated royalties',
    body: `{
  "ipAssetId": "0xabcd...efgh",
  "tokens": ["0x1514...0000"]
}`,
    response: `{
  "success": true,
  "claimed": "1.2",
  "currency": "WIP",
  "transactionHash": "0xabc1...2345"
}`,
  },
];

function CodeBlock({ code, language = 'json' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative">
      <button
        onClick={handleCopy}
        className="absolute right-2 top-2 rounded bg-gray-700 p-1.5 text-gray-300 hover:bg-gray-600"
      >
        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      </button>
      <pre className="overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    POST: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    PUT: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    DELETE: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  };

  return (
    <span className={`rounded px-2 py-1 text-xs font-bold ${colors[method] || 'bg-gray-100 text-gray-700'}`}>
      {method}
    </span>
  );
}

export default function ApiReferencePage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div>
          <nav className="flex items-center gap-2 text-sm text-gray-500">
            <a href="/docs" className="hover:text-gray-700 dark:hover:text-gray-300">Docs</a>
            <ChevronRight className="h-4 w-4" />
            <span className="text-gray-900 dark:text-white">API Reference</span>
          </nav>
          <h1 className="mt-4 text-4xl font-bold text-gray-900 dark:text-white">
            API Reference
          </h1>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            Complete API documentation for integrating with the RRA marketplace.
          </p>
        </div>

        {/* Base URL */}
        <div className="mt-8 rounded-lg bg-white p-6 shadow dark:bg-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Base URL</h2>
          <CodeBlock code="https://api.rra-marketplace.com/v1" />
          <p className="mt-4 text-sm text-gray-600 dark:text-gray-300">
            All API requests should be made to this base URL. Authentication is required for
            write operations using a Bearer token.
          </p>
        </div>

        {/* Authentication */}
        <div className="mt-8 rounded-lg bg-white p-6 shadow dark:bg-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Authentication</h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
            For write operations, include your API key in the Authorization header:
          </p>
          <CodeBlock
            code={`curl -X POST https://api.rra-marketplace.com/v1/licenses/mint \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"agentId": "agent-123", "tier": "commercial"}'`}
            language="bash"
          />
        </div>

        {/* Endpoints */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Endpoints</h2>

          <div className="mt-6 space-y-8">
            {endpoints.map((endpoint, index) => (
              <div key={index} className="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
                <div className="flex items-center gap-3">
                  <MethodBadge method={endpoint.method} />
                  <code className="text-lg font-mono text-gray-900 dark:text-white">
                    {endpoint.path}
                  </code>
                </div>
                <p className="mt-2 text-gray-600 dark:text-gray-300">{endpoint.description}</p>

                {endpoint.body && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Request Body</h4>
                    <div className="mt-2">
                      <CodeBlock code={endpoint.body} />
                    </div>
                  </div>
                )}

                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Response</h4>
                  <div className="mt-2">
                    <CodeBlock code={endpoint.response} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SDKs */}
        <div className="mt-12 rounded-lg bg-indigo-50 p-6 dark:bg-indigo-900/20">
          <h2 className="text-lg font-semibold text-indigo-900 dark:text-indigo-100">SDKs & Libraries</h2>
          <p className="mt-2 text-sm text-indigo-700 dark:text-indigo-300">
            We provide official SDKs for popular languages:
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm text-indigo-700 dark:bg-indigo-800 dark:text-indigo-200">
              JavaScript/TypeScript
            </span>
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm text-indigo-700 dark:bg-indigo-800 dark:text-indigo-200">
              Python
            </span>
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm text-indigo-700 dark:bg-indigo-800 dark:text-indigo-200">
              Go
            </span>
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm text-indigo-700 dark:bg-indigo-800 dark:text-indigo-200">
              Rust
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
