import { NextResponse } from 'next/server';
import { processAudio } from '@/utils/audioProcessing';

export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb',
    },
    responseLimit: false,
  },
};

export async function POST(request: Request) {
  try {
    const audioDetails = await request.json();
    
    // Process audio and get S3/CloudFront URL
    const audioUrl = await processAudio(audioDetails.audioBuffer);

    return NextResponse.json({ 
      success: true,
      url: audioUrl,
      expiresIn: 3600 // URL expiration in seconds
    });
  } catch (error) {
    console.error('Error generating final audio:', error);
    return NextResponse.json(
      { error: 'Failed to generate final audio' }, 
      { status: 500 }
    );
  }
}
