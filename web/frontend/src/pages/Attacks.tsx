import { useState } from 'react'
import { api } from '../services/api'
import type { AttackResponse } from '../types'
import { AttackCard, Alert } from '../components/AttackCard'
import { SecurityPipeline } from '../components/SecurityPipeline'
import { ErrorState } from '../components/MetricCard'

export function AttacksPage() {
  const [loading, setLoading] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, AttackResponse>>({})
  const [error, setError] = useState<string | null>(null)

  const launch = async (
    key: string,
    fn: () => Promise<AttackResponse>,
  ) => {
    setLoading(key)
    setError(null)
    try {
      const res = await fn()
      setResults((prev) => ({ ...prev, [key]: res }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Attack failed')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">
          Attack Simulation Center
        </h2>
        <p className="text-sm text-slate-500">
          Launch real attacks against the live verification pipeline — send a
          legitimate message first
        </p>
      </div>

      {error && <ErrorState message={error} />}

      <div className="grid gap-6 lg:grid-cols-2">
        <AttackCard
          title="Replay Attack"
          description="Attacker captures a legitimate V2V packet and retransmits it unchanged. Expected: rejected by sequence/timestamp replay protection."
          variant="replay"
          loading={loading === 'replay'}
          onLaunch={() => launch('replay', () => api.attackReplay())}
        >
          {results.replay && (
            <AttackResult result={results.replay} mechanism="Replay protection" />
          )}
        </AttackCard>

        <AttackCard
          title="Tampering Attack"
          description="Attacker modifies message content (e.g., speed 80 → 180 km/h) while keeping the original signature. Expected: rejected by ECDSA signature verification."
          variant="tamper"
          loading={loading === 'tamper'}
          onLaunch={() => launch('tamper', () => api.attackTampering())}
        >
          {results.tamper && (
            <>
              {results.tamper.original_message && results.tamper.modified_message && (
                <div className="mt-3 space-y-1 text-xs">
                  <p className="text-slate-500">
                    Original speed:{' '}
                    <span className="text-emerald-400">
                      {String(results.tamper.original_message.speed)} km/h
                    </span>
                  </p>
                  <p className="text-slate-500">
                    Modified speed:{' '}
                    <span className="text-red-400">
                      {String(results.tamper.modified_message.speed)} km/h
                    </span>
                  </p>
                  {results.tamper.explanation && (
                    <p className="text-amber-400">{results.tamper.explanation}</p>
                  )}
                </div>
              )}
              <AttackResult
                result={results.tamper}
                mechanism="ECDSA signature verification"
              />
            </>
          )}
        </AttackCard>

        <AttackCard
          title="Impersonation Attack"
          description="Attacker signs a schema-valid message claiming to be A001 with an untrusted self-signed certificate. Expected: rejected by certificate verification."
          variant="impersonation"
          loading={loading === 'impersonation'}
          onLaunch={() => launch('impersonation', () => api.attackImpersonation())}
        >
          {results.impersonation && (
            <AttackResult
              result={results.impersonation}
              mechanism="Certificate Authority verification"
            />
          )}
        </AttackCard>

        <AttackCard
          title="Fake Certificate Attack"
          description="Attacker swaps a valid registered EVIL001 certificate onto A001's signed message. Expected: certificate validation passes, then identity validation rejects the vehicle ID mismatch."
          variant="impersonation"
          loading={loading === 'fake'}
          onLaunch={() => launch('fake', () => api.attackFakeCertificate())}
        >
          {results.fake && (
            <AttackResult
              result={results.fake}
              mechanism="Certificate + identity verification"
            />
          )}
        </AttackCard>

        <AttackCard
          title="Stale Signed Message"
          description="A correctly signed emergency message is created with a timestamp outside the freshness window. Expected: rejected as stale after cryptographic checks."
          variant="replay"
          loading={loading === 'stale'}
          onLaunch={() => launch('stale', () => api.attackStale())}
        >
          {results.stale && <AttackResult result={results.stale} mechanism="Timestamp freshness" />}
        </AttackCard>

        <AttackCard
          title="False Data from Valid Sender"
          description="A validly authenticated sender reports an implausible speed and distant position. Authentication can succeed while plausibility and relevance remain separate questions."
          variant="tamper"
          loading={loading === 'false-data'}
          onLaunch={() => launch('false-data', () => api.attackFalseData())}
        >
          {results['false-data'] && <>
            <p className="mt-3 text-xs text-amber-300">
              {results['false-data'].cryptographically_authenticated ? 'Signature accepted' : 'Signature rejected'} · {results['false-data'].plausibility_suspicious ? 'plausibility flags raised' : 'no plausibility flags'}
            </p>
            {results['false-data'].plausibility_flags?.map((flag) => <p key={flag} className="mt-1 text-xs text-slate-400">{flag}</p>)}
            <AttackResult result={results['false-data']} mechanism="Authentication and advisory plausibility checks" />
          </>}
        </AttackCard>
      </div>
    </div>
  )
}

function AttackResult({
  result,
  mechanism,
}: {
  result: AttackResponse
  mechanism: string
}) {
  const failedStep = result.pipeline?.find((step) => step.status === 'failed')
  return (
    <div className="mt-3">
      {!result.accepted && failedStep && (
        <p className="mb-2 text-xs text-red-300">Rejected at: {failedStep.name}</p>
      )}
      <Alert
        accepted={result.accepted}
        reason={result.reason}
        mechanism={mechanism}
      />
      {result.pipeline && (
        <div className="mt-3">
          <SecurityPipeline steps={result.pipeline} />
        </div>
      )}
    </div>
  )
}
