import { NextResponse } from 'next/server';
import { PollyClient, SynthesizeSpeechCommand, Engine, LanguageCode, OutputFormat, TextType, VoiceId } from "@aws-sdk/client-polly";

// Initialize Polly client
const polly = new PollyClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

export async function POST(request: Request) {
  try {
    const { text, volume = 1 } = await request.json();

    if (!text) {
      return NextResponse.json({ error: 'Text is required' }, { status: 400 });
    }

    console.log('Received text for TTS:', text);

    // Clean and format the affirmations
    const affirmations: string[] = text.includes('.')
      ? text.split('.')
          .map((line: string) => line.trim())
          .filter((line: string) => line.length > 0)
      : text.split('-')
          .map((line: string) => line.trim())
          .filter((line: string) => line.length > 0);

    console.log('Separated affirmations:', affirmations);

    // Create SSML with proper breaks and emphasis
    const ssmlText = `<speak>
      ${affirmations.map((affirmation: string) => `
        <p>
          <prosody rate="95%" volume="loud">
            ${affirmation}${!affirmation.endsWith('.') ? '.' : ''}
          </prosody>
        </p>
        <break time="1.5s"/>
      `).join('')}
    </speak>`;

    console.log('Formatted SSML:', ssmlText);

    const params = {
      Text: ssmlText,
      OutputFormat: 'mp3' as OutputFormat,
      VoiceId: 'Joanna' as VoiceId,
      Engine: 'neural' as Engine,
      LanguageCode: "en-US" as LanguageCode,
      TextType: "ssml" as TextType,
      SampleRate: "24000",
    };

    const command = new SynthesizeSpeechCommand(params);
    const response = await polly.send(command);

    if (!response.AudioStream) {
      throw new Error('No audio stream returned from Polly');
    }

    // Convert the readable stream to a buffer
    const chunks: Uint8Array[] = [];
    for await (const chunk of response.AudioStream as any) {
      chunks.push(chunk);
    }
    
    const audioBuffer = Buffer.concat(chunks);
    const audioBase64 = audioBuffer.toString('base64');
    const audioUrl = `data:audio/mpeg;base64,${audioBase64}`;

    console.log('TTS conversion successful, audio length:', audioBuffer.length);
    console.log('Number of affirmations processed:', affirmations.length);

    return NextResponse.json({ audioUrl });
  } catch (error) {
    console.error('Error in TTS conversion:', error);
    return NextResponse.json({ 
      error: 'TTS conversion failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
