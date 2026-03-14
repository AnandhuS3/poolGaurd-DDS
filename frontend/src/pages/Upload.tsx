/**
 * Upload.tsx
 * Video upload page.
 * - Tab 1: Upload a file        → POST /analyze/upload
 * - Tab 2: YouTube URL          → POST /analyze/youtube
 * - After upload: trigger WS processing via sendVideoPath
 * - When processing complete: show download button → GET /download/{filename}
 * - Navigate to Dashboard to watch processing
 */

import { useState, useRef, useEffect, type DragEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { parseApiError } from '../services/parseApiError';
import { useAuth } from '../context/AuthContext';
import { wsClient } from '../core/websocket/WebSocketClient';
import { DetectionStore, type DetectionState } from '../state/DetectionStore';
import { AlertStore } from '../state/AlertStore';

interface UploadResponse {
  status: string;
  filename: string;
  filepath: string;
  video_url: string;
  message: string;
}

type Tab = 'file' | 'youtube';

export function Upload() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [tab, setTab] = useState<Tab>('file');

  // File tab state
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileStatus, setFileStatus] = useState<'idle' | 'uploading' | 'ready' | 'error'>('idle');
  const [fileError, setFileError] = useState('');

  // YouTube tab state
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [ytStatus, setYtStatus] = useState<'idle' | 'downloading' | 'ready' | 'error'>('idle');
  const [ytError, setYtError] = useState('');

  // Shared post-upload state
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);

  // Detection completion tracking (for download button)
  const [detection, setDetection] = useState<DetectionState>(() => DetectionStore.getState());
  useEffect(() => DetectionStore.subscribe(setDetection), []);

  // ── File handlers ────────────────────────────────────────────────────────────
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) acceptFile(dropped);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) acceptFile(f);
  };

  const acceptFile = (f: File) => {
    if (!f.type.startsWith('video/')) {
      setFileError('Please select a video file.');
      return;
    }
    setFileError('');
    setFile(f);
    setFileStatus('idle');
    setUploadedPath(null);
    setUploadedFilename(null);
  };

  const handleUpload = async () => {
    if (!file || !token) return;
    setFileStatus('uploading');
    setFileError('');
    setUploadProgress(0);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post<UploadResponse>('/analyze/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100));
        },
      });
      setUploadedPath(res.data.filepath);
      setUploadedFilename(res.data.filename);
      setFileStatus('ready');
    } catch (err: unknown) {
      const msg = parseApiError(err, 'Upload failed');
      setFileError(msg);
      setFileStatus('error');
    }
  };

  // ── YouTube handler ──────────────────────────────────────────────────────────
  const handleYoutubeDownload = async () => {
    if (!youtubeUrl.trim() || !token) return;
    setYtStatus('downloading');
    setYtError('');
    try {
      const res = await axios.post<UploadResponse>('/analyze/youtube', { url: youtubeUrl.trim() });
      setUploadedPath(res.data.filepath);
      setUploadedFilename(res.data.filename);
      setYtStatus('ready');
    } catch (err: unknown) {
      const msg = parseApiError(err, 'YouTube download failed');
      setYtError(msg);
      setYtStatus('error');
    }
  };

  // ── Start analysis ───────────────────────────────────────────────────────────
  const handleStartAnalysis = () => {
    if (!uploadedPath || !token) return;
    const pathToSend = uploadedPath;

    // Reset state from any previous analysis
    DetectionStore.reset();
    AlertStore.clear();

    // Always disconnect first so we get a clean connection (prevents the
    // "already open – skipping" guard from silently blocking a new session).
    wsClient.disconnect();
    wsClient.connect(token);

    // Navigate to Dashboard immediately – it will show idle until the first frame arrives
    navigate('/');

    // Send the video path as soon as the socket is confirmed open.
    // This is more robust than a fixed timeout (handles slow localhost startup).
    const unsub = wsClient.onStatus((status) => {
      if (status === 'connected') {
        wsClient.startProcessing(pathToSend);
        unsub();
      }
    });
  };

  const isReady = fileStatus === 'ready' || ytStatus === 'ready';

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto flex flex-col gap-6">
        <div>
          <h1 className="text-white font-semibold text-base">Upload Video</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">
            Upload a video file or provide a YouTube URL for drowning detection analysis.
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-[#0B0F19] border border-[#1F2937] rounded p-1 w-fit">
          {(['file', 'youtube'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded text-xs font-medium transition-colors ${
                tab === t
                  ? 'bg-[#1F2937] text-white'
                  : 'text-[#9CA3AF] hover:text-white'
              }`}
            >
              {t === 'file' ? '📁 File Upload' : '▶ YouTube URL'}
            </button>
          ))}
        </div>

        {/* ── File Upload Tab ── */}
        {tab === 'file' && (
          <>
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded transition-colors cursor-pointer p-10 text-center ${
                isDragging
                  ? 'border-[#3B82F6] bg-[#3B82F6]/5'
                  : 'border-[#1F2937] hover:border-[#374151] bg-[#121212]'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="text-[#6B7280] text-sm flex flex-col items-center gap-2">
                <span className="text-3xl">📹</span>
                {file ? (
                  <span className="text-white font-medium">{file.name}</span>
                ) : (
                  <>
                    <span>Drag & drop or click to select a video</span>
                    <span className="text-xs text-[#4B5563]">MP4, AVI, MOV supported</span>
                  </>
                )}
              </div>
            </div>

            {fileError && (
              <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/30 text-[#FF3B30] text-sm rounded p-3">
                {fileError}
              </div>
            )}

            {fileStatus === 'uploading' && (
              <div className="flex flex-col gap-2">
                <div className="flex justify-between text-xs text-[#9CA3AF]">
                  <span>Uploading…</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="h-1.5 bg-[#1F2937] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#3B82F6] transition-all duration-200"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {fileStatus === 'ready' && (
              <div className="bg-[#34C759]/10 border border-[#34C759]/30 text-[#34C759] text-sm rounded p-3">
                ✓ Uploaded successfully. Ready for analysis.
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={handleUpload}
                disabled={!file || fileStatus === 'uploading' || fileStatus === 'ready'}
                className="px-5 py-2 bg-[#1F2937] hover:bg-[#374151] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded transition-colors"
              >
                {fileStatus === 'uploading' ? 'Uploading…' : 'Upload'}
              </button>
            </div>
          </>
        )}

        {/* ── YouTube Tab ── */}
        {tab === 'youtube' && (
          <>
            <div className="flex flex-col gap-2">
              <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">YouTube URL</label>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="flex-1 bg-[#121212] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
                  disabled={ytStatus === 'downloading'}
                />
                <button
                  onClick={handleYoutubeDownload}
                  disabled={!youtubeUrl.trim() || ytStatus === 'downloading' || ytStatus === 'ready'}
                  className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded transition-colors whitespace-nowrap"
                >
                  {ytStatus === 'downloading' ? 'Downloading…' : 'Download'}
                </button>
              </div>
              <p className="text-[#4B5563] text-xs">
                The video will be downloaded server-side via yt-dlp.
              </p>
            </div>

            {ytError && (
              <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/30 text-[#FF3B30] text-sm rounded p-3">
                {ytError}
              </div>
            )}

            {ytStatus === 'downloading' && (
              <div className="flex items-center gap-2 text-[#9CA3AF] text-sm">
                <span className="animate-pulse">●</span>
                <span>Downloading from YouTube…</span>
              </div>
            )}

            {ytStatus === 'ready' && (
              <div className="bg-[#34C759]/10 border border-[#34C759]/30 text-[#34C759] text-sm rounded p-3">
                ✓ YouTube video downloaded. Ready for analysis.
              </div>
            )}
          </>
        )}

        {/* ── Start Analysis / Download (shared) ── */}
        {isReady && (
          <div className="flex gap-3 items-center">
            <button
              onClick={handleStartAnalysis}
              className="px-5 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-semibold rounded transition-colors"
            >
              Start Analysis →
            </button>

            {detection.isComplete && uploadedFilename && (
              <a
                href={`/download/${uploadedFilename}`}
                download
                className="px-5 py-2 bg-[#34C759]/20 border border-[#34C759]/40 hover:bg-[#34C759]/30 text-[#34C759] text-sm font-medium rounded transition-colors"
              >
                ↓ Download Processed Video
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

