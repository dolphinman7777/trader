import ffmpeg from 'ffmpeg-static';
import { spawn, type ChildProcess } from 'child_process';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';
import { Readable, Writable } from 'stream';

const writeFile = promisify(fs.writeFile);
const readFile = promisify(fs.readFile);
const unlink = promisify(fs.unlink);

// Ensure ffmpeg path is correctly set
const ffmpegPath = process.env.FFMPEG_PATH || ffmpeg;

if (!ffmpegPath) {
  throw new Error('FFmpeg path not found');
}

export async function combineAudioFiles(files: Buffer[]): Promise<Buffer> {
  const tempDir = '/tmp'; // Use /tmp directory in Vercel
  const inputPaths: string[] = [];
  
  try {
    // Ensure temp directory exists
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    // Write input files to temp directory
    for (let i = 0; i < files.length; i++) {
      const inputPath = path.join(tempDir, `input${i}.mp3`);
      await writeFile(inputPath, files[i]);
      inputPaths.push(inputPath);
    }

    const outputPath = path.join(tempDir, 'output.mp3');

    return new Promise<Buffer>((resolve, reject) => {
      const args = [
        '-y',
        ...inputPaths.flatMap(file => ['-i', file]),
        '-filter_complex', `amix=inputs=${files.length}:duration=longest`,
        outputPath
      ];

      console.log('FFmpeg path:', ffmpegPath);
      console.log('FFmpeg args:', args);

      // Assert ffmpegPath is string to satisfy TypeScript
      const ffProcess = spawn(ffmpegPath as string, args);

      let stdoutData = '';
      let stderrData = '';

      ffProcess.stdout?.on('data', (data: Buffer) => {
        stdoutData += data.toString();
      });

      ffProcess.stderr?.on('data', (data: Buffer) => {
        stderrData += data.toString();
      });

      ffProcess.on('close', async (code: number | null) => {
        try {
          if (code === 0) {
            const outputBuffer = await readFile(outputPath);
            
            // Cleanup temp files
            await Promise.all([
              ...inputPaths.map(file => unlink(file).catch(() => {})),
              unlink(outputPath).catch(() => {})
            ]);

            resolve(outputBuffer);
          } else {
            console.error('FFmpeg error:', { code, stdout: stdoutData, stderr: stderrData });
            reject(new Error(`FFmpeg process exited with code ${code}`));
          }
        } catch (error) {
          console.error('Error processing output:', error);
          reject(error);
        }
      });

      ffProcess.on('error', (err: Error) => {
        console.error('FFmpeg spawn error:', err);
        reject(err);
      });
    });
  } catch (error) {
    // Cleanup temp files in case of error
    await Promise.all(
      inputPaths.map(file => 
        unlink(file).catch(() => {})
      )
    );
    console.error('FFmpeg processing error:', error);
    throw error;
  }
}
