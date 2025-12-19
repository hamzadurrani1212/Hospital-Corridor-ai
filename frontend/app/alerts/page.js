"use client";

import { useState } from "react";
import Link from "next/link";
import { FiSearch, FiFilter, FiCalendar, FiList, FiRefreshCw } from "react-icons/fi";
import AlertItem from "@/components/cards/AlertItem";

// Mock Data (Expanded)
const ALERTS = [
    {
        id: 1,
        severity: "critical",
        title: "Unattended Bag Detected",
        description: "A bag has been left unattended for more than 3 minutes near the emergency exit. Immediate attention required.",
        location: "Floor 2 - East Wing Corridor",
        time: "2 minutes ago",
        acknowledged: false,
    },
    {
        id: 2,
        severity: "warning",
        title: "Person Loitering",
        description: "Individual has been stationary in restricted area for over 5 minutes without apparent purpose.",
        location: "Floor 2 - East Wing Corridor",
        time: "5 minutes ago",
        acknowledged: false,
    },
    {
        id: 3,
        severity: "warning",
        title: "Unusual Crowd Gathering",
        description: "Abnormal congregation of 8+ individuals detected in lobby area outside normal visiting hours.",
        location: "Floor 1 - Main Lobby",
        time: "12 minutes ago",
        acknowledged: true,
    },
    {
        id: 4,
        severity: "info",
        title: "Running Detected",
        description: "Fast movement detected in corridor. May indicate emergency situation or policy violation.",
        location: "Floor 3 - ICU Hallway",
        time: "18 minutes ago",
        acknowledged: true,
    },
    {
        id: 5,
        severity: "critical",
        title: "Unauthorized Access Attempt",
        description: "Individual attempted to enter restricted area without proper credentials.",
        location: "Floor 1 - North Emergency Exit",
        time: "32 minutes ago",
        acknowledged: true,
    }
];

export default function AlertsPage() {
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
                        className="bg-card border border-slate-700 text-sm pl-10 pr-4 py-2 rounded-lg text-white focus:outline-none focus:border-accent w-80 placeholder:text-slate-600"
                    />
                </div>
            </div>

            {/* Filters Bar */}
            <div className="flex flex-col gap-3">
                <label className="text-xs font-semibold text-slate-500 ml-1">Filters</label>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <select className="bg-card border border-slate-700 text-slate-300 text-sm rounded-lg p-2.5 focus:border-accent focus:outline-none">
                        <option>Severities</option>
                        <option>Critical</option>
                        <option>Warning</option>
                        <option>Info</option>
                    </select>

                    <select className="bg-card border border-slate-700 text-slate-300 text-sm rounded-lg p-2.5 focus:border-accent focus:outline-none">
                        <option>Status</option>
                        <option>Active</option>
                        <option>Acknowledged</option>
                        <option>Resolved</option>
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
                    <button className="text-xs text-slate-500 hover:text-accent transition-colors">
                        Clear Filters
                    </button>
                </div>
            </div>

            {/* List Header */}
            <div className="flex justify-between items-end border-b border-slate-800 pb-2 mt-2">
                <div className="flex items-center gap-2 text-white font-medium">
                    <FiList className="text-accent" />
                    5 Alerts <span className="text-slate-500 text-sm font-normal">(2 unacknowledged)</span>
                </div>

                <button className="text-sm text-slate-400 hover:text-white flex items-center gap-1">
                    <FiRefreshCw size={14} /> Refresh
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {ALERTS.map((alert) => (
                    <AlertItem
                        key={alert.id}
                        severity={alert.severity}
                        title={alert.title}
                        description={alert.description}
                        location={alert.location}
                        time={alert.time}
                        isAcknowledged={alert.acknowledged}
                    />
                ))}
            </div>
        </div>
    );
}