import React from 'react';

interface AudioLayerPlayerProps {
  onTrackSelect: (trackUrl: string | null) => void;
  audioRef: React.RefObject<HTMLAudioElement>;
}

export function AudioLayerPlayer({ onTrackSelect, audioRef }: AudioLayerPlayerProps) {
  // ... existing code

  return (
    <div className="audio-layer-player">
      {/* ... existing JSX */}
      <audio ref={audioRef} src={selectedTrack || undefined} className="hidden" />
    </div>
  );
}
