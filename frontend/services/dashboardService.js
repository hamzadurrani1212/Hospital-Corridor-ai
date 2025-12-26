import api from "./api";

/**
 * Dashboard Service - fetches stats and data for dashboard display
 */

/**
 * Get count of active (online) cameras
 */
export const getActiveCameras = async () => {
  try {
    const res = await api.get("/cameras/active");
    return res.data.count;
  } catch (error) {
    console.error("Failed to get active cameras:", error);
    return 0;
  }
};

/**
 * Get count of active (unacknowledged) alerts
 */
export const getActiveAlerts = async () => {
  try {
    const res = await api.get("/alerts/active");
    return res.data.count;
  } catch (error) {
    console.error("Failed to get active alerts:", error);
    return 0;
  }
};

/**
 * Get count of people detected today
 */
export const getPeopleDetected = async () => {
  try {
    const res = await api.get("/events/people");
    return res.data.count;
  } catch (error) {
    console.error("Failed to get people count:", error);
    return 0;
  }
};

/**
 * Get system health status
 */
export const getSystemHealth = async () => {
  try {
    const res = await api.get("/system/health");
    return res.data;
  } catch (error) {
    console.error("Failed to get system health:", error);
    return {
      status: "error",
      processor: "unknown",
      camera: "unknown",
      qdrant: "unknown"
    };
  }
};

/**
 * Get recent alerts for dashboard display
 * @param {number} limit - Number of alerts to fetch
 */
export const getRecentAlerts = async (limit = 10) => {
  try {
    const res = await api.get(`/alerts/recent?limit=${limit}`);
    return res.data;
  } catch (error) {
    console.error("Failed to get recent alerts:", error);
    return [];
  }
};

/**
 * Get camera streams for dashboard display
 */
export const getCameraStreams = async () => {
  try {
    const res = await api.get("/cameras/streams");
    return res.data;
  } catch (error) {
    console.error("Failed to get camera streams:", error);
    return [];
  }
};

/**
 * Get all dashboard stats in one call
 */
export const getDashboardStats = async () => {
  try {
    const [activeCameras, activeAlerts, peopleDetected, health] = await Promise.all([
      getActiveCameras(),
      getActiveAlerts(),
      getPeopleDetected(),
      getSystemHealth()
    ]);

    return {
      activeCameras,
      activeAlerts,
      peopleDetected,
      health,
      crowdCount: health?.processor_stats?.crowd_count || 0,
      crowdStatus: health?.processor_stats?.crowd_status || "normal"
    };
  } catch (error) {
    console.error("Failed to get dashboard stats:", error);
    return {
      activeCameras: 0,
      activeAlerts: 0,
      peopleDetected: 0,
      crowdCount: 0,
      crowdStatus: "normal",
      health: { status: "error" }
    };
  }
};
