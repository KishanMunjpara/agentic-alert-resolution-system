import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAlert, useWebSocket } from '../hooks'
import { alertService, EvaluationReport, TimelineEvent } from '../services/apiClient'
import { InvestigationTimeline } from '../components/Timeline'
import { ArrowLeft, Play, FileText, X, Mail, CheckCircle } from 'lucide-react'

// Helper function to parse report content into sections
const parseReportContent = (content: string) => {
  const sections: Record<string, string> = {}
  
  // Extract sections using the divider pattern
  const parts = content.split('───────────────────────────────────────────────────────────────────────────────')
  
  parts.forEach((part, index) => {
    const trimmed = part.trim()
    if (trimmed.includes('EXECUTIVE SUMMARY')) {
      sections.executiveSummary = trimmed.split('EXECUTIVE SUMMARY')[1]?.split('EVALUATION DETAILS')[0]?.trim() || ''
    } else if (trimmed.includes('EVALUATION DETAILS')) {
      sections.evaluationDetails = trimmed.split('EVALUATION DETAILS')[1]?.split('NEXT STEPS')[0]?.trim() || ''
    } else if (trimmed.includes('NEXT STEPS')) {
      sections.nextSteps = trimmed.split('NEXT STEPS')[1]?.split('CONTACT INFORMATION')[0]?.trim() || ''
    } else if (trimmed.includes('CONTACT INFORMATION')) {
      sections.contactInfo = trimmed.split('CONTACT INFORMATION')[1]?.split('IMPORTANT NOTES')[0]?.trim() || ''
    }
  })
  
  // If parsing failed, try simpler approach
  if (!sections.evaluationDetails) {
    const evalMatch = content.match(/EVALUATION DETAILS[\s\S]*?(?=NEXT STEPS|CONTACT INFORMATION|$)/i)
    if (evalMatch) {
      sections.evaluationDetails = evalMatch[0].replace(/EVALUATION DETAILS/gi, '').replace(/─+/g, '').trim()
    }
  }
  
  return sections
}

