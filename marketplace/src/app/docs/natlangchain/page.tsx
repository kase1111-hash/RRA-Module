import Link from 'next/link';
import { ChevronRight, Cpu, MessageSquare, Zap } from 'lucide-react';

export default function NatLangChainPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-500">
          <Link href="/docs" className="hover:text-gray-700 dark:hover:text-gray-300">Docs</Link>
          <ChevronRight className="h-4 w-4" />
          <Link href="/docs/integration" className="hover:text-gray-700 dark:hover:text-gray-300">Integration</Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-gray-900 dark:text-white">NatLangChain</span>
        </nav>

        <div className="mt-6 flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-100 dark:bg-purple-900">
            <Cpu className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            NatLangChain Integration
          </h1>
        </div>

        <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
          NatLangChain powers the AI negotiation agents in RRA. It provides natural language
          understanding for license discussions and autonomous deal execution.
        </p>

        {/* What is NatLangChain */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">What is NatLangChain?</h2>
          <p className="mt-4 text-gray-600 dark:text-gray-300">
            NatLangChain is a specialized blockchain that validates AI-generated content and
            enables trustless AI agent interactions. In the context of RRA:
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <MessageSquare className="h-8 w-8 text-purple-600 dark:text-purple-400" />
              <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">AI Negotiation</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Natural language discussions about licensing terms, pricing, and usage rights.
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <Zap className="h-8 w-8 text-purple-600 dark:text-purple-400" />
              <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">Validation</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                LLM responses are validated on-chain to prevent manipulation or hallucination.
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <Cpu className="h-8 w-8 text-purple-600 dark:text-purple-400" />
              <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">Execution</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Agents can autonomously execute licensing transactions when terms are agreed.
              </p>
            </div>
          </div>
        </div>

        {/* Configuration */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Configuration</h2>
          <p className="mt-4 text-gray-600 dark:text-gray-300">
            Configure NatLangChain integration in your <code className="rounded bg-gray-200 px-1 dark:bg-gray-700">.market.yaml</code>:
          </p>
          <pre className="mt-4 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
            <code>{`# .market.yaml
agent:
  negotiation_enabled: true
  llm_provider: "natlangchain"  # or "openai", "anthropic"

  # Negotiation parameters
  max_discount: 10          # Max discount agent can offer
  auto_approve_threshold: "0.5"  # Auto-approve deals under this price
  response_style: "professional"  # or "friendly", "technical"

  # NatLangChain specific
  natlangchain:
    validation_level: "standard"  # or "strict", "relaxed"
    require_consensus: true       # Require multi-node validation`}</code>
          </pre>
        </div>

        {/* API Usage */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">API Usage</h2>
          <pre className="mt-4 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
            <code>{`// Send a message to the negotiation agent
const response = await fetch('/api/agent/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    agentId: 'my-repo-agent',
    message: 'I need a commercial license for a team of 5',
    sessionId: 'session-123'
  })
});

const { reply, suggestedAction } = await response.json();
// reply: "For a team of 5, I recommend our Commercial tier..."
// suggestedAction: { type: 'purchase', tier: 'commercial', price: '0.1' }`}</code>
          </pre>
        </div>

        {/* Health Check */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Health Check</h2>
          <p className="mt-4 text-gray-600 dark:text-gray-300">
            Check if NatLangChain is available:
          </p>
          <pre className="mt-4 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
            <code>{`curl http://localhost:3000/api/chain/health

{
  "status": "healthy",
  "service": "NatLangChain API",
  "blocks": 42,
  "pending_entries": 0,
  "llm_validation_available": true
}`}</code>
          </pre>
        </div>

        {/* Next Steps */}
        <div className="mt-12 flex gap-4">
          <Link
            href="/docs/api"
            className="rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            ← API Reference
          </Link>
          <Link
            href="/docs/webhooks"
            className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white hover:bg-indigo-700"
          >
            Webhooks →
          </Link>
        </div>
      </div>
    </div>
  );
}
