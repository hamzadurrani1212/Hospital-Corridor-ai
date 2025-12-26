"use client";

import { useState, useRef, useEffect } from "react";
import { FiSearch, FiChevronDown, FiUpload, FiUser, FiMoreVertical, FiX, FiImage } from "react-icons/fi";

// Mock Data
const PERSONS = [
    {
        id: "p1",
        type: "Doctor",
        name: "Dr. Shahab khan",
        confidence: 98,
        lastSeen: "5 min ago",
        lastSeenTimestamp: Date.now() - 5 * 60 * 1000,
        camera: "CAM001",
        occurrences: 47,
    },
    {
        id: "p2",
        type: "Suspicious",
        name: "Person #P002",
        confidence: null,
        lastSeen: "12 min ago",
        lastSeenTimestamp: Date.now() - 12 * 60 * 1000,
        camera: "CAM002",
        occurrences: 3,
    },
    {
        id: "p3",
        type: "Known",
        name: "Security Staff #12",
        confidence: 95,
        lastSeen: "18 min ago",
        lastSeenTimestamp: Date.now() - 18 * 60 * 1000,
        camera: "CAM004",
        occurrences: 124,
    },
    {
        id: "p4",
        type: "Unknown",
        name: "Person #P004",
        confidence: null,
        lastSeen: "25 min ago",
        lastSeenTimestamp: Date.now() - 25 * 60 * 1000,
        camera: "CAM011",
        occurrences: 1,
    },
    {
        id: "p5",
        type: "Known",
        name: "Nurse Kainat Abbasi",
        confidence: 92,
        lastSeen: "32 min ago",
        lastSeenTimestamp: Date.now() - 32 * 60 * 1000,
        camera: "CAM003",
        occurrences: 89,
    }
];

const TYPE_OPTIONS = ["All Types", "Known", "Unknown", "Suspicious"];
const SORT_OPTIONS = ["Most Recent", "Most Frequent", "By Name"];

