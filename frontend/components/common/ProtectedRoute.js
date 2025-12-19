"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "./AuthProvider"

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    // 🔄 Auth loaded, but no user → login
    if (!loading && !user) {
      router.replace("/")
    }

    // ❌ User present but role not allowed
    if (!loading && user && roles && !roles.includes(user.role)) {
      router.replace("/unauthorized")
    }
  }, [user, loading, roles, router])

  //  While checking auth
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-500">
        Checking access...
      </div>
    )
  }

  //  No user
  if (!user) return null

  //  Role not allowed
  if (roles && !roles.includes(user.role)) return null

  //  Access granted
  return children
}
