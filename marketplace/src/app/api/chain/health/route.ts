import { NextResponse } from 'next/server';

const NATLANGCHAIN_URL = process.env.NATLANGCHAIN_URL || 'http://localhost:5000';

export async function GET() {
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
        { error: 'Chain unhealthy', status: response.status },
        { status: 503 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    // Return a degraded response when chain is unavailable
    return NextResponse.json(
      {
        status: 'unavailable',
        service: 'NatLangChain API',
        blocks: 0,
        pending_entries: 0,
        llm_validation_available: false,
        error: 'Unable to connect to NatLangChain',
      },
      { status: 503 }
    );
  }
}
