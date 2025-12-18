import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAlerts } from '../hooks'
import { AlertCard } from '../components/AlertCard'
import { Search, Filter, RefreshCw, TestTube } from 'lucide-react'

export const Dashboard: React.FC = () => {
  const { alerts, loading } = useAlerts()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedScenario, setSelectedScenario] = useState('')

  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch =
      alert.alert_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      alert.customer_id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesScenario = !selectedScenario || alert.scenario_code === selectedScenario
    return matchesSearch && matchesScenario
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 animate-fade-in">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="text-4xl font-bold text-slate-900 mb-2">Alert Dashboard</h1>
              <p className="text-slate-600">Real-time transaction monitoring and investigation</p>
            </div>
            <Link
              to="/test-scenarios"
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
            >
              <TestTube className="w-5 h-5" />
              <span className="font-medium">Test Scenarios</span>
            </Link>
          </div>
        </div>

        {/* Search & Filter */}
        <div className="card mb-8 animate-slide-up">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by alert ID or customer..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Scenarios</option>
              <option value="VELOCITY_SPIKE">Velocity Spike</option>
              <option value="STRUCTURING">Structuring</option>
              <option value="KYC_INCONSISTENCY">KYC Inconsistency</option>
              <option value="SANCTIONS_HIT">Sanctions Hit</option>
              <option value="DORMANT_ACTIVATION">Dormant Activation</option>
            </select>
            <button className="btn btn-secondary flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Alerts Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="h-12 bg-slate-200 rounded mb-4"></div>
                <div className="h-8 bg-slate-200 rounded"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredAlerts.map((alert) => (
              <div key={alert.alert_id} className="animate-slide-up">
                <AlertCard alert={alert} onClick={() => {
                  // Navigate to details page
                  window.location.href = `/alerts/${alert.alert_id}`
                }} />
              </div>
            ))}
          </div>
        )}

        {!loading && filteredAlerts.length === 0 && (
          <div className="card text-center py-12">
            <p className="text-slate-500 text-lg">No alerts found</p>
          </div>
        )}

        {/* Summary Stats */}
        <div className="mt-8 card grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-slate-500">Total Alerts</p>
            <p className="text-3xl font-bold text-slate-900">{alerts.length}</p>
          </div>
          <div>
            <p className="text-slate-500">Open</p>
            <p className="text-3xl font-bold text-blue-600">{alerts.filter(a => a.status === 'OPEN').length}</p>
          </div>
          <div>
            <p className="text-slate-500">Investigating</p>
            <p className="text-3xl font-bold text-yellow-600">{alerts.filter(a => a.status === 'INVESTIGATING').length}</p>
          </div>
          <div>
            <p className="text-slate-500">Resolved</p>
            <p className="text-3xl font-bold text-green-600">{alerts.filter(a => a.status === 'RESOLVED').length}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

