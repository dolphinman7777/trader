import { NextResponse } from 'next/server';
import AWS from 'aws-sdk';

AWS.config.update({
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  region: process.env.AWS_REGION
});

const polly = new AWS.Polly();

export async function POST(request: Request) {
  try {
    const { text, voice = 'Joanna' } = await request.json();

    console.log('Received request:', { text: text.substring(0, 100), voice });

    const params = {
      Text: text,
      OutputFormat: 'mp3',
      VoiceId: voice,
      Engine: 'neural'
    };

    console.log('Polly params:', params);

    const data = await polly.synthesizeSpeech(params).promise();
    
    console.log('Polly response:', data);

    if (data.AudioStream instanceof Buffer) {
      const audioBase64 = data.AudioStream.toString('base64');
      const audioUrl = `data:audio/mp3;base64,${audioBase64}`;
      return NextResponse.json({ audioUrl });
    } else {
      console.error('AudioStream is not a Buffer:', data.AudioStream);
      throw new Error('Failed to generate audio: AudioStream is not a Buffer');
    }
  } catch (error) {
    console.error('Error in TTS conversion:', error);
    if (error instanceof Error) {
      return NextResponse.json({ error: `Failed to convert text to speech: ${error.message}` }, { status: 500 });
    } else {
      return NextResponse.json({ error: 'An unknown error occurred' }, { status: 500 });
    }
  }
}
