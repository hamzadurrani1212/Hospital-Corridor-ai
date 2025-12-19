import api from "./api";

/**
 * Alert Service - handles alert CRUD operations
 */

/**
 * Fetch all alerts
 * @param {number} limit - Max number of alerts to return
 */
export const fetchAlerts = async (limit = 100) => {
    try {
        const res = await api.get(`/alerts?limit=${limit}`);
        return res.data;
    } catch (error) {
        console.error("Failed to fetch alerts:", error);
        return [];
    }
};

/**
 * Get recent alerts for dashboard display
 * @param {number} limit - Number of recent alerts
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
 * Get count of active (unacknowledged) alerts
 */
export const getActiveCount = async () => {
    try {
        const res = await api.get("/alerts/active");
        return res.data.count;
    } catch (error) {
        console.error("Failed to get active count:", error);
        return 0;
    }
};

/**
 * Acknowledge an alert
 * @param {string} alertId - ID of alert to acknowledge
 */
export const acknowledgeAlert = async (alertId) => {
    const res = await api.post(`/alerts/${alertId}/acknowledge`);
    return res.data;
};

/**
 * Get a specific alert by ID
 * @param {string} alertId - Alert ID
 */
export const getAlertById = async (alertId) => {
    const res = await api.get(`/alerts/${alertId}`);
    return res.data;
};