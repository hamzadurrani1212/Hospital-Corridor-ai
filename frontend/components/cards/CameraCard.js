"use client";

import { useState } from "react";

/**
 * CameraCard component for displaying camera streams
 * @param {object} camera - Camera object with id, name, status, stream_url, location
 */
export default function CameraCard({ camera }) {
  // Handle both direct props and camera object
  const name = camera?.name || camera?.title || "Camera";
  const streamUrl = camera?.stream_url || camera?.url || "/api/stream/0";
  const status = camera?.status || "online";
  const location = camera?.location || "";

  const [imageError, setImageError] = useState(false);

  // Build full stream URL
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'http://localhost:8000';
  const fullStreamUrl = `${baseUrl}${streamUrl}`;

  const isOnline = status === "online";

  return (
    <div className="bg-card border border-slate-800 rounded-xl overflow-hidden group hover:border-slate-700 transition-colors">
      {/* Camera Header */}
      <div className="p-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${isOnline ? "bg-emerald-500 animate-pulse" : "bg-slate-600"
              }`}
          ></span>
          <span className="text-white font-medium text-sm">{name}</span>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${isOnline
            ? "bg-emerald-500/10 text-emerald-400"
            : "bg-slate-700 text-slate-400"
            }`}
        >
          {isOnline ? "Live" : "Offline"}
        </span>
      </div>

      {/* Stream Preview - Always show stream, backend returns placeholder if offline */}
      <div className="relative aspect-video bg-black flex items-center justify-center">
        {!imageError ? (
          <img
            src={fullStreamUrl}
            alt={name}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="text-slate-600 text-sm flex flex-col items-center gap-2">
            <span>📹</span>
            <span>Camera Offline or Unavailable</span>
            <button
              onClick={() => setImageError(false)}
              className="text-xs text-cyan-400 hover:text-cyan-300"
            >
              Retry
            </button>
          </div>
        )}

        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <button className="px-4 py-2 bg-accent/20 border border-accent text-accent rounded-lg text-sm hover:bg-accent/30 transition-colors">
            View Fullscreen
          </button>
        </div>
      </div>

      {/* Camera Footer */}
      {location && (
        <div className="p-2 bg-slate-900/50 text-xs text-slate-400">
          📍 {location}
        </div>
      )}
    </div>
  );
}

