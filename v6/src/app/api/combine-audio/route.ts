import { NextRequest, NextResponse } from 'next/server';
import { combineAudioFiles } from '@/utils/ffmpeg';

export const config = {
  maxDuration: 300
};

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const files = formData.getAll('files') as File[];

    if (!files || files.length === 0) {
      return NextResponse.json(
        { error: 'No audio files provided' },
        { status: 400 }
      );
    }

    // Convert Files to Buffers
    const buffers = await Promise.all(
      files.map(async (file) => {
        const arrayBuffer = await file.arrayBuffer();
        return Buffer.from(arrayBuffer);
      })
    );

    // Combine audio files
    const combinedBuffer = await combineAudioFiles(buffers);

    return new NextResponse(combinedBuffer, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Disposition': 'attachment; filename="combined.mp3"'
      }
    });
  } catch (error) {
    console.error('Error processing audio:', error);
    return NextResponse.json(
      { error: 'Error processing audio files' },
      { status: 500 }
    );
  }
}
