import api from './api'

export interface Alert {
  alert_id: string
  scenario_code: string
  customer_id: string
  account_id: string
  status: string
  severity: string
  risk_score?: number
  created_at: string
  started_investigating_at?: string
  resolved_at?: string
}

export interface Resolution {
  resolution_id: string
  alert_id: string
  recommendation: string
  rationale: string
  confidence: number
  created_at: string
  findings: Record<string, any>
  context: Record<string, any>
}

export interface EvaluationReport {
  alert_id: string
  report_content: string
  metadata: Record<string, any>
  next_steps?: string
  generated_at: string
  format: string
  can_send_email?: boolean
  email_sent?: boolean
  email_sent_at?: string
  email_sent_to?: string
}

export interface TimelineEvent {
  event_id?: string
  event: string
  timestamp: string
  data: Record<string, any>
  agent_name?: string
}

export interface DashboardMetrics {
  total_alerts: number
  alerts_by_status: Record<string, number>
  alerts_by_scenario: Record<string, number>
  resolution_distribution: Record<string, number>
  avg_resolution_time_seconds: number
}

export const alertService = {
  async ingestAlert(data: {
    alert_id: string
    scenario_code: string
    customer_id: string
    account_id: string
    severity: string
    description?: string
  }) {
    const response = await api.post('/alerts/ingest', data)
    return response.data
  },

  async listAlerts(filters?: { status?: string; scenario?: string; limit?: number }) {
    const response = await api.get('/alerts/list', { params: filters })
    return response.data
  },

  async getAlert(alertId: string) {
    const response = await api.get(`/alerts/${alertId}`)
    return response.data as Alert
  },

  async investigateAlert(alertId: string, force = false) {
    const response = await api.post(`/alerts/${alertId}/investigate`, { force })
    return response.data
  },

  async getResolution(alertId: string) {
    const response = await api.get(`/resolutions/${alertId}`)
    return response.data as Resolution
  },

  async getEvaluationReport(alertId: string) {
    const response = await api.get(`/alerts/${alertId}/evaluation-report`)
    return response.data as EvaluationReport
  },

  async sendReportEmail(alertId: string) {
    const response = await api.post(`/alerts/${alertId}/send-report-email`)
    return response.data
  },

  async getDashboardMetrics() {
    const response = await api.get('/analytics/dashboard')
    return response.data as DashboardMetrics
  },

  async getTimeline(alertId: string) {
    const response = await api.get(`/alerts/${alertId}/timeline`)
    return response.data.events as TimelineEvent[]
  },
}

export const authService = {
  async register(username: string, email: string, password: string) {
    const response = await api.post('/auth/register', { username, email, password })
    return response.data
  },

  async login(username: string, password: string) {
    const response = await api.post('/auth/login', { username, password })
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token)
      localStorage.setItem('user_id', response.data.user_id)
      localStorage.setItem('username', response.data.username)
    }
    return response.data
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('username')
  },

  getAccessToken() {
    return localStorage.getItem('access_token')
  },

  getUsername() {
    return localStorage.getItem('username')
  },

  isAuthenticated() {
    return !!localStorage.getItem('access_token')
  },
}

