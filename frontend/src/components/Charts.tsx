import React from 'react'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { DashboardMetrics } from '../services/apiClient'

interface ChartProps {
  data: DashboardMetrics
}

export const ScenarioChart: React.FC<ChartProps> = ({ data }) => {
  const chartData = Object.entries(data.alerts_by_scenario).map(([name, value]) => ({
    name,
    value,
  }))

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Alerts by Scenario</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="value" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export const ResolutionChart: React.FC<ChartProps> = ({ data }) => {
  const chartData = Object.entries(data.resolution_distribution).map(([name, value]) => ({
    name,
    value,
  }))

  const COLORS = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6']

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Resolution Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, value }) => `${name}: ${value}`}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export const StatusMetrics: React.FC<ChartProps> = ({ data }) => {
  const metrics = [
    { label: 'Open', value: data.alerts_by_status.OPEN, color: 'bg-blue-500', icon: '⏱️' },
    { label: 'Investigating', value: data.alerts_by_status.INVESTIGATING, color: 'bg-yellow-500', icon: '🔍' },
    { label: 'Resolved', value: data.alerts_by_status.RESOLVED, color: 'bg-green-500', icon: '✓' },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {metrics.map((metric) => (
        <div key={metric.label} className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-500 text-sm">{metric.label}</p>
              <p className="text-3xl font-bold text-slate-900">{metric.value}</p>
            </div>
            <div className={`${metric.color} w-12 h-12 rounded-lg flex items-center justify-center text-2xl`}>
              {metric.icon}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

