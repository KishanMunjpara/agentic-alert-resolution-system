import React from 'react'
import { Activity, AlertCircle, CheckCircle, Clock, Zap } from 'lucide-react'
import { Alert } from '../services/apiClient'

interface AlertCardProps {
  alert: Alert
  onClick?: () => void
}

export const AlertCard: React.FC<AlertCardProps> = ({ alert, onClick }) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      default:
        return 'bg-blue-100 text-blue-800 border-blue-300'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'INVESTIGATING':
        return <Zap className="w-5 h-5 animate-pulse" />
      case 'RESOLVED':
        return <CheckCircle className="w-5 h-5" />
      default:
        return <AlertCircle className="w-5 h-5" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'INVESTIGATING':
        return 'text-blue-600'
      case 'RESOLVED':
        return 'text-green-600'
      case 'ESCALATED':
        return 'text-red-600'
      default:
        return 'text-slate-600'
    }
  }

  return (
    <div
      onClick={onClick}
      className="card cursor-pointer group hover:shadow-lg"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${getStatusColor(alert.status)} bg-opacity-10`}>
            {getStatusIcon(alert.status)}
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{alert.alert_id}</h3>
            <p className="text-sm text-slate-500">{alert.scenario_code}</p>
          </div>
        </div>
        <span className={`badge ${getSeverityColor(alert.severity)}`}>
          {alert.severity}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-slate-500">Customer</p>
          <p className="font-medium">{alert.customer_id}</p>
        </div>
        <div>
          <p className="text-slate-500">Account</p>
          <p className="font-medium">{alert.account_id}</p>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-200">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {new Date(alert.created_at).toLocaleDateString()}
          </span>
          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full ${
            alert.status === 'RESOLVED' ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700'
          }`}>
            <span className={`pulse-dot ${alert.status === 'RESOLVED' ? 'pulse-dot-success' : 'pulse-dot-warning'}`}></span>
            {alert.status}
          </span>
        </div>
      </div>
    </div>
  )
}

