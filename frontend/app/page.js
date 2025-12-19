"use client";

import { useState, useEffect, useRef } from "react";
import { FiSearch, FiBell, FiUser, FiRefreshCw } from "react-icons/fi";
import StatCard from "@/components/cards/StatCard";
import AlertItem from "@/components/cards/AlertItem";
import { FiAlertTriangle, FiCamera, FiActivity } from "react-icons/fi";
import { getDashboardStats, getRecentAlerts } from "@/services/dashboardService";
import api from "@/services/api";

// API base URL for streaming (remove /api suffix)
const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/alerts';

export default function Dashboard() {
  const [searchTerm, setSearchTerm] = useState("");
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({
    activeAlerts: 0,
    activeCameras: 0,
    peopleDetected: 0,
  });
  const [loading, setLoading] = useState(true);
  const wsRef = useRef(null);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // Fetch stats
        const dashStats = await getDashboardStats();
        setStats({
          activeAlerts: dashStats.activeAlerts,
          activeCameras: dashStats.activeCameras,
          peopleDetected: dashStats.peopleDetected,
        });
        setIsCameraOn(dashStats.activeCameras > 0);

        // Fetch recent alerts
        const recentAlerts = await getRecentAlerts(10);
        setAlerts(recentAlerts);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // WebSocket connection for real-time alerts
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        wsRef.current = new WebSocket(WS_URL);

        wsRef.current.onopen = () => {
          console.log("WebSocket connected");
        };

        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // Handle ping/pong
            if (data.type === "ping") return;

            // Add new alert to the list
            const newAlert = {
              id: data.id,
              severity: data.severity || "warning",
              title: data.title || data.type,
              description: data.description || "",
              location: data.location || "Unknown",
              time: "Just now",
              acknowledged: false,
              snapshot: data.snapshot,
            };

            setAlerts((prev) => [newAlert, ...prev.slice(0, 9)]);

            // Update active alerts count
            setStats((prev) => ({
              ...prev,
              activeAlerts: prev.activeAlerts + 1,
            }));
          } catch (e) {
            console.error("Failed to parse WebSocket message:", e);
          }
        };

        wsRef.current.onclose = () => {
          console.log("WebSocket disconnected, reconnecting...");
          setTimeout(connectWebSocket, 3000);
        };

        wsRef.current.onerror = (error) => {
          console.error("WebSocket error:", error);
        };
      } catch (error) {
        console.error("Failed to connect WebSocket:", error);
        setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const toggleCamera = async () => {
    const newState = !isCameraOn;
    try {
      await api.post("/control", { active: newState });
      setIsCameraOn(newState);
      setStats((prev) => ({
        ...prev,
        activeCameras: newState ? 1 : 0,
      }));
    } catch (err) {
      console.error("Failed to toggle camera:", err);
    }
  };

  const refreshData = async () => {
    try {
      const recentAlerts = await getRecentAlerts(10);
      setAlerts(recentAlerts);

      const dashStats = await getDashboardStats();
      setStats({
        activeAlerts: dashStats.activeAlerts,
        activeCameras: dashStats.activeCameras,
        peopleDetected: dashStats.peopleDetected,
      });
    } catch (error) {
      console.error("Failed to refresh data:", error);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm">Hospital Corridor Monitoring</p>
        </div>

        <div className="flex items-center gap-4">
          {/* Search Bar */}
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search cameras, alerts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-card border border-slate-700 text-sm pl-10 pr-4 py-2 rounded-lg text-white focus:outline-none focus:border-accent w-64 placeholder:text-slate-600"
            />
          </div>

          <button
            onClick={refreshData}
            className="p-2 text-slate-400 hover:text-white transition-colors"
            title="Refresh"
          >
            <FiRefreshCw size={20} />
          </button>

          <button className="p-2 text-slate-400 hover:text-white transition-colors relative">
            <FiBell size={20} />
            {stats.activeAlerts > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-rose-500 rounded-full text-[10px] flex items-center justify-center text-white">
                {stats.activeAlerts > 9 ? "9+" : stats.activeAlerts}
              </span>
            )}
          </button>

          <div className="w-8 h-8 rounded-full bg-accent/20 text-accent flex items-center justify-center border border-accent/50">
            <FiUser size={16} />
          </div>
        </div>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Active Alerts"
          value={loading ? "..." : stats.activeAlerts.toString()}
          subtext={stats.activeAlerts > 0 ? "Requires attention" : "All clear"}
          type={stats.activeAlerts > 0 ? "negative" : "positive"}
          headerAction={<FiAlertTriangle className={stats.activeAlerts > 0 ? "text-rose-400" : "text-slate-500"} />}
        />
        <StatCard
          title="Cameras Online"
          value={isCameraOn ? "Online" : "Offline"}
          subtext={isCameraOn ? "Monitoring active" : "Click to start"}
          type={isCameraOn ? "neutral" : "negative"}
          headerAction={<FiCamera className={isCameraOn ? "text-accent" : "text-slate-600"} />}
        />
        <StatCard
          title="People Detected Today"
          value={loading ? "..." : stats.peopleDetected.toString()}
          subtext="Unique detections"
          type="positive"
          headerAction={<FiActivity className="text-emerald-400" />}
        />
      </div>

      {/* Controls Bar */}
      <div className="flex gap-4">
        <button
          onClick={toggleCamera}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${isCameraOn
            ? "bg-rose-500/10 text-rose-500 border border-rose-500/50 hover:bg-rose-500/20"
            : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/50 hover:bg-emerald-500/20"
            }`}
        >
          <FiCamera size={16} />
          {isCameraOn ? "Turn Camera Off" : "Turn Camera On"}
        </button>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-280px)] min-h-[500px]">

        {/* Live Feeds Section */}
        <div className="bg-card border border-slate-800 rounded-xl p-0 overflow-hidden relative group lg:col-span-2 flex flex-col">
          <div className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-3 py-1 rounded-full border border-white/10">
            <span className="flex items-center gap-2 text-xs font-semibold text-white">
              <span className={`w-2 h-2 rounded-full ${isCameraOn ? "bg-red-500 animate-pulse" : "bg-slate-500"}`}></span>
              {isCameraOn ? "LIVE" : "OFFLINE"}
            </span>
          </div>

          <div className="flex-1 bg-black flex items-center justify-center text-slate-600 overflow-hidden relative">
            {isCameraOn ? (
              <img
                src={`${API_BASE}/api/stream/0`}
                alt="Live Stream"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="text-center">
                <FiCamera size={48} className="mx-auto mb-4 text-slate-700" />
                <p className="text-slate-500">Camera is offline</p>
                <button
                  onClick={toggleCamera}
                  className="mt-4 px-4 py-2 bg-accent/20 border border-accent text-accent rounded-lg text-sm hover:bg-accent/30"
                >
                  Start Monitoring
                </button>
              </div>
            )}
          </div>

          <div className="p-4 bg-card border-t border-slate-800">
            <div className="flex justify-between items-center text-sm text-slate-400">
              <span>FEED_CAM001 - Main Entrance</span>
              <span className={isCameraOn ? "text-emerald-400" : "text-slate-500"}>
                {isCameraOn ? "Online" : "Offline"}
              </span>
            </div>
          </div>
        </div>

        {/* Alerts List */}
        <div className="flex flex-col h-full overflow-hidden">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-white font-semibold">Active Alerts</h2>
            <a href="/alerts" className="text-xs text-accent hover:text-white transition-colors">
              View All &gt;
            </a>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
            {loading ? (
              <div className="text-center py-8 text-slate-500">Loading alerts...</div>
            ) : alerts.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <FiBell size={32} className="mx-auto mb-2 opacity-50" />
                <p>No active alerts</p>
              </div>
            ) : (
              alerts.map((alert) => (
                <AlertItem
                  key={alert.id}
                  severity={alert.severity}
                  title={alert.title}
                  description={alert.description}
                  location={alert.location || alert.camera}
                  time={alert.time}
                  isAcknowledged={alert.status === "acknowledged" || alert.acknowledged}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
