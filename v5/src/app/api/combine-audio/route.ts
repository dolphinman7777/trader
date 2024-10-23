import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { promisify } from 'util';
import { exec } from 'child_process';
import { PollyClient, SynthesizeSpeechCommand, Engine, LanguageCode, OutputFormat, TextType, VoiceId } from "@aws-sdk/client-polly";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const execAsync = promisify(exec);

const polly = new PollyClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

const s3Client = new S3Client({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

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
      text, 
      selectedBackingTrack, 
      ttsVolume, 
      backingTrackVolume, 
      trackDuration: requestTrackDuration, // Rename here to avoid conflict
      ttsSpeed,
      ttsDuration
    } = await request.json();

    console.log('Received parameters for audio mixing:', {
      text: text ? `${text.substring(0, 50)}...` : 'missing',
      selectedBackingTrack: selectedBackingTrack ? (typeof selectedBackingTrack === 'string' ? 'present' : 'invalid type') : 'missing',
      ttsVolume,
      backingTrackVolume,
      trackDuration: requestTrackDuration, // Use the renamed variable
      ttsSpeed,
      ttsDuration
    });

    // Validate parameters
    if (
      !text || typeof text !== 'string' || 
      !selectedBackingTrack || typeof selectedBackingTrack !== 'string' || 
      typeof ttsVolume !== 'number' || 
      typeof backingTrackVolume !== 'number' || 
      typeof requestTrackDuration !== 'number' || // Add the missing '||' here
      typeof ttsSpeed !== 'number' || 
      typeof ttsDuration !== 'number'
    ) {
      console.error('Invalid parameters:', { 
        text: typeof text, 
        selectedBackingTrack: typeof selectedBackingTrack, 
        ttsVolume: typeof ttsVolume, 
        backingTrackVolume: typeof backingTrackVolume, 
        trackDuration: typeof requestTrackDuration, // Use the renamed variable
        ttsSpeed: typeof ttsSpeed, 
        ttsDuration: typeof ttsDuration 
      });
      return NextResponse.json({ error: 'Invalid or missing audio parameters.' }, { status: 400 });
    }

    // Additional validations
    if (ttsSpeed < 0.5 || ttsSpeed > 4.0) {
      throw new Error('TTS speed must be between 0.5x and 4.0x.');
    }

    if (ttsDuration > requestTrackDuration) {
      throw new Error('TTS duration cannot exceed track duration.');
    }

    const textToGenerate = text.repeat(Math.ceil(900 / ttsDuration)); // Repeat the text to ensure enough duration
    let ttsAudioUrl: string;
    if (text.startsWith('data:audio')) {
      console.log('TTS audio already provided, skipping generation...');
      ttsAudioUrl = text;
    } else {
      console.log('Generating TTS audio...');
      ttsAudioUrl = await generatePollyTTS(textToGenerate); // Generate TTS audio with the repeated text
    }
    console.log('TTS audio URL:', ttsAudioUrl);

    console.log('Downloading TTS audio...');
    const ttsAudioPath = await downloadAudio(ttsAudioUrl, 'tts');
    console.log('TTS audio downloaded:', ttsAudioPath);

    console.log('Downloading backing track...');
    let backingTrackPath: string;
    if (selectedBackingTrack === 'present') {
      // Handle the case where no backing track is selected
      backingTrackPath = path.join(os.tmpdir(), 'silent.mp3');
      // Create a silent audio file (you may need to implement this)
      await createSilentAudio(backingTrackPath, requestTrackDuration);
    } else {
      backingTrackPath = await downloadAudio(selectedBackingTrack, 'backing');
    }
    console.log('Backing track downloaded:', backingTrackPath);

    console.log('Mixing audio...');
    const outputPath = path.join(os.tmpdir(), `combined_${Date.now()}.mp3`);
    const mixAudio = async (
        ttsPath: string,
        backingPath: string,
        ttsVolume: number,
        backingTrackVolume: number,
        trackDuration: number, // Ensure this is used correctly
        ttsSpeed: number,
        ttsDuration: number,
        outputPath: string
    ): Promise<void> => {
        console.log('Mixing audio with parameters:', {
            ttsVolume,
            backingTrackVolume,
            trackDuration,
            ttsSpeed,
            ttsDuration
        });

        const ttsVolumeDb = Math.log10(ttsVolume) * 20; // Convert to dB
        const backingVolumeDb = Math.log10(backingTrackVolume) * 20; // Convert to dB

        const atempoFilters = getAtempoFilters(ttsSpeed);
        
        // Ensure atempoFilters is not empty
        const atempoFilterString = atempoFilters.length > 0 ? atempoFilters.join(',') + ',' : '';

        // Calculate the number of loops needed to reach the desired track duration
        const loopCount = Math.ceil(trackDuration / (ttsDuration / ttsSpeed));

        const command = [
          'ffmpeg',
          '-i', `"${ttsPath}"`,
          '-stream_loop', '-1',
          '-i', `"${backingPath}"`,
          '-filter_complex',
          `"[0:a]${atempoFilterString}volume=${ttsVolumeDb}dB,aloop=loop=${loopCount}:size=${Math.floor(ttsDuration * 48000)}[a];` +
          `[1:a]volume=${backingVolumeDb}dB[b];` +
          `[a][b]amix=inputs=2:duration=first:dropout_transition=2,asetpts=PTS-STARTPTS,atrim=0:${trackDuration}"`,
          '-ar', '48000',
          '-acodec', 'libmp3lame',
          '-b:a', '192k',
          `"${outputPath}"`
        ].join(' ');

        console.log('FFmpeg command:', command);

        try {
            const { stdout, stderr } = await execAsync(command);
            console.log('FFmpeg stdout:', stdout);
            console.log('FFmpeg stderr:', stderr);
        } catch (error) {
            console.error('Error during FFmpeg processing:', error);
            throw error;
        }
    };
    const trackDuration = 900; // 15 minutes in seconds
    // Call the mixAudio function with the correct duration
    await mixAudio(ttsAudioPath, backingTrackPath, ttsVolume, backingTrackVolume, trackDuration, ttsSpeed, ttsDuration, outputPath);
    console.log('Audio mixed successfully');

    console.log('Reading mixed audio file...');
    const mixedAudioBuffer = await fs.readFile(outputPath);
    console.log('Mixed audio file read, size:', mixedAudioBuffer.length);

    // Clean up temporary files
    await Promise.all([
      fs.unlink(ttsAudioPath),
      fs.unlink(backingTrackPath),
      fs.unlink(outputPath)
    ]);

    console.log('Sending audio response...');
    return new NextResponse(mixedAudioBuffer, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Disposition': `attachment; filename="combined_affirmation_audio.mp3"`,
      },
    });
  } catch (error) {
    console.error('Error processing request:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

async function generatePollyTTS(text: string): Promise<string> {
  const MAX_TEXT_LENGTH = 3000; // Amazon Polly's maximum text length
  const audioUrls: string[] = [];

  // Split the text into chunks
  const textChunks = [];
  for (let i = 0; i < text.length; i += MAX_TEXT_LENGTH) {
    textChunks.push(text.slice(i, i + MAX_TEXT_LENGTH));
  }

  for (const chunk of textChunks) {
    const params = {
      Engine: "neural" as Engine,
      LanguageCode: "en-US" as LanguageCode,
      Text: chunk,
      TextType: "text" as TextType,
      OutputFormat: "mp3" as OutputFormat,
      VoiceId: "Joanna" as VoiceId,
    };

    const command = new SynthesizeSpeechCommand(params);
    const { AudioStream } = await polly.send(command);

    if (!AudioStream) {
      throw new Error('Failed to generate audio with Polly');
    }

    const buffer = await AudioStream.transformToByteArray();
    const fileName = `tts_${Date.now()}_${audioUrls.length}.mp3`;

    // Upload to S3
    await s3Client.send(new PutObjectCommand({
      Bucket: process.env.S3_BUCKET_NAME,
      Key: fileName,
      Body: buffer,
      ContentType: 'audio/mpeg'
    }));

    // Store the S3 URL
    audioUrls.push(`https://${process.env.S3_BUCKET_NAME}.s3.${process.env.AWS_REGION}.amazonaws.com/${fileName}`);
  }

  return audioUrls.join(',');
}

async function downloadAudio(url: string, prefix: string): Promise<string> {
  try {
    if (url.startsWith('data:')) {
      // Handle base64 data URL
      const base64Data = url.split(',')[1];
      const buffer = Buffer.from(base64Data, 'base64');
      const tempPath = path.join(os.tmpdir(), `${prefix}_${Date.now()}.mp3`);
      await fs.writeFile(tempPath, buffer);
      return tempPath;
    } else {
      // Handle regular URL
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch ${prefix} audio. Status: ${response.status}`);
      }
      const buffer = await response.arrayBuffer();
      const tempPath = path.join(os.tmpdir(), `${prefix}_${Date.now()}.mp3`);
      await fs.writeFile(tempPath, Buffer.from(buffer));
      return tempPath;
    }
  } catch (error: unknown) {
    console.error(`Error downloading ${prefix} audio:`, error);
    if (error instanceof Error) {
      throw new Error(`Failed to download ${prefix} audio: ${error.message}`);
    } else {
      throw new Error(`Failed to download ${prefix} audio: Unknown error`);
    }
  }
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

  const ttsVolumeDb = Math.log10(ttsVolume) * 20;
  const backingVolumeDb = Math.log10(backingTrackVolume) * 20;

  const atempoFilters = getAtempoFilters(ttsSpeed);
  const atempoFilterString = atempoFilters.length > 0 ? atempoFilters.join(',') + ',' : '';

  // Calculate the number of loops needed to reach the desired track duration
  const loopCount = Math.ceil(trackDuration / (ttsDuration / ttsSpeed));

  const command = [
    'ffmpeg',
    '-i', `"${ttsPath}"`,
    '-stream_loop', '-1',
    '-i', `"${backingPath}"`,
    '-filter_complex',
    `"[0:a]${atempoFilterString}volume=${ttsVolumeDb}dB,aloop=loop=${loopCount}:size=${Math.floor(ttsDuration * 48000)}[a];` +
    `[1:a]volume=${backingVolumeDb}dB[b];` +
    `[a][b]amix=inputs=2:duration=first:dropout_transition=2,asetpts=PTS-STARTPTS,atrim=0:${trackDuration}"`,
    '-ar', '48000',
    '-acodec', 'libmp3lame',
    '-b:a', '192k',
    `"${outputPath}"`
  ].join(' ');

  console.log('FFmpeg command:', command);

  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error('FFmpeg stderr:', stderr);
        reject(error);
      } else {
        console.log('FFmpeg stdout:', stdout);
        resolve();
      }
    });
  });
}

// Add this function to create a silent audio file
async function createSilentAudio(outputPath: string, duration: number): Promise<void> {
  const command = `ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t ${duration} -q:a 9 -acodec libmp3lame "${outputPath}"`;
  await execAsync(command);
}