export default function EventsPage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [typeFilter, setTypeFilter] = useState("All Types");
    const [sortBy, setSortBy] = useState("Most Recent");
    const [showTypeDropdown, setShowTypeDropdown] = useState(false);
    const [showSortDropdown, setShowSortDropdown] = useState(false);
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [dragActive, setDragActive] = useState(false);
    const [uploadedImage, setUploadedImage] = useState(null);

    // Real Data State
    const [events, setEvents] = useState([]);
    const [stats, setStats] = useState({
        today_total: 0,
        today_authorized: 0,
        today_suspicious: 0
    });

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

    // Fetch Data
    const fetchData = async () => {
        try {
            const [eventsRes, statsRes] = await Promise.all([
                fetch(`${API_URL}/events/recent`),
                fetch(`${API_URL}/events/stats`)
            ]);

            if (eventsRes.ok && statsRes.ok) {
                const eventsData = await eventsRes.json();
                const statsData = await statsRes.json();

                // Transform Events to UI format
                const transformedEvents = eventsData.map(e => ({
                    id: e.track_id,
                    type: mapEventType(e.type),
                    name: e.name || "Unknown Person",
                    confidence: e.confidence ? Math.round(e.confidence * 100) : null,
                    lastSeen: formatTimeAgo(e.timestamp),
                    lastSeenTimestamp: e.timestamp * 1000,
                    camera: "CAM001", // Placeholder until camera ID is in event
                    occurrences: 1, // Logic for this would need more backend support, defaulting to 1
                    snapshot: e.snapshot
                }));

                setEvents(transformedEvents);
                setStats(statsData);
            }
        } catch (error) {
            console.error("Error fetching events:", error);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 2000); // Poll every 2s
        return () => clearInterval(interval);
    }, []);

    const mapEventType = (type) => {
        if (!type) return "Unknown";
        if (type.includes("AUTHORIZED") && !type.includes("UNAUTHORIZED")) return "Known";
        if (type.includes("UNAUTHORIZED")) return "Unknown"; // Or Suspicious? UI asks for "Unknown"
        if (type.includes("SUSPICIOUS") || type.includes("BEHAVIOR")) return "Suspicious";
        return "Unknown";
    };

    const formatTimeAgo = (ts) => {
        const seconds = Math.floor(Date.now() / 1000 - ts);
        if (seconds < 60) return "Just now";
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} min ago`;
        const hours = Math.floor(minutes / 60);
        return `${hours} hours ago`;
    };

    // Filter and sort persons
    const filteredPersons = events
        .filter((p) => {
            // Type filter
            if (typeFilter !== "All Types" && p.type !== typeFilter) return false;
            // Search filter
            if (searchTerm) {
                const term = searchTerm.toLowerCase();
                return (
                    p.name.toLowerCase().includes(term) ||
                    p.id.toLowerCase().includes(term) ||
                    p.camera.toLowerCase().includes(term)
                );
            }
            return true;
        })
        .sort((a, b) => {
            if (sortBy === "Most Recent") {
                return b.lastSeenTimestamp - a.lastSeenTimestamp;
            } else if (sortBy === "Most Frequent") {
                return b.occurrences - a.occurrences;
            } else if (sortBy === "By Name") {
                return a.name.localeCompare(b.name);
            }
            return 0;
        });

    return (
        <div className="max-w-7xl mx-auto flex flex-col gap-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white">Person Database</h1>
                    <p className="text-slate-400 text-sm">CLIP-Based Person Recognition</p>
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

            {/* Toolbar */}
            <div className="flex flex-wrap items-center gap-3 bg-card/50 p-3 rounded-xl border border-slate-800">
                {/* Search Input */}
                <div className="relative flex-1 min-w-[200px]">
                    <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search by name, ID, or upload image..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="bg-slate-800/50 border border-slate-700 text-sm pl-10 pr-4 py-2 rounded-lg text-white focus:outline-none focus:border-accent w-full"
                    />
                </div>

                {/* Type Filter Dropdown */}
                <div className="relative flex-shrink-0">
                    <button
                        onClick={() => {
                            setShowTypeDropdown(!showTypeDropdown);
                            setShowSortDropdown(false);
                        }}
                        className="flex items-center gap-2 px-3 py-2 bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg hover:bg-slate-700 min-w-[110px] justify-between transition-colors"
                    >
                        {typeFilter} <FiChevronDown size={14} />
                    </button>
                    {showTypeDropdown && (
                        <div className="absolute top-full left-0 mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
                            {TYPE_OPTIONS.map((option) => (
                                <button
                                    key={option}
                                    onClick={() => {
                                        setTypeFilter(option);
                                        setShowTypeDropdown(false);
                                    }}
                                    className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-700 flex items-center gap-2 ${typeFilter === option ? "text-accent" : "text-slate-300"
                                        }`}
                                >
                                    {typeFilter === option && <span className="text-accent">✓</span>}
                                    {option}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Sort Dropdown */}
                <div className="relative flex-shrink-0">
                    <button
                        onClick={() => {
                            setShowSortDropdown(!showSortDropdown);
                            setShowTypeDropdown(false);
                        }}
                        className="flex items-center gap-2 px-3 py-2 bg-accent/20 border border-accent/50 text-accent text-sm rounded-lg hover:bg-accent/30 min-w-[130px] justify-between transition-colors"
                    >
                        {sortBy} <FiChevronDown size={14} />
                    </button>
                    {showSortDropdown && (
                        <div className="absolute top-full left-0 mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
                            {SORT_OPTIONS.map((option) => (
                                <button
                                    key={option}
                                    onClick={() => {
                                        setSortBy(option);
                                        setShowSortDropdown(false);
                                    }}
                                    className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-700 flex items-center gap-2 ${sortBy === option ? "text-accent" : "text-slate-300"
                                        }`}
                                >
                                    {sortBy === option && <span className="text-accent">✓</span>}
                                    {option}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* List/Grid Toggle */}
                <button className="p-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 flex-shrink-0 transition-colors">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <line x1="1" y1="3" x2="15" y2="3" />
                        <line x1="1" y1="8" x2="15" y2="8" />
                        <line x1="1" y1="13" x2="15" y2="13" />
                    </svg>
                </button>

                {/* Upload Image Button - Styled like other toolbar buttons */}
                <button
                    onClick={() => setShowUploadModal(true)}
                    className="flex items-center gap-2 px-3 py-2 bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg transition-all duration-200 hover:bg-slate-700 hover:text-white hover:border-slate-600 flex-shrink-0"
                >
                    <FiUpload size={16} /> Upload Image
                </button>
            </div>

            {/* Stats Line */}
            <div className="flex items-center gap-6 text-sm text-slate-400 px-1">
                <span>{stats.today_total} persons detected today</span>
                <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span> {stats.today_authorized} known
                </span>
                <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-amber-500 rounded-full"></span> {stats.today_suspicious + stats.today_unauthorized} unknown/suspicious
                </span>
            </div>

            {/* List */}
            <div className="flex flex-col gap-4">
                {filteredPersons.length === 0 ? (
                    <div className="text-center py-12 text-slate-500">
                        No persons found matching your criteria.
                    </div>
                ) : (
                    filteredPersons.map((p) => (
                        <PersonRow key={`${p.id}-${p.lastSeenTimestamp}`} person={p} />
                    ))
                )}
            </div>

            {/* Upload Modal */}
            {showUploadModal && (
                <UploadModal
                    onClose={() => {
                        setShowUploadModal(false);
                        setUploadedImage(null);
                    }}
                    dragActive={dragActive}
                    setDragActive={setDragActive}
                    uploadedImage={uploadedImage}
                    setUploadedImage={setUploadedImage}
                />
            )}
        </div>
    );
}

function PersonRow({ person }) {
    // Determine Type Color
    let typeColor = "text-slate-400";
    if (person.type === "Known") typeColor = "text-emerald-400";
    if (person.type === "Suspicious") typeColor = "text-amber-400";
    if (person.type === "Unknown") typeColor = "text-slate-400";

    return (
        <div className="bg-card border border-slate-800 rounded-xl overflow-hidden group hover:border-slate-700 transition-colors">
            <div className="p-4 flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 flex-shrink-0 overflow-hidden">
                    {person.snapshot ? (
                        <img
                            src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${person.snapshot}`}
                            alt={person.name}
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <FiUser size={24} />
                    )}
                </div>

                <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-1">
                        <span className={`text-xs font-bold uppercase tracking-wide ${typeColor}`}>{person.type}</span>
                        {person.type === "Suspicious" && <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>}
                    </div>

                    <div className="flex justify-between items-start">
                        <div>
                            <h3 className="text-white font-semibold text-lg">{person.name}</h3>
                            {person.confidence && (
                                <div className="text-xs text-slate-500 mb-2">
                                    Match confidence: <span className="text-accent">{person.confidence}%</span>
                                </div>
                            )}

                            <div className="flex items-center gap-4 text-xs text-slate-400 mt-1">
                                <span><span className="text-slate-500">⏱</span> {person.lastSeen}</span>
                                <span><span className="text-slate-500">📷</span> {person.camera}</span>
                                <span><span className="text-accent">{person.occurrences}</span> occurrences</span>
                            </div>
                        </div>

                        <button className="text-slate-500 hover:text-white p-1">
                            <FiMoreVertical size={20} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Action Footer */}
            <div className="bg-slate-900/50 border-t border-slate-800 px-4 py-2 flex justify-between items-center text-xs">
                <button className="text-slate-400 hover:text-white">View Timeline</button>
                <button className="text-accent hover:text-accent/80 font-medium">Track Person</button>
            </div>
        </div>
    );
}

