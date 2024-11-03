const { execSync } = require('child_process');
const os = require('os');
const fs = require('fs');
const path = require('path');

function installFFmpeg() {
  try {
    console.log('Installing FFmpeg...');
    
    if (os.platform() === 'linux') {
      execSync('npm install @ffmpeg-installer/ffmpeg @ffprobe-installer/ffprobe', {
        stdio: 'inherit'
      });
    } else {
      console.log('Local development: Skipping FFmpeg installation');
    }
    
    console.log('FFmpeg installation completed');
  } catch (error) {
    console.error('Error installing FFmpeg:', error);
    process.exit(1);
  }
}

installFFmpeg(); 