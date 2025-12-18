import React, { useState, useEffect } from 'react'
import { alertService } from '../services/apiClient'
import { CheckCircle2, XCircle, Loader2, Play, Search, FileText, AlertCircle } from 'lucide-react'

interface Scenario {
  id: string
  name: string
  code: string
  description: string
  customerId: string
  accountId: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  expectedDecision?: string
}

const SCENARIOS: Scenario[] = [
  {
    id: 'A-001',
    name: 'Velocity Spike',
    code: 'VELOCITY_SPIKE',
    description: 'Multiple transactions over threshold in 48 hours',
    customerId: 'CUST-101',
    accountId: 'ACC-001',
    severity: 'HIGH',
    expectedDecision: 'ESCALATE'
  },
  {
    id: 'A-002',
    name: 'Structuring',
    code: 'STRUCTURING',
    description: 'Multiple deposits just under $10k threshold',
    customerId: 'CUST-102',
    accountId: 'ACC-002',
    severity: 'HIGH',
    expectedDecision: 'RFI'
  },
  {
    id: 'A-003',
    name: 'KYC Inconsistency',
    code: 'KYC_INCONSISTENCY',
    description: 'Transaction pattern inconsistent with declared occupation',
    customerId: 'CUST-103',
    accountId: 'ACC-003',
    severity: 'MEDIUM',
    expectedDecision: 'CLOSE'
  },
  {
    id: 'A-004',
    name: 'Sanctions Hit',
    code: 'SANCTIONS_HIT',
    description: 'Transaction with entity matching sanctions list',
    customerId: 'CUST-104',
    accountId: 'ACC-004',
    severity: 'CRITICAL',
    expectedDecision: 'ESCALATE'
  },
  {
    id: 'A-005',
    name: 'Dormant Account Activation',
    code: 'DORMANT_ACTIVATION',
    description: 'Dormant account activated with large transaction',
    customerId: 'CUST-105',
    accountId: 'ACC-005',
    severity: 'HIGH',
    expectedDecision: 'RFI'
  }
]

type StepStatus = 'pending' | 'loading' | 'success' | 'error'

interface ScenarioState {
  alertId: string | null
  steps: {
    ingest: StepStatus
    investigate: StepStatus
    checkResolution: StepStatus
  }
  alertData: any
  resolution: any
  error: string | null
}

