import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import ffmpeg from 'fluent-ffmpeg';
import { promisify } from 'util';
import { exec } from 'child_process';

const execAsync = promisify(exec);

// Helper function to split ttsSpeed into multiple atempo filters
function getAtempoFilters(speed: number): string[] {
  const filters: string[] = [];
  
  // Limit the speed to a maximum of 4.0 and minimum of 0.5
  speed = Math.min(Math.max(speed, 0.5), 4.0);
  
  // Handle speed greater than 2.0
  while (speed > 2.0) {
    filters.push('atempo=2.0');
    speed /= 2.0;
  }
  
  // Handle speed less than 0.5
  while (speed < 0.5) {
    filters.push('atempo=0.5');
    speed /= 0.5;
  }
  
  // Add the remaining atempo filter if speed is not exactly 1.0
  if (speed !== 1.0) {
    filters.push(`atempo=${speed.toFixed(2)}`);
  }
  
  return filters;
}

export async function POST(request: Request) {
  try {
    const { 
      ttsAudioUrl, 
      selectedBackingTrack, 
      ttsVolume, 
      backingTrackVolume, 
      trackDuration, 
      ttsSpeed,
      ttsDuration
    } = await request.json();

    console.log('Received parameters for audio mixing:', {
      ttsAudioUrl: ttsAudioUrl ? 'present' : 'missing',
      selectedBackingTrack: selectedBackingTrack ? 'present' : 'missing',
      ttsVolume,
      backingTrackVolume,
      trackDuration,
      ttsSpeed,
      ttsDuration
    });

    // Validate parameters
    if (
      !ttsAudioUrl || typeof ttsAudioUrl !== 'string' || 
      !selectedBackingTrack || typeof selectedBackingTrack !== 'string' || 
      typeof ttsVolume !== 'number' || 
      typeof backingTrackVolume !== 'number' || 
      typeof trackDuration !== 'number' || 
      typeof ttsSpeed !== 'number' || 
      typeof ttsDuration !== 'number'
    ) {
      console.error('Invalid parameters:', { 
        ttsAudioUrl: typeof ttsAudioUrl, 
        selectedBackingTrack: typeof selectedBackingTrack, 
        ttsVolume: typeof ttsVolume, 
        backingTrackVolume: typeof backingTrackVolume, 
        trackDuration: typeof trackDuration, 
        ttsSpeed: typeof ttsSpeed, 
        ttsDuration: typeof ttsDuration 
      });
      throw new Error('Invalid or missing audio parameters.');
    }

    // Additional validations
    if (ttsSpeed < 0.5 || ttsSpeed > 4.0) {
      throw new Error('TTS speed must be between 0.5x and 4.0x.');
    }

    if (ttsDuration > trackDuration) {
      throw new Error('TTS duration cannot exceed track duration.');
    }

    // Download or decode audio files
    const ttsAudioPath = await saveBase64Audio(ttsAudioUrl, 'tts');
    const backingTrackPath = await downloadAudio(selectedBackingTrack, 'backing');

    // Mix audio using ffmpeg
    const outputPath = path.join(os.tmpdir(), `combined_${Date.now()}.mp3`);
    await mixAudio(ttsAudioPath, backingTrackPath, ttsVolume, backingTrackVolume, trackDuration, ttsSpeed, ttsDuration, outputPath);

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
        'Content-Disposition': `attachment; filename="affirmation_audio_${Math.floor(trackDuration / 60)}min.mp3"`,
      },
    });
  } catch (error) {
    console.error('Error in combine-audio:', error);
    return NextResponse.json({ error: (error as Error).message || 'An error occurred while combining audio.' }, { status: 500 });
  }
}

async function saveBase64Audio(base64Url: string, prefix: string): Promise<string> {
  const base64Data = base64Url.split(',')[1];
  if (!base64Data) {
    throw new Error('Invalid base64 audio data.');
  }
  const buffer = Buffer.from(base64Data, 'base64');
  const tempPath = path.join(os.tmpdir(), `${prefix}_${Date.now()}.mp3`);
  await fs.writeFile(tempPath, buffer);
  return tempPath;
}

async function downloadAudio(url: string, prefix: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to fetch ${prefix} audio.`);
  const buffer = await response.arrayBuffer();
  const tempPath = path.join(os.tmpdir(), `${prefix}_${Date.now()}.mp3`);
  await fs.writeFile(tempPath, Buffer.from(buffer));
  return tempPath;
}

async function mixAudio(
  ttsPath: string, 
  backingPath: string, 
  ttsVolume: number, 
  backingTrackVolume: number, 
  trackDuration: number, 
  ttsSpeed: number,
  ttsDuration: number,
  outputPath: string
): Promise<void> {
  console.log('Mixing audio with parameters:', {
    ttsVolume,
    backingTrackVolume,
    trackDuration,
    ttsSpeed,
    ttsDuration
  });

  const atempoFilters = getAtempoFilters(ttsSpeed).join(',');

  // Calculate the number of times to loop the TTS audio
  const loopCount = Math.ceil(trackDuration / ttsDuration);

  // Updated FFmpeg command to correctly handle quotes in filter_complex
  const command = `ffmpeg -i "${ttsPath}" -stream_loop -1 -i "${backingPath}" -filter_complex "[0:a]${atempoFilters},volume=${ttsVolume},aloop=loop=${loopCount}:size=${Math.floor(ttsDuration * 44100)}[a];[1:a]volume=${backingTrackVolume}[b];[a][b]amix=inputs=2:duration=first:dropout_transition=2,asetpts=PTS-STARTPTS" -t ${trackDuration} "${outputPath}"`;

  try {
    const { stdout, stderr } = await execAsync(command);
    console.log('FFmpeg stdout:', stdout);
    console.log('FFmpeg stderr:', stderr);
  } catch (error) {
    console.error('Error during FFmpeg processing:', error);
    throw error;
  }
}
