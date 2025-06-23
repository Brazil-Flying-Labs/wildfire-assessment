import { NextRequest, NextResponse } from 'next/server';

// Hardcoded valid dates for each area
// In a real implementation, this would fetch from your backend API
const VALID_DATES_BY_AREA: Record<string, string[]> = {
  'test-area4': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'luiz-antonio': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'jatai': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'sao-paulo': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'amazon': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'cerrado': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'pantanal': ['2023-05-01', '2023-05-15', '2023-06-01'],
};

// Default dates to use if no area-specific dates are found
const DEFAULT_VALID_DATES = ['2023-05-01', '2023-05-15'];

export async function GET(request: NextRequest) {
  try {
    // Get the area ID from the query parameters
    const { searchParams } = new URL(request.url);
    const areaId = searchParams.get('areaId');

    // Get the valid dates for the specified area or use default dates
    const validDates = areaId && VALID_DATES_BY_AREA[areaId] 
      ? VALID_DATES_BY_AREA[areaId] 
      : DEFAULT_VALID_DATES;

    // Log for debugging
    console.log(`API: Returning valid dates for area ${areaId}:`, validDates);

    // Return the valid dates as JSON
    return NextResponse.json({ validDates });
  } catch (error) {
    console.error('Error in valid-dates API route:', error);
    return NextResponse.json(
      { error: 'Failed to fetch valid dates', message: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