export const ScenarioTester: React.FC = () => {
  const [scenarios, setScenarios] = useState<Record<string, ScenarioState>>({})
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null)

  useEffect(() => {
    // Initialize state for all scenarios
    const initialState: Record<string, ScenarioState> = {}
    SCENARIOS.forEach(scenario => {
      initialState[scenario.id] = {
        alertId: null,
        steps: {
          ingest: 'pending',
          investigate: 'pending',
          checkResolution: 'pending'
        },
        alertData: null,
        resolution: null,
        error: null
      }
    })
    setScenarios(initialState)
  }, [])

  const updateScenarioState = (scenarioId: string, updates: Partial<ScenarioState>) => {
    setScenarios(prev => ({
      ...prev,
      [scenarioId]: { ...prev[scenarioId], ...updates }
    }))
  }

  const updateStepStatus = (scenarioId: string, step: keyof ScenarioState['steps'], status: StepStatus) => {
    setScenarios(prev => ({
      ...prev,
      [scenarioId]: {
        ...prev[scenarioId],
        steps: {
          ...prev[scenarioId].steps,
          [step]: status
        }
      }
    }))
  }

  const handleIngest = async (scenario: Scenario) => {
    const alertId = `TEST-${scenario.id}-${Date.now()}`
    updateStepStatus(scenario.id, 'ingest', 'loading')
    updateScenarioState(scenario.id, { error: null })

    try {
      const alertData = await alertService.ingestAlert({
        alert_id: alertId,
        scenario_code: scenario.code,
        customer_id: scenario.customerId,
        account_id: scenario.accountId,
        severity: scenario.severity,
        description: scenario.description
      })

      updateScenarioState(scenario.id, {
        alertId,
        alertData,
        steps: {
          ingest: 'success',
          investigate: 'pending',
          checkResolution: 'pending'
        }
      })
    } catch (error: any) {
      updateStepStatus(scenario.id, 'ingest', 'error')
      updateScenarioState(scenario.id, {
        error: error.response?.data?.detail || error.message || 'Failed to ingest alert'
      })
    }
  }

  const handleInvestigate = async (scenario: Scenario) => {
    const state = scenarios[scenario.id]
    if (!state.alertId) return

    updateStepStatus(scenario.id, 'investigate', 'loading')
    updateScenarioState(scenario.id, { error: null })

    try {
      await alertService.investigateAlert(state.alertId, false)
      updateStepStatus(scenario.id, 'investigate', 'success')
      updateStepStatus(scenario.id, 'checkResolution', 'pending')
    } catch (error: any) {
      updateStepStatus(scenario.id, 'investigate', 'error')
      updateScenarioState(scenario.id, {
        error: error.response?.data?.detail || error.message || 'Failed to start investigation'
      })
    }
  }

  const handleCheckResolution = async (scenario: Scenario) => {
    const state = scenarios[scenario.id]
    if (!state.alertId) return

    updateStepStatus(scenario.id, 'checkResolution', 'loading')
    updateScenarioState(scenario.id, { error: null })

    try {
      const resolution = await alertService.getResolution(state.alertId)
      updateScenarioState(scenario.id, {
        resolution,
        steps: {
          ...state.steps,
          checkResolution: 'success'
        }
      })
    } catch (error: any) {
      if (error.response?.status === 404) {
        updateStepStatus(scenario.id, 'checkResolution', 'pending')
        updateScenarioState(scenario.id, {
          error: 'Resolution not yet available. Investigation may still be running. Wait a few seconds and try again.'
        })
      } else {
        updateStepStatus(scenario.id, 'checkResolution', 'error')
        updateScenarioState(scenario.id, {
          error: error.response?.data?.detail || error.message || 'Failed to get resolution'
        })
      }
    }
  }

  const resetScenario = (scenarioId: string) => {
    updateScenarioState(scenarioId, {
      alertId: null,
      steps: {
        ingest: 'pending',
        investigate: 'pending',
        checkResolution: 'pending'
      },
      alertData: null,
      resolution: null,
      error: null
    })
  }

  const getStatusIcon = (status: StepStatus) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'loading':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
    }
  }

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

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Scenario Testing Guide</h1>
          <p className="text-gray-600">
            Step-by-step testing interface for all 5 alert scenarios. Follow the buttons in order for each scenario.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {SCENARIOS.map(scenario => {
            const state = scenarios[scenario.id] || {
              alertId: null,
              steps: { ingest: 'pending', investigate: 'pending', checkResolution: 'pending' },
              alertData: null,
              resolution: null,
              error: null
            }

            return (
              <div
                key={scenario.id}
                className="bg-white rounded-lg shadow-md p-6 border-2 border-gray-200"
              >
                {/* Scenario Header */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-xl font-semibold text-gray-900">{scenario.id}: {scenario.name}</h2>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getSeverityColor(scenario.severity)}`}>
                      {scenario.severity}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{scenario.description}</p>
                  <div className="text-xs text-gray-500">
                    Customer: {scenario.customerId} | Account: {scenario.accountId}
                  </div>
                  {scenario.expectedDecision && (
                    <div className="mt-2 text-xs text-gray-500">
                      Expected Decision: <span className="font-semibold">{scenario.expectedDecision}</span>
                    </div>
                  )}
                </div>

                {/* Step-by-Step Buttons */}
                <div className="space-y-3 mb-4">
                  {/* Step 1: Ingest Alert */}
                  <div className="flex items-center gap-3">
                    {getStatusIcon(state.steps.ingest)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleIngest(scenario)}
                          disabled={state.steps.ingest === 'loading'}
                          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                        >
                          <Play className="w-4 h-4" />
                          Step 1: Ingest Alert
                        </button>
                        {state.alertId && (
                          <span className="text-xs text-gray-500">ID: {state.alertId}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Step 2: Investigate */}
                  <div className="flex items-center gap-3">
                    {getStatusIcon(state.steps.investigate)}
                    <button
                      onClick={() => handleInvestigate(scenario)}
                      disabled={state.steps.ingest !== 'success' || state.steps.investigate === 'loading'}
                      className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                    >
                      <Search className="w-4 h-4" />
                      Step 2: Start Investigation
                    </button>
                  </div>

                  {/* Step 3: Check Resolution */}
                  <div className="flex items-center gap-3">
                    {getStatusIcon(state.steps.checkResolution)}
                    <button
                      onClick={() => handleCheckResolution(scenario)}
                      disabled={state.steps.investigate !== 'success' || state.steps.checkResolution === 'loading'}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                    >
                      <FileText className="w-4 h-4" />
                      Step 3: Check Resolution
                    </button>
                  </div>

                  {/* Reset Button */}
                  {(state.steps.ingest === 'success' || state.steps.ingest === 'error') && (
                    <button
                      onClick={() => resetScenario(scenario.id)}
                      className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
                    >
                      Reset Scenario
                    </button>
                  )}
                </div>

                {/* Error Message */}
                {state.error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-red-700">{state.error}</p>
                    </div>
                  </div>
                )}

                {/* Alert Data */}
                {state.alertData && (
                  <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="text-xs font-semibold text-blue-900 mb-1">Alert Created:</div>
                    <div className="text-xs text-blue-700">
                      Status: <span className="font-medium">{state.alertData.status}</span> | 
                      Created: <span className="font-medium">{new Date(state.alertData.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                )}

                {/* Resolution Data */}
                {state.resolution && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="text-sm font-semibold text-green-900 mb-2">✅ Resolution Received:</div>
                    <div className="space-y-1 text-xs">
                      <div>
                        <span className="font-medium text-green-800">Recommendation:</span>{' '}
                        <span className="text-green-700">{state.resolution.recommendation}</span>
                      </div>
                      <div>
                        <span className="font-medium text-green-800">Confidence:</span>{' '}
                        <span className="text-green-700">{state.resolution.confidence}%</span>
                      </div>
                      <div>
                        <span className="font-medium text-green-800">Rationale:</span>{' '}
                        <span className="text-green-700">{state.resolution.rationale}</span>
                      </div>
                      {scenario.expectedDecision && (
                        <div className="mt-2 pt-2 border-t border-green-300">
                          <span className="font-medium text-green-800">Expected:</span>{' '}
                          <span className={`font-semibold ${
                            state.resolution.recommendation === scenario.expectedDecision
                              ? 'text-green-700'
                              : 'text-orange-700'
                          }`}>
                            {scenario.expectedDecision}
                            {state.resolution.recommendation === scenario.expectedDecision ? ' ✓' : ' ✗'}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">📋 How to Use</h3>
          <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
            <li>Click <strong>"Step 1: Ingest Alert"</strong> to create an alert for the scenario</li>
            <li>Wait for Step 1 to complete (green checkmark), then click <strong>"Step 2: Start Investigation"</strong></li>
            <li>Wait for Step 2 to complete, then click <strong>"Step 3: Check Resolution"</strong></li>
            <li>If resolution is not ready, wait 10-15 seconds and click Step 3 again</li>
            <li>Compare the received recommendation with the expected decision</li>
            <li>Use <strong>"Reset Scenario"</strong> to test the same scenario again</li>
          </ol>
        </div>
      </div>
    </div>
  )
}

