import { useState, useRef } from "react";
import { Mic, MicOff } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  onAudioReady: (blob: Blob) => void;
  disabled?: boolean;
}

export function VoiceButton({ onAudioReady, disabled }: Props) {
  const [recording, setRecording] = useState(false);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        onAudioReady(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      mr.start();
      setRecording(true);
    } catch {
      alert("无法访问麦克风，请检查权限。");
    }
  };

  const stop = () => {
    mediaRef.current?.stop();
    setRecording(false);
  };

  return (
    <button
      type="button"
      className={clsx("voice-btn", recording && "voice-btn-recording")}
      onClick={recording ? stop : start}
      disabled={disabled}
      title={recording ? "点击停止录音" : "按住录音"}
    >
      {recording ? <MicOff size={18} /> : <Mic size={18} />}
    </button>
  );
}
