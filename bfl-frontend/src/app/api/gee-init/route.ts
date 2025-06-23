import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// This endpoint provides a way to initialize the GEE API with proper authentication
export async function GET() {
  try {
    // In production, you would use environment variables or a secure secret manager
    const serviceAccountPath = path.join(process.cwd(), 'ee-chandlerbfl-b02ecee40f7a (1).json');
    
    if (!fs.existsSync(serviceAccountPath)) {
      return NextResponse.json(
        { error: 'Service account file not found' },
        { status: 404 }
      );
    }
    
    // Read the service account file
    const serviceAccountJson = JSON.parse(fs.readFileSync(serviceAccountPath, 'utf8'));
    
    // Return only the necessary information for client-side initialization
    // Important: We're not returning the private key
    return NextResponse.json({
      success: true,
      clientId: serviceAccountJson.client_email,
      projectId: serviceAccountJson.project_id,
      // Include instructions for the frontend
      instructions: "Use ee.data.authenticateViaOauth() for client-side authentication"
    });
    
  } catch (error) {
    console.error('Error in GEE init route:', error);
    return NextResponse.json(
      { error: 'Failed to initialize GEE' },
      { status: 500 }
    );
  }
}
