import React from 'react'
import { AlertCircle, Zap, Info, CheckCircle, FileText, User, Clock, Target, MessageSquare } from 'lucide-react'

interface TimelineEvent {
  timestamp: string
  event: string
  data: Record<string, any>
}

interface TimelineProps {
  events: TimelineEvent[]
  isLoading?: boolean
}

export const InvestigationTimeline: React.FC<TimelineProps> = ({ events, isLoading }) => {
  const getEventIcon = (event: string) => {
    switch (event) {
      case 'investigation_started':
        return <Zap className="w-5 h-5 text-blue-600" />
      case 'investigator_finding':
        return <AlertCircle className="w-5 h-5 text-yellow-600" />
      case 'decision_made':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'action_executed':
        return <Target className="w-5 h-5 text-purple-600" />
      case 'investigation_complete':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'investigation_skipped':
        return <Info className="w-5 h-5 text-slate-600" />
      default:
        return <Info className="w-5 h-5 text-slate-600" />
    }
  }

  const getEventColor = (event: string) => {
    switch (event) {
      case 'investigation_started':
        return 'bg-blue-50 border-blue-200'
      case 'investigator_finding':
        return 'bg-yellow-50 border-yellow-200'
      case 'decision_made':
        return 'bg-green-50 border-green-200'
      case 'action_executed':
        return 'bg-purple-50 border-purple-200'
      case 'investigation_complete':
        return 'bg-green-50 border-green-200'
      case 'investigation_skipped':
        return 'bg-slate-50 border-slate-200'
      default:
        return 'bg-slate-50 border-slate-200'
    }
  }

  const formatEventData = (event: string, data: Record<string, any>) => {
    // Format action_executed events
    if (event === 'action_executed') {
      const actionType = data.action_type || data.result?.action || 'UNKNOWN'
      const result = data.result || {}
      
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-purple-600" />
            <span className="font-semibold text-purple-700">Action Type:</span>
            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-md text-sm font-medium">
              {actionType}
            </span>
          </div>
          
          {result.status && (
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="font-semibold text-slate-700">Status:</span>
              <span className={`px-2 py-1 rounded-md text-sm font-medium ${
                result.status === 'ROUTED_TO_QUEUE' || result.status === 'SENT' 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {result.status}
              </span>
            </div>
          )}
          
          {result.message && (
            <div className="mt-3 p-3 bg-white rounded-md border border-purple-200">
              <div className="flex items-start gap-2">
                <MessageSquare className="w-4 h-4 text-purple-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-700 mb-1">Message:</p>
                  <p className="text-sm text-slate-600 whitespace-pre-wrap">{result.message}</p>
                </div>
              </div>
            </div>
          )}
          
          {result.customer && (
            <div className="mt-3 p-3 bg-white rounded-md border border-purple-200">
              <div className="flex items-start gap-2">
                <User className="w-4 h-4 text-purple-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-700 mb-2">Customer Information:</p>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-slate-500">Name:</span>
                      <span className="ml-2 font-medium text-slate-700">{result.customer.name || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">ID:</span>
                      <span className="ml-2 font-medium text-slate-700">{result.customer.id || 'N/A'}</span>
                    </div>
                    {result.customer.email && (
                      <div className="col-span-2">
                        <span className="text-slate-500">Email:</span>
                        <span className="ml-2 font-medium text-slate-700">{result.customer.email}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {result.rationale && (
            <div className="mt-3 p-3 bg-white rounded-md border border-purple-200">
              <p className="text-sm font-medium text-slate-700 mb-1">Rationale:</p>
              <p className="text-sm text-slate-600">{result.rationale}</p>
            </div>
          )}
          
          {result.confidence !== undefined && (
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Confidence:</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-sm font-medium">
                {(result.confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}
          
          {result.timestamp && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Clock className="w-3 h-3" />
              <span>{new Date(result.timestamp).toLocaleString()}</span>
            </div>
          )}
        </div>
      )
    }
    
    // Format decision_made events
    if (event === 'decision_made') {
      return (
        <div className="space-y-2">
          {data.recommendation && (
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Recommendation:</span>
              <span className={`px-2 py-1 rounded-md text-sm font-medium ${
                data.recommendation === 'ESCALATE' ? 'bg-red-100 text-red-800' :
                data.recommendation === 'CLOSE' ? 'bg-green-100 text-green-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {data.recommendation}
              </span>
            </div>
          )}
          {data.rationale && (
            <div className="mt-2 p-2 bg-white rounded-md">
              <p className="text-sm text-slate-600">{data.rationale}</p>
            </div>
          )}
          {data.confidence !== undefined && (
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Confidence:</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-sm font-medium">
                {(data.confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )
    }
    
    // Format investigation_complete events
    if (event === 'investigation_complete') {
      return (
        <div className="space-y-2">
          {data.final_resolution && (
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Final Resolution:</span>
              <span className={`px-2 py-1 rounded-md text-sm font-medium ${
                data.final_resolution === 'ESCALATE' ? 'bg-red-100 text-red-800' :
                data.final_resolution === 'CLOSE' ? 'bg-green-100 text-green-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {data.final_resolution}
              </span>
            </div>
          )}
          {data.duration_ms && (
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-600" />
              <span className="text-sm text-slate-600">
                Duration: {(data.duration_ms / 1000).toFixed(2)}s
              </span>
            </div>
          )}
        </div>
      )
    }
    
    // Format investigation_skipped events
    if (event === 'investigation_skipped') {
      return (
        <div className="space-y-2">
          <p className="text-sm text-slate-600">{data.reason || 'Investigation skipped'}</p>
          {data.existing_resolution && (
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Existing Resolution:</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-sm font-medium">
                {data.existing_resolution}
              </span>
            </div>
          )}
        </div>
      )
    }
    
    // Format investigator_finding events
    if (event === 'investigator_finding') {
      return (
        <div className="space-y-2">
          {data.findings && typeof data.findings === 'object' && (
            <div className="p-2 bg-white rounded-md">
              <p className="text-sm font-medium text-slate-700 mb-1">Findings:</p>
              <pre className="text-xs text-slate-600 whitespace-pre-wrap">
                {JSON.stringify(data.findings, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )
    }
    
    // Default: show formatted JSON for other events
    if (Object.keys(data).length > 0) {
      // Filter out common fields that are less interesting
      const filteredData = { ...data }
      delete filteredData.alert_id
      delete filteredData.timestamp
      
      if (Object.keys(filteredData).length > 0) {
        return (
          <div className="p-2 bg-white rounded-md">
            <pre className="text-xs text-slate-600 whitespace-pre-wrap overflow-x-auto">
              {JSON.stringify(filteredData, null, 2)}
            </pre>
          </div>
        )
      }
    }
    
    return null
  }

  if (isLoading) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 bg-slate-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-6">Investigation Timeline</h3>
      <div className="space-y-4">
        {events.length === 0 ? (
          <p className="text-slate-500 text-center py-8">No events yet...</p>
        ) : (
          events.map((event, index) => (
            <div key={index} className={`p-4 rounded-lg border ${getEventColor(event.event)} animate-slide-up`}>
              <div className="flex items-start gap-4">
                <div className="mt-1">{getEventIcon(event.event)}</div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold text-slate-900 capitalize">
                      {event.event.replace(/_/g, ' ')}
                    </h4>
                    <span className="text-xs text-slate-500">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="mt-3">
                    {formatEventData(event.event, event.data)}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
