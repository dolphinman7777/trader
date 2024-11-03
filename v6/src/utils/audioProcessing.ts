import { Redis } from '@upstash/redis';
import { S3 } from 'aws-sdk';
import { v4 as uuidv4 } from 'uuid';

const s3 = new S3({
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  region: process.env.AWS_REGION,
});

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL!,
  token: process.env.UPSTASH_REDIS_REST_TOKEN!,
});

export async function processAudio(audioBuffer: Buffer): Promise<string> {
  const fileName = `${uuidv4()}.mp3`;
  
  try {
    // Upload to S3 instead of processing locally
    await s3.upload({
      Bucket: process.env.S3_BUCKET_NAME!,
      Key: `temp/${fileName}`,
      Body: audioBuffer,
      ContentType: 'audio/mpeg',
    }).promise();

    // Fix Redis set command to use correct argument count
    await redis.set(`audio:${fileName}`, 'true');
    // Set expiration separately
    await redis.expire(`audio:${fileName}`, 3600);

    // Return the CloudFront URL if you're using CDN
    return `${process.env.CLOUDFRONT_URL}/temp/${fileName}`;
  } catch (error) {
    console.error('Error processing audio:', error);
    throw new Error('Audio processing failed');
  }
} 