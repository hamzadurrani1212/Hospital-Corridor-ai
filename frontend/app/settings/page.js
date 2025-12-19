"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import {
    FiSearch, FiSave, FiClock, FiUsers, FiActivity, FiAlertTriangle,
    FiVideo, FiMonitor, FiUserPlus, FiTrash2, FiUpload, FiX, FiCheck
} from "react-icons/fi";
import { registerStaff, getStaffList, deleteStaff } from "@/services/staffService";

const ABSOLUTE_ACCENT = "text-cyan-400";
const ABSOLUTE_BG_ACCENT = "bg-cyan-400";
const ABSOLUTE_BORDER_ACCENT = "border-cyan-400";

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState("Staff Management");

    return (
        <div className="max-w-5xl mx-auto flex flex-col gap-6 pb-10">
            <Link href="/" className="text-slate-400 hover:text-white flex items-center gap-2 text-sm font-medium w-fit">
                ← Back to Dashboard
            </Link>

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white">Settings</h1>
                    <p className="text-slate-400 text-sm">Configure system, staff, and alerts</p>
                </div>

                {/* Search */}
                <div className="relative">
                    <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search settings..."
                        className="bg-card border border-slate-700 text-sm pl-10 pr-4 py-2 rounded-lg text-white focus:outline-none focus:border-cyan-400 w-80 placeholder:text-slate-600"
                    />
                </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 border-b border-slate-800 overflow-x-auto">
                <TabButton active={activeTab === "Staff Management"} onClick={() => setActiveTab("Staff Management")} icon={FiUserPlus} label="Staff Management" />
                <TabButton active={activeTab === "Alert Thresholds"} onClick={() => setActiveTab("Alert Thresholds")} icon={FiAlertTriangle} label="Alert Thresholds" />
                <TabButton active={activeTab === "Cameras"} onClick={() => setActiveTab("Cameras")} icon={FiVideo} label="Cameras" />
                <TabButton active={activeTab === "System"} onClick={() => setActiveTab("System")} icon={FiMonitor} label="System" />
            </div>

            {/* Content Area */}
            {activeTab === "Staff Management" && <StaffManagementTab />}
            {activeTab === "Alert Thresholds" && <AlertThresholdsTab />}
        </div>
    );
}

