import { NextResponse } from 'next/server';
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { Readable } from 'stream';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

const execAsync = promisify(exec);

const s3Client = new S3Client({
  region: process.env.AWS_REGION!,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

export async function POST(request: Request) {
  try {
    const { ttsAudioUrl, backingTrackUrl, ttsVolume, backingTrackVolume, trackDuration } = await request.json();

    // Download TTS audio and backing track
    const ttsAudioPath = await downloadAudio(ttsAudioUrl, 'tts');
    const backingTrackPath = await downloadAudio(backingTrackUrl, 'backing');

    // Mix audio using ffmpeg
    const outputPath = path.join(os.tmpdir(), `mixed_audio_${Date.now()}.mp3`);
    await mixAudio(ttsAudioPath, backingTrackPath, ttsVolume, backingTrackVolume, trackDuration, outputPath);

    // Read the mixed audio file
    const mixedAudioBuffer = await fs.readFile(outputPath);

    // Clean up temporary files
    await Promise.all([
      fs.unlink(ttsAudioPath),
      fs.unlink(backingTrackPath),
      fs.unlink(outputPath)
    ]);

    // Return the mixed audio as a blob
    return new NextResponse(mixedAudioBuffer, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Disposition': `attachment; filename="mixed_audio_${Math.floor(trackDuration / 60)}min.mp3"`,
      },
    });
  } catch (error) {
    console.error('Error in mix-audio:', error);
    return NextResponse.json({ error: 'An error occurred while mixing audio' }, { status: 500 });
  }
}

async function downloadAudio(url: string, prefix: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to fetch ${prefix} audio`);
  const buffer = await response.arrayBuffer();
  const tempPath = path.join(os.tmpdir(), `${prefix}_${Date.now()}.mp3`);
  await fs.writeFile(tempPath, Buffer.from(buffer));
  return tempPath;
}

async function mixAudio(ttsPath: string, backingPath: string, ttsVolume: number, backingVolume: number, duration: number, outputPath: string) {
  const command = `ffmpeg -i "${ttsPath}" -i "${backingPath}" -filter_complex "[0:a]aloop=loop=-1:size=${duration}s[a];[a]volume=${ttsVolume}[a1];[1:a]volume=${backingVolume}[a2];[a1][a2]amix=inputs=2:duration=longest" -t ${duration} "${outputPath}"`;
  await execAsync(command);
}