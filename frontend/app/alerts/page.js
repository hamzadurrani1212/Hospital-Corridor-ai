"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { FiSearch, FiFilter, FiCalendar, FiList, FiRefreshCw } from "react-icons/fi";
import AlertItem from "@/components/cards/AlertItem";
import api from "@/services/api";
import { getRecentAlerts } from "@/services/dashboardService";

export default function AlertsPage() {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("all");
    const [searchTerm, setSearchTerm] = useState("");

    const fetchAlerts = async () => {
        try {
            setLoading(true);
            const data = await getRecentAlerts(100);
            setAlerts(data);
        } catch (error) {
            console.error("Failed to fetch alerts:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();

        // Refresh every 30 seconds
        const interval = setInterval(fetchAlerts, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleAcknowledge = async (id) => {
        try {
            await api.post(`/alerts/${id}/acknowledge`);
            // Update local state
            setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: "acknowledged", acknowledged: true } : a));
        } catch (error) {
            console.error("Failed to acknowledge alert:", error);
        }
    };

    const filteredAlerts = alerts.filter(alert => {
        const matchesSearch = (alert.title || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
            (alert.description || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
            (alert.camera || alert.location || "").toLowerCase().includes(searchTerm.toLowerCase());

        if (filter === "all") return matchesSearch;
        if (filter === "active") return matchesSearch && (alert.status === "active" || !alert.acknowledged);
        if (filter === "acknowledged") return matchesSearch && (alert.status === "acknowledged" || alert.acknowledged);
        return matchesSearch;
    });

    const unacknowledgedCount = alerts.filter(a => a.status === "active" || !a.acknowledged).length;

    return (
        <div className="max-w-7xl mx-auto flex flex-col gap-6 h-[calc(100vh-100px)]">
            <Link href="/" className="text-slate-400 hover:text-white flex items-center gap-2 text-sm font-medium w-fit">
                ← Back to Dashboard
            </Link>

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white">Alerts</h1>
                    <p className="text-slate-400 text-sm">Security Event Management</p>
                </div>

                {/* Search */}
                <div className="relative">
                    <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search cameras, alerts..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="bg-card border border-slate-700 text-sm pl-10 pr-4 py-2 rounded-lg text-white focus:outline-none focus:border-accent w-80 placeholder:text-slate-600"
                    />
                </div>
            </div>

            {/* Filters Bar */}
            <div className="flex flex-col gap-3">
                <label className="text-xs font-semibold text-slate-500 ml-1">Filters</label>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="bg-card border border-slate-700 text-slate-300 text-sm rounded-lg p-2.5 focus:border-accent focus:outline-none"
                    >
                        <option value="all">All Alerts</option>
                        <option value="active">Active Only</option>
                        <option value="acknowledged">Acknowledged Only</option>
                    </select>

                    <select className="bg-card border border-slate-700 text-slate-300 text-sm rounded-lg p-2.5 focus:border-accent focus:outline-none">
                        <option>Severities (All)</option>
                        <option>Critical</option>
                        <option>Warning</option>
                        <option>Info</option>
                    </select>

                    <select className="bg-card border border-slate-700 text-slate-300 text-sm rounded-lg p-2.5 focus:border-accent focus:outline-none">
                        <option>All Cameras</option>
                        <option>Main Entrance</option>
                        <option>ICU Hallway</option>
                    </select>

                    <select className="bg-card border border-slate-700 text-slate-300 text-sm rounded-lg p-2.5 focus:border-accent focus:outline-none">
                        <option>Last 24 hours</option>
                        <option>Last 7 days</option>
                        <option>Last 30 days</option>
                    </select>
                </div>

                <div className="flex items-center gap-4 mt-1">
                    <button className="flex items-center gap-2 px-3 py-1.5 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-800 transition-colors">
                        <FiCalendar size={14} />
                        Custom Range
                    </button>
                    <button
                        onClick={() => { setFilter("all"); setSearchTerm(""); }}
                        className="text-xs text-slate-500 hover:text-accent transition-colors"
                    >
                        Clear Filters
                    </button>
                </div>
            </div>

            {/* List Header */}
            <div className="flex justify-between items-end border-b border-slate-800 pb-2 mt-2">
                <div className="flex items-center gap-2 text-white font-medium">
                    <FiList className="text-accent" />
                    {filteredAlerts.length} Alerts <span className="text-slate-500 text-sm font-normal">({unacknowledgedCount} unacknowledged)</span>
                </div>

                <button
                    onClick={fetchAlerts}
                    className="text-sm text-slate-400 hover:text-white flex items-center gap-1"
                >
                    <FiRefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {loading && alerts.length === 0 ? (
                    <div className="text-center py-12 text-slate-500">Loading alerts...</div>
                ) : filteredAlerts.length === 0 ? (
                    <div className="text-center py-12 text-slate-500">No alerts found matching your criteria.</div>
                ) : (
                    filteredAlerts.map((alert) => (
                        <AlertItem
                            key={alert.id}
                            {...alert}
                            isAcknowledged={alert.status === "acknowledged" || alert.acknowledged}
                            onAcknowledge={() => handleAcknowledge(alert.id)}
                        />
                    ))
                )}
            </div>
        </div>
    );
}