// ============================================
// STAFF MANAGEMENT TAB
// ============================================
function StaffManagementTab() {
    const [staffList, setStaffList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showRegisterModal, setShowRegisterModal] = useState(false);

    const fetchStaff = useCallback(async () => {
        setLoading(true);
        const data = await getStaffList();
        setStaffList(data);
        setLoading(false);
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        fetchStaff();
    }, [fetchStaff]);

    const handleDelete = async (staffId) => {
        if (!confirm("Are you sure you want to remove this staff member?")) return;

        try {
            await deleteStaff(staffId);
            setStaffList(prev => prev.filter(s => s.staff_id !== staffId && s.id !== staffId));
        } catch (error) {
            alert("Failed to delete staff member");
        }
    };

    const handleRegisterSuccess = () => {
        setShowRegisterModal(false);
        fetchStaff();
    };

    return (
        <div className="animate-in fade-in duration-300">
            <div className="mb-6 flex justify-between items-start">
                <div>
                    <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                        <div className={`w-2 h-6 ${ABSOLUTE_BORDER_ACCENT} border-l-4 rounded-full`}></div>
                        Authorized Staff
                    </h2>
                    <p className="text-slate-400 text-sm mt-1 ml-4">
                        Register and manage authorized hospital personnel
                    </p>
                </div>

                <button
                    onClick={() => setShowRegisterModal(true)}
                    className={`px-4 py-2 ${ABSOLUTE_BG_ACCENT} hover:bg-cyan-300 text-slate-900 font-semibold rounded-lg flex items-center gap-2 transition-colors`}
                >
                    <FiUserPlus size={18} />
                    Register New Staff
                </button>
            </div>

            {/* Staff List */}
            <div className="bg-card border border-slate-800 rounded-xl overflow-hidden">
                {loading ? (
                    <div className="p-8 text-center text-slate-500">Loading staff list...</div>
                ) : staffList.length === 0 ? (
                    <div className="p-8 text-center">
                        <FiUsers size={48} className="mx-auto text-slate-700 mb-4" />
                        <p className="text-slate-500 mb-4">No staff members registered yet</p>
                        <button
                            onClick={() => setShowRegisterModal(true)}
                            className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
                        >
                            Register First Staff Member
                        </button>
                    </div>
                ) : (
                    <table className="w-full">
                        <thead className="bg-slate-900/50 border-b border-slate-800">
                            <tr>
                                <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Name</th>
                                <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Role</th>
                                <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Department</th>
                                <th className="text-left py-3 px-4 text-slate-400 text-sm font-medium">Status</th>
                                <th className="text-right py-3 px-4 text-slate-400 text-sm font-medium">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {staffList.map((staff) => (
                                <tr key={staff.id || staff.staff_id} className="border-b border-slate-800 hover:bg-slate-900/30">
                                    <td className="py-4 px-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-500">
                                                <FiUsers size={20} />
                                            </div>
                                            <span className="text-white font-medium">{staff.name}</span>
                                        </div>
                                    </td>
                                    <td className="py-4 px-4 text-slate-300">{staff.role}</td>
                                    <td className="py-4 px-4 text-slate-400">{staff.department}</td>
                                    <td className="py-4 px-4">
                                        <span className={`px-2 py-1 rounded-full text-xs ${staff.authorized
                                            ? "bg-emerald-500/10 text-emerald-400"
                                            : "bg-slate-700 text-slate-400"
                                            }`}>
                                            {staff.authorized ? "Authorized" : "Pending"}
                                        </span>
                                    </td>
                                    <td className="py-4 px-4 text-right">
                                        <button
                                            onClick={() => handleDelete(staff.staff_id || staff.id)}
                                            className="p-2 text-slate-500 hover:text-rose-400 transition-colors"
                                            title="Remove staff"
                                        >
                                            <FiTrash2 size={18} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Register Modal */}
            {showRegisterModal && (
                <RegisterStaffModal
                    onClose={() => setShowRegisterModal(false)}
                    onSuccess={handleRegisterSuccess}
                />
            )}
        </div>
    );
}

// ============================================
// REGISTER STAFF MODAL
// ============================================
function RegisterStaffModal({ onClose, onSuccess }) {
    const [formData, setFormData] = useState({
        name: "",
        role: "",
        department: "",
    });
    const [imageFile, setImageFile] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    const roles = ["Doctor", "Nurse", "Security", "Administrator", "Technician", "Other"];
    const departments = ["Emergency", "ICU", "General Ward", "Pediatrics", "Surgery", "Radiology", "Laboratory", "Pharmacy", "Administration"];

    const handleImageChange = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            setImageFile(file);
            const reader = new FileReader();
            reader.onload = (e) => setImagePreview(e.target?.result);
            reader.readAsDataURL(file);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!formData.name || !formData.role || !formData.department || !imageFile) {
            setError("Please fill all fields and upload an image");
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            await registerStaff({
                ...formData,
                image: imageFile,
            });
            onSuccess();
        } catch (err) {
            setError(err.response?.data?.detail || "Registration failed. Please try again.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-card border border-slate-700 rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h2 className="text-xl font-bold text-white">Register New Staff</h2>
                        <p className="text-slate-400 text-sm mt-1">
                            Add authorized hospital personnel to the system
                        </p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
                        <FiX size={20} />
                    </button>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Image Upload */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Staff Photo <span className="text-rose-400">*</span>
                        </label>
                        <div
                            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${imagePreview
                                ? "border-emerald-500 bg-emerald-500/5"
                                : "border-slate-600 hover:border-slate-500"
                                }`}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={handleImageChange}
                            />
                            {imagePreview ? (
                                <div className="flex flex-col items-center gap-3">
                                    <img
                                        src={imagePreview}
                                        alt="Preview"
                                        className="w-24 h-24 object-cover rounded-full border-2 border-slate-600"
                                    />
                                    <span className="text-emerald-400 text-sm flex items-center gap-1">
                                        <FiCheck size={16} /> Image selected
                                    </span>
                                </div>
                            ) : (
                                <>
                                    <FiUpload className="mx-auto text-slate-500 mb-2" size={32} />
                                    <p className="text-slate-400 text-sm">Click to upload staff photo</p>
                                    <p className="text-slate-600 text-xs">JPG, PNG up to 10MB</p>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Name */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Full Name <span className="text-rose-400">*</span>
                        </label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            placeholder="Enter staff name"
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder:text-slate-600 focus:outline-none focus:border-cyan-400"
                        />
                    </div>

                    {/* Role */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Role <span className="text-rose-400">*</span>
                        </label>
                        <select
                            value={formData.role}
                            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                        >
                            <option value="">Select role</option>
                            {roles.map(role => (
                                <option key={role} value={role}>{role}</option>
                            ))}
                        </select>
                    </div>

                    {/* Department */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Department <span className="text-rose-400">*</span>
                        </label>
                        <select
                            value={formData.department}
                            onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400"
                        >
                            <option value="">Select department</option>
                            {departments.map(dept => (
                                <option key={dept} value={dept}>{dept}</option>
                            ))}
                        </select>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-slate-800">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={submitting}
                            className={`px-4 py-2 ${ABSOLUTE_BG_ACCENT} hover:bg-cyan-300 text-slate-900 font-semibold rounded-lg flex items-center gap-2 transition-colors ${submitting ? "opacity-50 cursor-not-allowed" : ""
                                }`}
                        >
                            {submitting ? (
                                <>
                                    <span className="animate-spin">⏳</span> Registering...
                                </>
                            ) : (
                                <>
                                    <FiUserPlus size={18} /> Register Staff
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// ============================================
// ALERT THRESHOLDS TAB
// ============================================
function AlertThresholdsTab() {
    return (
        <div className="animate-in fade-in duration-300">
            <div className="mb-6">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    <div className={`w-2 h-6 ${ABSOLUTE_BORDER_ACCENT} border-l-4 rounded-full`}></div>
                    Alert Configuration
                </h2>
                <p className="text-slate-400 text-sm mt-1 ml-4">Set detection thresholds and notification preferences</p>
            </div>

            <div className="space-y-6">
                <SettingSection
                    icon={FiClock}
                    title="Loitering Detection"
                    subtitle="loitering detection"
                    value={300}
                    unit="seconds"
                    max={600}
                    step={30}
                    enabled={true}
                />
                <SettingSection
                    icon={FiAlertTriangle}
                    title="Restricted Area Intrusion"
                    subtitle="intrusion detection"
                    value={5}
                    unit="seconds"
                    max={30}
                    step={1}
                    enabled={true}
                    startIconColor="text-rose-500"
                />
                <SettingSection
                    icon={FiUsers}
                    title="Crowd Density"
                    subtitle="crowd detection"
                    value={8}
                    unit="people"
                    max={50}
                    step={1}
                    enabled={true}
                />
                <SettingSection
                    icon={FiActivity}
                    title="Fall Detection"
                    subtitle="fall detection"
                    value={80}
                    unit="% confidence"
                    max={100}
                    step={5}
                    enabled={true}
                    startIconColor="text-amber-400"
                />
            </div>
        </div>
    );
}

// ============================================
// SUB COMPONENTS
// ============================================

function TabButton({ active, onClick, icon: Icon, label }) {
    return (
        <button
            onClick={onClick}
            className={`px-4 py-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap
             ${active
                    ? `${ABSOLUTE_BORDER_ACCENT} text-white`
                    : "border-transparent text-slate-500 hover:text-slate-300"}`
            }
        >
            <Icon size={16} />
            {label}
        </button>
    )
}

function SettingSection({ icon: Icon, title, subtitle, value, unit, max, step, enabled, startIconColor, noSlider }) {
    const [val, setVal] = useState(value);
    const [isOn, setIsOn] = useState(enabled);
    const [email, setEmail] = useState(true);
    const [push, setPush] = useState(true);

    return (
        <div className={`p-6 bg-card border border-slate-800 rounded-xl transition-opacity ${isOn ? 'opacity-100' : 'opacity-60'}`}>
            <div className="flex justify-between items-start mb-6">
                <div className="flex items-center gap-3">
                    {Icon && <Icon className={`${startIconColor || 'text-slate-400'}`} size={24} />}
                    <div>
                        <h3 className="text-white font-medium text-lg">{title}</h3>
                        <p className="text-slate-500 text-xs lowercase">{subtitle}</p>
                    </div>
                </div>

                <div
                    className={`w-12 h-6 rounded-full cursor-pointer relative transition-colors ${isOn ? ABSOLUTE_BG_ACCENT : 'bg-slate-700'}`}
                    onClick={() => setIsOn(!isOn)}
                >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-slate-900 shadow-sm transition-all ${isOn ? 'left-7' : 'left-1'}`}></div>
                </div>
            </div>

            {!noSlider && (
                <div className="mb-6">
                    <div className="flex justify-between text-sm mb-2">
                        <span className="text-slate-400 font-medium">Threshold Value</span>
                        <span className={`font-mono ${ABSOLUTE_ACCENT}`}>{val} {unit}</span>
                    </div>
                    <input
                        type="range"
                        min="1"
                        max={max}
                        step={step}
                        value={val}
                        onChange={(e) => setVal(e.target.value)}
                        className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                </div>
            )}

            <div className="flex items-center gap-8">
                <ToggleLabel label="Email Notifications" checked={email} onChange={setEmail} />
                <ToggleLabel label="Push Notifications" checked={push} onChange={setPush} />
            </div>
        </div>
    )
}

function ToggleLabel({ label, checked, onChange }) {
    return (
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => onChange(!checked)}>
            <div className={`w-10 h-5 rounded-full relative transition-colors ${checked ? ABSOLUTE_BG_ACCENT : 'bg-slate-700'}`}>
                <div className={`absolute top-1 w-3 h-3 rounded-full bg-slate-900 shadow-sm transition-all ${checked ? 'left-6' : 'left-1'}`}></div>
            </div>
            <span className="text-slate-300 text-sm font-medium">{label}</span>
        </div>
    )
}