export const AlertDetails: React.FC = () => {
  const { alertId } = useParams<{ alertId: string }>()
  const { alert, loading, error, investigate } = useAlert(alertId!)
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [resolution, setResolution] = useState(null)
  const [investigating, setInvestigating] = useState(false)
  const [evaluationReport, setEvaluationReport] = useState<EvaluationReport | null>(null)
  const [showReport, setShowReport] = useState(false)
  const [loadingReport, setLoadingReport] = useState(false)
  const [sendingEmail, setSendingEmail] = useState(false)
  const [emailSent, setEmailSent] = useState(false)

  useWebSocket((message) => {
    // Debug: Log all WebSocket messages
    console.log('WebSocket message received:', message)
    console.log('Comparing alert_id:', {
      message_alert_id: message.data?.alert_id,
      current_alertId: alertId,
      match: message.data?.alert_id === alertId
    })
    
    // Check if this event is for the current alert
    const eventAlertId = message.data?.alert_id || message.alert_id
    if (eventAlertId === alertId) {
      console.log('Adding event to timeline:', message.event)
      setTimeline((prev) => [
        ...prev,
        {
          timestamp: message.timestamp,
          event: message.event,
          data: message.data,
        },
      ])

      // If decision made, fetch resolution
      if (message.event === 'decision_made') {
        fetchResolution()
        // Also try to fetch evaluation report if resolution exists
        setTimeout(() => {
          fetchEvaluationReport()
        }, 1000)
      }
    } else {
      console.log('Event filtered out - alert_id mismatch:', {
        event_alert_id: eventAlertId,
        current_alertId: alertId
      })
    }
  })

  const fetchResolution = async () => {
    try {
      const res = await alertService.getResolution(alertId!)
      setResolution(res)
      return res
    } catch (err: any) {
      // 404 is expected if no resolution exists yet - that's okay
      if (err.response?.status !== 404) {
        console.error('Failed to fetch resolution:', err)
      }
      // Don't set resolution if it doesn't exist
      setResolution(null)
      throw err
    }
  }

  const fetchEvaluationReport = async () => {
    // Allow fetching even without resolution (it will check on backend)
    setLoadingReport(true)
    try {
      const report = await alertService.getEvaluationReport(alertId!)
      setEvaluationReport(report)
    } catch (err: any) {
      // 404 is expected if resolution doesn't exist yet - that's okay
      if (err.response?.status !== 404) {
        console.error('Failed to fetch evaluation report:', err)
      }
      // Report might not be available yet, that's okay
    } finally {
      setLoadingReport(false)
    }
  }

  const handleViewReport = async () => {
    if (!evaluationReport && !loadingReport) {
      await fetchEvaluationReport()
    }
    setShowReport(true)
    // Check if email was already sent after fetching
    if (evaluationReport?.email_sent) {
      setEmailSent(true)
    }
  }

  // Fetch timeline events on page load
  const fetchTimeline = async () => {
    if (!alertId) return
    try {
      const events = await alertService.getTimeline(alertId)
      if (events && events.length > 0) {
        setTimeline(events)
      }
    } catch (err: any) {
      // 404 is expected if no events exist yet - that's okay
      if (err.response?.status !== 404) {
        console.error('Failed to fetch timeline:', err)
      }
    }
  }

  // Automatically fetch resolution and timeline when page loads (if investigation already done)
  useEffect(() => {
    if (alertId && !loading) {
      // Fetch timeline events
      fetchTimeline()
      
      // Try to fetch resolution automatically
      fetchResolution().then(() => {
        // If resolution was fetched successfully, also try to fetch evaluation report
        // We'll check resolution state in another effect
      }).catch((err) => {
        // 404 is expected if no resolution exists yet - that's okay
        if (err.response?.status !== 404) {
          console.error('Failed to fetch resolution on page load:', err)
        }
      })
    }
  }, [alertId, loading])

  // Fetch evaluation report when resolution is available
  useEffect(() => {
    if (resolution && !evaluationReport && !loadingReport) {
      // Small delay to ensure resolution is fully set
      setTimeout(() => {
        fetchEvaluationReport()
      }, 500)
    }
  }, [resolution])

  // Update email sent status when report is fetched
  useEffect(() => {
    if (evaluationReport?.email_sent) {
      setEmailSent(true)
    }
  }, [evaluationReport])

  const handleSendEmail = async () => {
    if (!alertId) return
    setSendingEmail(true)
    try {
      await alertService.sendReportEmail(alertId)
      setEmailSent(true)
      // Refresh the report to get updated email status
      await fetchEvaluationReport()
      alert('Email sent successfully!')
    } catch (err: any) {
      console.error('Failed to send email:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Unknown error'
      alert(`Failed to send email: ${errorMessage}`)
    } finally {
      setSendingEmail(false)
    }
  }

  const handleInvestigate = async () => {
    setInvestigating(true)
    setTimeline([])
    try {
      await investigate()
    } finally {
      setInvestigating(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-12 bg-slate-200 rounded"></div>
            <div className="h-64 bg-slate-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !alert) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="card text-center py-12">
            <p className="text-red-600 text-lg">{error || 'Alert not found'}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-4">
            <button
              onClick={() => window.history.back()}
              className="p-2 hover:bg-slate-200 rounded-lg transition"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-slate-900">{alert.alert_id}</h1>
              <p className="text-slate-600">{alert.scenario_code}</p>
            </div>
          </div>
          <button
            onClick={handleInvestigate}
            disabled={investigating}
            className="btn btn-primary flex items-center gap-2"
          >
            <Play className="w-4 h-4" />
            {investigating ? 'Investigating...' : 'Start Investigation'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Alert Details */}
          <div className="lg:col-span-1">
            <div className="card animate-slide-up">
              <h3 className="text-lg font-semibold mb-4">Alert Details</h3>
              <dl className="space-y-4">
                <div>
                  <dt className="text-sm text-slate-500">Status</dt>
                  <dd className="font-semibold text-slate-900">{alert.status}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500">Severity</dt>
                  <dd className="font-semibold text-slate-900">{alert.severity}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500">Customer ID</dt>
                  <dd className="font-semibold text-slate-900">{alert.customer_id}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500">Account ID</dt>
                  <dd className="font-semibold text-slate-900">{alert.account_id}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500">Created</dt>
                  <dd className="font-semibold text-slate-900">
                    {new Date(alert.created_at).toLocaleString()}
                  </dd>
                </div>
              </dl>
            </div>

            {resolution && (
              <div className="card mt-6 animate-slide-up">
                <h3 className="text-lg font-semibold mb-4">Resolution</h3>
                <dl className="space-y-4">
                  <div>
                    <dt className="text-sm text-slate-500">Recommendation</dt>
                    <dd className={`font-semibold ${
                      resolution.recommendation === 'ESCALATE' ? 'text-red-600' :
                      resolution.recommendation === 'CLOSE' ? 'text-green-600' :
                      'text-blue-600'
                    }`}>{resolution.recommendation}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-slate-500">Confidence</dt>
                    <dd className="font-semibold">{(resolution.confidence * 100).toFixed(0)}%</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-slate-500 mb-2">Rationale</dt>
                    <dd className="text-sm text-slate-700">{resolution.rationale}</dd>
                  </div>
                </dl>
                <div className="pt-4 mt-4 border-t">
                  <button
                    onClick={handleViewReport}
                    disabled={loadingReport}
                    className="btn btn-secondary w-full flex items-center justify-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    {loadingReport ? 'Loading...' : 'View Evaluation Report'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Timeline */}
          <div className="lg:col-span-2">
            <InvestigationTimeline events={timeline} isLoading={investigating} />
          </div>
        </div>

        {/* Evaluation Report Modal */}
        {showReport && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
              <div className="flex items-center justify-between p-6 border-b">
                <h2 className="text-2xl font-bold text-slate-900">Evaluation Report</h2>
                <button
                  onClick={() => setShowReport(false)}
                  className="p-2 hover:bg-slate-100 rounded-lg transition"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
                {evaluationReport ? (() => {
                  const sections = parseReportContent(evaluationReport.report_content)
                  return (
                    <div className="bg-white rounded-lg shadow-sm p-8 max-w-3xl mx-auto">
                      {/* Report Header */}
                      <div className="text-center border-b-2 border-slate-200 pb-6 mb-6">
                        <h1 className="text-2xl font-bold text-slate-900 mb-2">Transaction Evaluation Report</h1>
                        <div className="text-sm text-slate-600 space-y-1">
                          <p><strong>Report Date:</strong> {new Date(evaluationReport.generated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
                          <p><strong>Alert ID:</strong> {evaluationReport.alert_id}</p>
                          {evaluationReport.metadata?.customer_name && (
                            <p><strong>Customer:</strong> {evaluationReport.metadata.customer_name} (ID: {evaluationReport.metadata.customer_id})</p>
                          )}
                        </div>
                      </div>

                      {/* Executive Summary */}
                      <div className="mb-8">
                        <h2 className="text-xl font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-200">Executive Summary</h2>
                        <div className="bg-blue-50 rounded-lg p-4 mb-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-sm text-slate-600 mb-1">Resolution</p>
                              <p className={`font-semibold text-lg ${
                                evaluationReport.metadata?.recommendation === 'ESCALATE' ? 'text-red-600' :
                                evaluationReport.metadata?.recommendation === 'CLOSE' ? 'text-green-600' :
                                'text-blue-600'
                              }`}>
                                {evaluationReport.metadata?.recommendation || 'N/A'}
                              </p>
                            </div>
                            <div>
                              <p className="text-sm text-slate-600 mb-1">Confidence Level</p>
                              <p className="font-semibold text-lg text-slate-900">
                                {((evaluationReport.metadata?.confidence || 0) * 100).toFixed(1)}%
                              </p>
                            </div>
                          </div>
                        </div>
                        <p className="text-slate-700 leading-relaxed">
                          This report summarizes the evaluation of recent account activity and provides guidance on next steps.
                        </p>
                      </div>

                      {/* Evaluation Details */}
                      <div className="mb-8">
                        <h2 className="text-xl font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-200">Evaluation Details</h2>
                        <div className="text-slate-700 leading-relaxed">
                          {(() => {
                            let content = sections.evaluationDetails || evaluationReport.report_content
                              .replace(/╔═+╗/g, '')
                              .replace(/║[^║]*║/g, '')
                              .replace(/╚═+╝/g, '')
                              .replace(/─+/g, '')
                              .replace(/EXECUTIVE SUMMARY[\s\S]*?EVALUATION DETAILS/gi, 'EVALUATION DETAILS')
                              .replace(/EVALUATION DETAILS/gi, '')
                              .replace(/NEXT STEPS[\s\S]*/gi, '')
                              .trim()
                            
                            // Remove placeholders
                            content = content
                              .replace(/\[Your Name\]/g, '')
                              .replace(/\[Bank Name\]/g, '')
                              .replace(/\[Company Name\]/g, '')
                              .replace(/\[Compliance Department Contact Information\]/g, 'our compliance department')
                            
                            // Split content into paragraphs and process each
                            const paragraphs = content.split(/\n\n+/).filter(p => p.trim())
                            
                            return (
                              <div className="space-y-4">
                                {paragraphs.map((para, idx) => {
                                  // Check if this is a section header (starts with **)
                                  if (para.match(/^\*\*[^*]+\*\*/)) {
                                    const headerText = para.replace(/\*\*/g, '').replace(/:/g, '').trim()
                                    return (
                                      <h3 key={idx} className="font-semibold text-slate-900 mt-6 mb-2 text-lg">
                                        {headerText}
                                      </h3>
                                    )
                                  }
                                  
                                  // Process regular paragraphs - convert markdown to JSX
                                  const processedPara = para
                                    .replace(/\*\*([^*]+)\*\*/g, (match, text) => `<strong>${text}</strong>`)
                                    .replace(/\*([^*]+)\*/g, (match, text) => `<em>${text}</em>`)
                                  
                                  return (
                                    <p key={idx} className="whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: processedPara }} />
                                  )
                                })}
                              </div>
                            )
                          })()}
                        </div>
                      </div>

                      {/* Next Steps */}
                      {(evaluationReport.next_steps || sections.nextSteps) && (
                        <div className="mb-8">
                          <h2 className="text-xl font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-200">Next Steps</h2>
                          <div className="bg-blue-50 rounded-lg p-4">
                            <div className="text-slate-800 whitespace-pre-wrap text-sm leading-relaxed">
                              {evaluationReport.next_steps || sections.nextSteps}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Contact Information */}
                      <div className="mb-8 p-4 bg-slate-100 rounded-lg">
                        <h3 className="font-semibold text-slate-900 mb-3">Contact Information</h3>
                        <p className="text-sm text-slate-700 mb-2">
                          If you have questions or need assistance, please contact our Compliance Team:
                        </p>
                        <ul className="text-sm text-slate-700 space-y-1">
                          <li><strong>Email:</strong> compliance@bank.com</li>
                          <li><strong>Phone:</strong> 1-800-COMPLIANCE</li>
                          <li><strong>Hours:</strong> Monday - Friday, 9:00 AM - 5:00 PM EST</li>
                        </ul>
                      </div>

                      {/* Footer */}
                      <div className="mt-8 pt-6 border-t border-slate-200 text-xs text-slate-500 text-center">
                        <p>Generated: {new Date(evaluationReport.generated_at).toLocaleString()}</p>
                        <p>Report ID: RPT-{evaluationReport.alert_id}</p>
                      </div>
                    </div>
                  )
                })() : (
                  <div className="text-center py-12">
                    <p className="text-slate-600">Loading evaluation report...</p>
                  </div>
                )}
              </div>
              <div className="p-6 border-t flex justify-between items-center">
                <div>
                  {evaluationReport?.email_sent && (
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="text-sm font-medium">
                        Email sent {evaluationReport.email_sent_at 
                          ? `on ${new Date(evaluationReport.email_sent_at).toLocaleString()}`
                          : ''}
                        {evaluationReport.email_sent_to && ` to ${evaluationReport.email_sent_to}`}
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex gap-3">
                  {evaluationReport?.can_send_email && !emailSent && (
                    <button
                      onClick={handleSendEmail}
                      disabled={sendingEmail}
                      className="btn btn-secondary flex items-center gap-2"
                    >
                      <Mail className="w-4 h-4" />
                      {sendingEmail ? 'Sending...' : 'Send Email'}
                    </button>
                  )}
                  <button
                    onClick={() => setShowReport(false)}
                    className="btn btn-primary"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

