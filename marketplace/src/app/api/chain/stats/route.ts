import { NextResponse } from 'next/server';

const NATLANGCHAIN_URL = process.env.NATLANGCHAIN_URL || 'http://localhost:5000';

export async function GET() {
  try {
    const response = await fetch(`${NATLANGCHAIN_URL}/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch chain stats' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      {
        total_blocks: 0,
        total_entries: 0,
        pending_entries: 0,
        unique_authors: 0,
        validated_entries: 0,
        chain_valid: false,
        latest_block_hash: '',
        error: 'Unable to fetch stats',
      },
      { status: 503 }
    );
  }
}