function UploadModal({ onClose, dragActive, setDragActive, uploadedImage, setUploadedImage }) {
    const fileInputRef = useRef(null);
    const [searching, setSearching] = useState(false);
    const [searchResults, setSearchResults] = useState(null);
    const [selectedFile, setSelectedFile] = useState(null);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileInput = (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const handleFile = (file) => {
        if (file.type.startsWith("image/")) {
            setSelectedFile(file);
            const reader = new FileReader();
            reader.onload = (e) => {
                setUploadedImage(e.target.result);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleSearch = async () => {
        if (!selectedFile) return;

        setSearching(true);
        setSearchResults(null);

        try {
            const formData = new FormData();
            formData.append("file", selectedFile);
            formData.append("top_k", "5");

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/search/image`,
                {
                    method: "POST",
                    body: formData,
                }
            );

            if (response.ok) {
                const results = await response.json();
                setSearchResults(results);
            } else {
                alert("Search failed. Please try again.");
            }
        } catch (error) {
            console.error("Search error:", error);
            alert("Failed to connect to server.");
        } finally {
            setSearching(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-card border border-slate-700 rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h2 className="text-xl font-bold text-white">Search by Image</h2>
                        <p className="text-slate-400 text-sm mt-1">
                            Upload an image to search for matching persons in the database using CLIP embeddings.
                        </p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
                        <FiX size={20} />
                    </button>
                </div>

                {/* Drop Zone */}
                <div
                    className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${dragActive
                        ? "border-accent bg-accent/10"
                        : uploadedImage
                            ? "border-emerald-500 bg-emerald-500/10"
                            : "border-slate-600 hover:border-slate-500"
                        }`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleFileInput}
                    />

                    {uploadedImage ? (
                        <div className="flex flex-col items-center gap-3">
                            <img
                                src={uploadedImage}
                                alt="Uploaded"
                                className="w-24 h-24 object-cover rounded-lg border border-slate-600"
                            />
                            <span className="text-emerald-400 text-sm">Image ready for search</span>
                        </div>
                    ) : (
                        <>
                            <FiImage className="mx-auto text-slate-500 mb-3" size={32} />
                            <p className="text-slate-300 text-sm mb-1">
                                Drag and drop an image here, or click to browse
                            </p>
                            <p className="text-slate-500 text-xs">Supports JPG, PNG up to 10MB</p>
                        </>
                    )}
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 mt-6">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg transition-all duration-200 hover:bg-slate-700 hover:text-white hover:border-slate-600"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSearch}
                        disabled={!uploadedImage}
                        className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg font-medium transition-all duration-200 ${uploadedImage
                            ? "bg-slate-800 border border-accent text-accent hover:bg-accent/20 hover:text-white"
                            : "bg-slate-800 border border-slate-700 text-slate-500 cursor-not-allowed opacity-50"
                            }`}
                    >
                        <FiSearch size={16} /> Search Database
                    </button>
                </div>
            </div>
        </div>
    );
}