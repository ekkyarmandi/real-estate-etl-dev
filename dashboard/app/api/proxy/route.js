import { NextResponse } from 'next/server';

// Enable CORS for OPTIONS requests (preflight)
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const url = searchParams.get('url');

    if (!url) {
      return NextResponse.json({ error: 'URL parameter is required' }, { status: 400 });
    }

    const cf_clearance = 'IuTgTzvUCWM0TKg6x8_ZBNbLVnlahec5ev354.LY8JE-1743848723-1.2.1.1-a0r.mhHSSKBOIWoWim.rFq8KL01FtPMF01noPE02UuUpgEowxrx.uUK6_TO9RJ7lq76.LDrRdRkSX.tbppn3AGLD6AB549cosSgBLI_z8f0Olug9HGN_lf7lG0zQCZrg2X5smF8KQtjJdisUjlLF5NjDWiCbFUUH4UEmSY3Or4ulvd9agWAe5new5Ia7qIn9MzBLz7pDiiasRcEVfQSWRjvEAFxADYOf55MEcr6aJbLU_IPP3k5VQDrnYou5jT4XDrxeP2Cz7jttE_wDnEQjCBawJJxJPr19lc3k6wzmisKdw8lmZEg81bbykXGGqPRDJ6lqaOSfKJiqF_CTU3dnuMAHwf7uCAFQuQUlGzT.ZVR0cK7wfbuLIWSZpVsjcA4y';
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
    });

    const text = await response.text();

    return new NextResponse(text, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'text/html',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json({ error: error.message }, {
      status: 500,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    });
  }
} 