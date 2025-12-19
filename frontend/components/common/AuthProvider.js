"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { login as loginApi, fetchMe } from "../../services/authService";
import api from "../../services/api";
import { useRouter } from "next/navigation";

const AuthContext = createContext(undefined);

export function AuthProvider({ children }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    api.defaults.headers.Authorization = `Bearer ${token}`;
    fetchMe()
      .then((res) => {
        if (res?.role) setUser(res);
        else if (res?.user) setUser(res.user);
        else setUser(null);
      })
      .catch(() => {
        localStorage.removeItem("token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (credentials) => {
    setLoading(true);
    setError("");

    try {
      if (process.env.NEXT_PUBLIC_TEMP_AUTH === "true") {
        if (
          credentials.username === "admin" &&
          credentials.password === "admin123"
        ) {
          const fakeToken = "temp-admin-token";
          localStorage.setItem("token", fakeToken);
          api.defaults.headers.Authorization = `Bearer ${fakeToken}`;
          setUser({ role: "admin", username: "admin" });
          setLoading(false);
          router.push("/dashboard");
          return;
        }
        throw new Error("Invalid temp credentials");
      }

      const data = await loginApi(credentials);
      localStorage.setItem("token", data.access_token);
      api.defaults.headers.Authorization = `Bearer ${data.access_token}`;
      setUser({ role: data.role, username: data.username });
      setLoading(false);
      router.push("/dashboard");
    } catch (err) {
      setLoading(false);
      setError(err.message || "Login failed");
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    delete api.defaults.headers.Authorization;
    setUser(null);
    router.push("/");
  };

  if (!user && !loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-10 rounded-2xl shadow-xl w-full max-w-sm transform transition-all duration-300 hover:scale-105">
          <h2 className="text-3xl font-bold mb-6 text-center">Login</h2>

          {error && (
            <div className="mb-4 text-red-600 text-sm font-medium">{error}</div>
          )}

          <LoginForm onLogin={login} loading={loading} />
          <p className="mt-4 text-center text-sm text-gray-500">
            Need to create an account?{" "}
            <a href="/register" className="text-blue-600 hover:underline">
              Create Account
            </a>
          </p>
        </div>
      </div>
    );
  }

  return children;
}

function LoginForm({ onLogin, loading }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin({ username, password });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        type="text"
        placeholder="Email"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
        required
      />
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition"
      >
        {loading ? "Logging in..." : "Login"}
      </button>
    </form>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    return {
      user: null,
      loading: true,
      login: async () => {},
      logout: () => {},
    };
  }
  return context;
};
