import type { AssetReferenceCheck } from '../../types'

export function AssetReferenceStatus({ check }: { check: AssetReferenceCheck }) {
  if (!check || check.status === 'ok') return null
  return <div className="asset-reference-status" role="status">
    <strong>Asset references: {check.status}.</strong> The agent's content claim and ZIP byte verification are separate.
    <ul>{check.issues.map((issue, i) => <li key={i}>{issue.role && `${issue.role}: `}{issue.destination && <code>{issue.destination} — </code>}{issue.message}</li>)}</ul>
  </div>
}
