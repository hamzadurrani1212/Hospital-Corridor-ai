"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import ProtectedRoute from "../../components/common/ProtectedRoute";
import StatCard from "../../components/cards/StatCard";
import CameraCard from "../../components/cards/CameraCard";
import AlertsTable from "../../components/tables/AlertTable";
import Sidebar from "../../components/layout/Sidebar";
import useSocket from "../../hooks/useSocket";
import { toast } from "react-toastify";

import {
  getActiveCameras,
  getActiveAlerts,
  getPeopleDetected,
  getSystemHealth,
  getRecentAlerts,
  getCameraStreams,
} from "../../services/dashboardService";

export default function DashboardPage() {
  const [stats, setStats] = useState({
    cameras: 0,
    alerts: 0,
    people: 0,
    crowdCount: 0,
    system: { status: "OK" },
  });
  const [alerts, setAlerts] = useState([]);
  const [streams, setStreams] = useState([]);

  //  Play alert sound
  const playSound = useCallback(() => {
    const audio = new Audio("/sounds/alert.mp3");
    audio.play().catch(e => console.log("Audio play blocked"));
  }, []);

  //  Handle Real-time WebSocket Messages
  const handleSocketMessage = useCallback((data) => {
    console.log("WebSocket Alert Received:", data);

    // Add new alert to the top of the list
    setAlerts(prev => {
      // Check if alert already exists to prevent duplicates
      if (prev.some(a => a.id === data.id)) return prev;

      const updated = [data, ...prev].slice(0, 50); // Keep last 50
      return updated;
    });

    // Update alert count stat
    setStats(prev => ({
      ...prev,
      alerts: prev.alerts + 1
    }));

    // Notify user
    toast.error(`${data.type}: ${data.title || "Security Alert"}`, {
      autoClose: 7000,
      position: "top-right"
    });

    playSound();
  }, [playSound]);

  // Connect to WebSocket
  useSocket(handleSocketMessage);

  //  Initial metadata fetch & periodic sync for stats
  const fetchMetadata = useCallback(async () => {
    try {
      const [cameras, alertsCount, people, system, cameraStreams, recentAlerts] = await Promise.all([
        getActiveCameras(),
        getActiveAlerts(),
        getPeopleDetected(),
        getSystemHealth(),
        getCameraStreams(),
        getRecentAlerts()
      ]);

      // Extract crowd count from processor stats
      const crowdCount = system?.processor_stats?.crowd_count || 0;

      setStats({ cameras, alerts: alertsCount, people, crowdCount, system });
      setStreams(cameraStreams);
      setAlerts(recentAlerts);
    } catch (error) {
      console.error("Failed to fetch dashboard metadata:", error);
    }
  }, []);

  useEffect(() => {
    fetchMetadata();
    // Sync heavy stats less frequently (e.g. every 10s) 
    // real-time alerts are handled by WebSocket
    const interval = setInterval(fetchMetadata, 10000);
    return () => clearInterval(interval);
  }, [fetchMetadata]);

  // Memoize components to prevent jitter
  const memoizedStreams = useMemo(() => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {streams.map((cam, idx) => (
        <CameraCard key={cam.id || idx} title={cam.title} streamUrl={cam.url} />
      ))}
    </div>
  ), [streams]);

  const memoizedAlertsTable = useMemo(() => (
    <AlertsTable alerts={alerts} />
  ), [alerts]);

  return (
    <ProtectedRoute roles={["admin", "operator"]}>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 p-6 md:p-8 lg:p-10 space-y-8 max-w-7xl mx-auto">
          {/* Header Area */}
          <div className="flex justify-between items-end">
            <div>
              <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">System Dashboard</h1>
              <p className="text-gray-500 mt-1">Real-time corridor safety monitoring</p>
            </div>
            <div className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-bold flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              Live Connection: Active
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
            <StatCard title="Active Cameras" value={stats.cameras} status="normal" />
            <StatCard title="Total Alerts" value={stats.alerts} status={stats.alerts > 10 ? "critical" : "normal"} />
            <StatCard title="People Detected" value={stats.people} status={stats.people > 20 ? "warning" : "normal"} />
            <StatCard title="Crowd Count" value={stats.crowdCount} status={stats.crowdCount >= 3 ? "warning" : "normal"} />
            <StatCard title="System Status" value={stats.system.status} status={stats.system.status === "OK" ? "normal" : "critical"} />
          </div>

          {/* Visualization Section */}
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">Live Video Surveillance</h2>
            {memoizedStreams}
          </div>

          {/* Event Logs */}
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">Threat Assessment & Logs</h2>
            {memoizedAlertsTable}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
