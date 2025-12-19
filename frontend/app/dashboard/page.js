"use client";

import { useEffect, useState, useCallback } from "react";
import ProtectedRoute from "../../components/common/ProtectedRoute";
import StatCard from "../../components/cards/StatCard";
import CameraCard from "../../components/cards/CameraCard";
import AlertsTable from "../../components/tables/AlertsTable";
import Sidebar from "../../components/layout/Sidebar";
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
    system: { status: "OK" },
  });
  const [alerts, setAlerts] = useState([]);
  const [streams, setStreams] = useState([]);
  const [prevAlertIds, setPrevAlertIds] = useState(new Set());

  // 🔔 Play alert sound
  const playSound = useCallback(() => {
    const audio = new Audio("/sounds/alert.mp3"); // make sure alert.mp3 is in /public/sounds/
    audio.play();
  }, []);

  // 🔄 Fetch dashboard data
  const fetchData = useCallback(async () => {
    const [cameras, alertsCount, people, system, recentAlerts, cameraStreams] =
      await Promise.all([
        getActiveCameras(),
        getActiveAlerts(),
        getPeopleDetected(),
        getSystemHealth(),
        getRecentAlerts(),
        getCameraStreams(),
      ]);

    setStats({ cameras, alerts: alertsCount, people, system });
    setStreams(cameraStreams);

    // 🚨 Detect new alerts and notify
    const newAlerts = recentAlerts.filter((a) => !prevAlertIds.has(a.id));
    if (newAlerts.length > 0) {
      newAlerts.forEach((alert) => {
        toast.error(`${alert.type} detected on ${alert.camera}`, {
          autoClose: 7000,
        });
        playSound();
      });
      setPrevAlertIds(new Set(recentAlerts.map((a) => a.id)));
    }

    setAlerts(recentAlerts);
  }, [prevAlertIds, playSound]);

  // ⏱ Fetch every 5 seconds
  useEffect(() => {
    // Initial fetch
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <ProtectedRoute roles={["admin", "operator"]}>
      <div className="flex min-h-screen bg-gray-100">
        <Sidebar />
        <main className="flex-1 p-4 md:p-6 lg:p-8 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Active Cameras"
              value={stats.cameras}
              status="normal"
            />
            <StatCard
              title="Active Alerts"
              value={stats.alerts}
              status={stats.alerts > 5 ? "critical" : "normal"}
            />
            <StatCard
              title="People Detected"
              value={stats.people}
              status={stats.people > 50 ? "warning" : "normal"}
            />
            <StatCard
              title="System Health"
              value={stats.system.status}
              status={stats.system.status === "OK" ? "normal" : "critical"}
            />
          </div>

          {/* Live Camera Feeds */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {streams.map((cam, idx) => (
              <CameraCard key={idx} title={cam.title} streamUrl={cam.url} />
            ))}
          </div>

          {/* Recent Alerts Table */}
          <AlertsTable alerts={alerts} />
        </main>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {streams.map((cam, idx) => (
            <CameraCard key={idx} title={cam.title} streamUrl={cam.url} />
          ))}
        </div>
      </div>
    </ProtectedRoute>
  );
}
