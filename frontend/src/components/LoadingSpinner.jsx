import './LoadingSpinner.css'

export default function LoadingSpinner() {
  return (
    <div className="loading-container">
      <div className="spinner">
        <div className="dot" />
        <div className="dot" />
        <div className="dot" />
      </div>
      <p className="loading-text">The AI employee is reasoning…</p>
      <p className="loading-hint">This can take a few seconds while tools are consulted.</p>
    </div>
  )
}