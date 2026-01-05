import { NextResponse } from 'next/server';

const NATLANGCHAIN_URL = process.env.NATLANGCHAIN_URL || 'http://localhost:5000';
const isDev = process.env.NODE_ENV === 'development';

// Story Protocol network configuration
const STORY_NETWORK = {
  name: 'Story Protocol',
  chain: 'Aeneid Testnet',
  chainId: 1315,
  explorer: 'https://aeneid.explorer.story.foundation',
};

export async function GET() {
  // In development, return mock response if no chain is running
  if (isDev && !process.env.NATLANGCHAIN_URL) {
    return NextResponse.json({
      status: 'demo',
      service: 'NatLangChain (Demo Mode)',
      network: STORY_NETWORK,
      blocks: 42,
      pending_entries: 0,
      llm_validation_available: false,
      mock: true,
    });
  }

  try {
    const response = await fetch(`${NATLANGCHAIN_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Short timeout for health check
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Chain unhealthy', status: response.status, network: STORY_NETWORK },
        { status: 503 }
      );
    }

    const data = await response.json();
    return NextResponse.json({ ...data, network: STORY_NETWORK });
  } catch (error) {
    // Return a degraded response when chain is unavailable
    return NextResponse.json(
      {
        status: 'unavailable',
        service: 'NatLangChain API',
        network: STORY_NETWORK,
        blocks: 0,
        pending_entries: 0,
        llm_validation_available: false,
        error: 'Unable to connect to NatLangChain',
      },
      { status: 503 }
    );
  }
}
